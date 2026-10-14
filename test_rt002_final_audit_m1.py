"""RT-002 FA-M1 (CLAUDE-RT002-FA-M1-001) — Final Audit evidence containment, security and regression hardening.

Acceptance command (guarded, offline, exit 0 only for the complete MANIFEST):
    .venv/Scripts/python.exe -B test_rt002_final_audit_m1.py

Before any runtime import the runner redirects LOCALAPPDATA/APPDATA/TEMP into a sandbox and installs the S1
process guards (no child process — so Git can never run —, no network, no writes outside the sandbox, no
.git/.ultra access). Git is always the in-process FakeGitRepo below; the provider is always a fake HTTP client.
All "sensitive" markers are synthetic. No RAW text is embedded: the R-033/R-034 fixture keeps only recorded
metadata (lengths, permissions, counters) with synthetic strings of the same character/byte length.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import test_rt002_s1_routes as s1  # shared gate, guard and recording result (imports no runtime module)

ROOT = Path(__file__).resolve().parent
PRODUCTION_FILES = ("server.py", "verifier_runtime.py", "planner_runtime.py", "task_planner.py", "run_store.py",
                    "audit_storage.py", "provider_accounting.py", "gigachat_transport.py", "ultra_budget_policy.py")
MARKER = "M1-SYNTHETIC-SENSITIVE-7F3A9C"          # synthetic; never a real secret
UNRELATED_NAME = "notes/" + MARKER.lower() + ".env"
RUN_TOKEN = "M1-RUN-OWNED-CONTENT-41B2"
MAX_GIT_OUTPUT = 128 * 1024

MANIFEST = (
    "PacketScopeTests.test_direct_no_mutation_dirty_tree_sends_no_unrelated_data",
    "PacketScopeTests.test_direct_packet_is_independent_of_unrelated_workspace_state",
    "PacketScopeTests.test_r033_shaped_run_costs_the_same_as_r034_shaped_run",
    "PacketScopeTests.test_planner_on_and_off_scope_git_identically",
    "PacketScopeTests.test_own_mutation_keeps_its_diff_and_excludes_unrelated_changes",
    "PacketScopeTests.test_run_created_file_content_is_kept_unrelated_untracked_file_is_not",
    "PacketScopeTests.test_run_deleted_file_stays_in_scope",
    "PacketScopeTests.test_truncated_own_git_evidence_is_fail_closed_without_planner",
    "PacketScopeTests.test_non_git_workspace_is_explicit_and_not_critical",
    "PacketScopeTests.test_out_of_scope_run_path_is_critical_and_leaks_nothing",
    "PacketScopeTests.test_false_candidate_claims_remain_conflicts_without_planner",
    "PacketScopeTests.test_semantics_describe_the_scoped_contract",
    "PacketScopeTests.test_context_byte_accounting_is_exact_and_bounded",
    "PacketScopeTests.test_read_disabled_runs_no_git_in_either_mode",
    "PacketScopeTests.test_task_scoped_discovery_directory_does_not_pull_unrelated_diffs",
    "PacketScopeTests.test_task_scoped_file_requirement_still_observed",
    "PacketScopeTests.test_file_target_that_is_a_directory_is_critical_and_not_observed",
    "PacketScopeTests.test_mutating_run_without_any_scoped_path_is_critical",
    "PacketScopeTests.test_run_scoped_unattributed_status_is_reported_like_task_scoped",
    "OutboundTests.test_outbound_final_audit_request_has_no_unrelated_workspace_data",
    "OutboundTests.test_outbound_fail_verdict_still_blocks_success",
    "OutboundTests.test_outbound_mutation_run_sends_its_own_evidence_only",
    "OutboundTests.test_outbound_false_write_claim_never_succeeds",
    "IsolationTests.test_manifest_matches_the_loaded_collection",
    "IsolationTests.test_no_real_child_process_or_network_was_possible",
)

_OBSERVATIONS: dict = {}
_ISOLATED = False
_SANDBOX: Path | None = None


def setUpModule():
    if not _ISOLATED:
        raise unittest.SkipTest("run through main(): guards and sandbox are installed there")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthetic_text(chars: int, utf8_bytes: int) -> str:
    """A string with exactly `chars` characters and `utf8_bytes` UTF-8 bytes (Cyrillic + ASCII)."""
    cyrillic = utf8_bytes - chars
    return ("ж" * cyrillic + "a" * (chars - cyrillic))


# Recorded metadata of R-033 / R-034 (RAW run_started / executor response / run_finished), no RAW text.
R03X = {
    "raw_task": synthetic_text(6, 12),
    "candidate": synthetic_text(43, 78),
    "run_id": "20261009_000000_000000",            # same length as the recorded run ids (22 characters)
    "permissions": {"allow_read": True, "allow_write": False, "allow_delete": False, "allow_verify": True,
                    "allow_guard_p1": True, "read_scope": ".", "write_scope": "Документация", "delete_scope": ".",
                    "tool_limit": 20, "auto_backup": True},
    "verification_state": {"write_revision": 0, "python_write_revision": None, "python_verified_revision": None,
                           "python_verified_paths": [], "git_status_revision": None, "git_diff_revision": None,
                           "ui_smoke_required": False, "ui_smoke_write_revision": None,
                           "ui_smoke_verified_revision": None, "changed_python_paths": [],
                           "deleted_python_paths": []},
    "observed_user_chars": {"R-033": 62913, "R-034": 4122},
}


class FakeGitRepo:
    """In-process stand-in for `git status --porcelain` / `git diff HEAD` (pathspec-aware; Git never runs)."""

    def __init__(self, entries: dict[str, tuple[str, str | None]] | None = None, *, available: bool = True):
        self.entries = dict(entries or {})
        self.available = available
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, args, *, cwd, timeout=None):
        if not args or args[0] != "git":
            raise PermissionError(f"FakeGitRepo refuses non-git process: {args[:2]}")
        sub = args[args.index("--no-pager") + 1]
        specs = tuple(args[args.index("--") + 1:]) if "--" in args else ()
        self.calls.append((sub, specs))
        if not self.available:
            return {"ok": False, "exit_code": 128, "stdout": "", "stderr": "fatal: not a git repository (fake)",
                    "truncated": False, "stdout_bytes": 0, "stderr_bytes": 34}
        chosen = [p for p in sorted(self.entries) if not specs or any(
            spec == "." or p == spec or p.startswith(spec.rstrip("/") + "/") for spec in specs)]
        if sub == "status":
            text = "\n".join(f"{self.entries[p][0]} {p}" for p in chosen)
        else:
            text = "".join(self.entries[p][1] or "" for p in chosen if self.entries[p][0] != "??")
        raw = text.encode("utf-8")
        truncated = len(raw) > MAX_GIT_OUTPUT
        if truncated:
            text = raw[:MAX_GIT_OUTPUT].decode("utf-8", errors="replace") + "\n... <OUTPUT TRUNCATED> ..."
        return {"ok": True, "exit_code": 0, "stdout": text, "stderr": "", "truncated": truncated,
                "stdout_bytes": len(raw), "stderr_bytes": 0}


def diff_for(path: str, payload: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-old\n+{payload}\n"


def unrelated_dirty_tree(filler_kib: int = 8) -> dict:
    line = "+строка постороннего черновика пользователя\n"
    filler = (line * (filler_kib * 1024 // len(line) + 1))[: filler_kib * 1024]
    return {
        "notes/private_draft.md": (" M", diff_for("notes/private_draft.md", MARKER) + filler),
        "docs/other.md": (" M", diff_for("docs/other.md", "unrelated " + MARKER)),
        UNRELATED_NAME: ("??", None),
    }


class _Workspace(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        (self.root / "work").mkdir(parents=True)
        (self.root / "Документация").mkdir()

    def policy(self, **overrides):
        permissions = dict(R03X["permissions"], **overrides)
        return self.server._prepare_policy_for_workspace(self.root, self.server._normalize_permissions(permissions))

    def collect(self, repo: FakeGitRepo, *, candidate="Готово.", policy=None, tool_calls=0, write_revision=0,
                backup=None, run_owned=None, task_plan=None, freshness=None, verification_state=None,
                tool_facts=None, run_id="run-m1"):
        state = copy.deepcopy(verification_state or dict(R03X["verification_state"], write_revision=write_revision))
        with patch.object(self.server, "_run_verify_process", repo):
            context, completeness = self.server._collect_final_audit_evidence(
                root=self.root, candidate_final=candidate, policy=policy or self.policy(), run_id=run_id,
                api_request_count=1, tool_call_count=tool_calls, verification_state=state,
                backup_session=backup, run_owned_state=run_owned or {}, tool_facts=tool_facts or [],
                task_plan_evidence=task_plan, freshness_snapshot=freshness)
        return context, completeness

    def write(self, relative: str, text: str) -> dict:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {"state": "present", "content_sha256": self.server._sha256_utf8(self.server._read_logical_text(path))}

    def assert_no_unrelated_data(self, text: str):
        self.assertNotIn(MARKER, text)
        self.assertNotIn(MARKER.lower(), text)
        self.assertNotIn("private_draft", text)
        self.assertNotIn("docs/other.md", text)
        self.assertNotIn("постороннего черновика", text)


def manifest(changed=(), new=(), deleted=()):
    return {"manifest": {"changed_files": list(changed), "new_files": list(new), "deleted_files": list(deleted)}}


def task_plan_for(path: str):
    plan = {
        "task_block_id": "tb_" + "1" * 32, "run_id": "run-m1", "plan_id": "plan-m1", "plan_version": 1,
        "stages": [{"stage_id": "s1", "goal": "update", "stage_type": "produce_artifact",
                    "persistence_required": True, "allowed_capabilities": ["WRITE"],
                    "artifacts": [{"artifact_id": "a1", "path": path, "operation": "update",
                                   "postcondition": {"kind": "contains", "value": RUN_TOKEN},
                                   "allow_already_satisfied": False}],
                    "completion_mode": "persistence", "evidence_requirements": [],
                    "completion_criteria": ["updated"]}],
        "stage_states": {"s1": {"status": "SATISFIED", "obligations": {"a1": {"status": "SATISFIED"}},
                                "evidence_generation": 0}},
        "replans": [],
    }
    freshness = {"task_block_id": plan["task_block_id"], "run_id": "run-m1", "plan_id": "plan-m1",
                 "plan_version": 1,
                 "stages": [{"stage_id": "s1", "persistence_required": True,
                             "artifacts": [{"artifact_id": "a1", "path": path, "operation": "update",
                                            "obligation_status": "SATISFIED",
                                            "observed_state_sha256": "state-current"}]}]}
    return plan, freshness


class PacketScopeTests(_Workspace):
    def test_direct_no_mutation_dirty_tree_sends_no_unrelated_data(self):
        """R-033 shape: DIRECT, no tools, no mutation, foreign uncommitted work in the tree."""
        repo = FakeGitRepo(unrelated_dirty_tree())
        context, completeness = self.collect(repo)
        self.assert_no_unrelated_data(context)
        payload = json.loads(context)
        self.assertEqual(repo.calls, [])                         # no Git process for a RUN that touched nothing
        self.assertEqual(payload["task_scope"]["mode"], "run_scoped_v1")
        self.assertEqual(payload["task_scope"]["paths"], [])
        for key in ("fresh_git_status", "fresh_git_diff"):
            self.assertTrue(payload[key]["not_applicable"], key)
            self.assertEqual(payload[key]["reason"], "no_run_scoped_paths")
        self.assertTrue(completeness["complete"])
        self.assertFalse(completeness["critical_for_success"])

    def test_direct_packet_is_independent_of_unrelated_workspace_state(self):
        packets = {}
        for label, tree in (("clean", {}), ("dirty_8k", unrelated_dirty_tree(8)),
                            ("dirty_56k", unrelated_dirty_tree(56)), ("dirty_200k", unrelated_dirty_tree(200))):
            packets[label] = self.collect(FakeGitRepo(tree))[0]
        sizes = {k: len(v.encode("utf-8")) for k, v in packets.items()}
        _OBSERVATIONS["direct_packet_bytes_by_tree"] = sizes
        self.assertEqual(len(set(packets.values())), 1, sizes)

    def test_r033_shaped_run_costs_the_same_as_r034_shaped_run(self):
        """Recorded R-033/R-034 metadata (synthetic strings of identical length): only the tree differs."""
        import verifier_runtime
        observed = {}
        for label, tree in (("R-033", unrelated_dirty_tree(56)), ("R-034", {})):
            context, _ = self.collect(FakeGitRepo(tree), candidate=R03X["candidate"], run_id=R03X["run_id"])
            messages = verifier_runtime._build_verifier_messages(check_type="FINAL", raw_task=R03X["raw_task"],
                                                                 verification_context=context)
            observed[label] = {"system_chars": len(messages[0]["content"]), "user_chars": len(messages[1]["content"]),
                               "user_bytes": len(messages[1]["content"].encode("utf-8"))}
        _OBSERVATIONS["r033_r034_reconstruction"] = {"observed_before_fix": R03X["observed_user_chars"],
                                                     "reconstructed": observed}
        self.assertEqual(observed["R-033"], observed["R-034"])
        self.assertEqual(observed["R-034"]["system_chars"], 2875)

    def test_planner_on_and_off_scope_git_identically(self):
        target = "work/target.md"
        tree = dict(unrelated_dirty_tree(), **{target: (" M", diff_for(target, RUN_TOKEN))})
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        plan, freshness = task_plan_for(target)
        modes = {}
        for label, kwargs in (("planner_off", {}), ("planner_on", {"task_plan": plan, "freshness": freshness})):
            repo = FakeGitRepo(tree)
            context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                                 backup=manifest(changed=[target]), **kwargs)
            self.assert_no_unrelated_data(context)
            payload = json.loads(context)
            modes[label] = (payload["task_scope"]["mode"], sorted(set(repo.calls)), payload["task_scope"]["paths"])
            self.assertIn(RUN_TOKEN, payload["fresh_git_diff"]["stdout"])
            self.assertFalse(completeness["critical_for_success"], completeness)
        self.assertEqual(modes["planner_off"][0], "run_scoped_v1")
        self.assertEqual(modes["planner_on"][0], "task_scoped_v1")
        self.assertEqual(modes["planner_off"][1], modes["planner_on"][1])   # same Git calls, same pathspecs
        self.assertEqual(modes["planner_off"][1], [("diff", (target,)), ("status", (target,))])

    def test_own_mutation_keeps_its_diff_and_excludes_unrelated_changes(self):
        target = "work/target.md"
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        repo = FakeGitRepo(dict(unrelated_dirty_tree(), **{target: (" M", diff_for(target, RUN_TOKEN))}))
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                             backup=manifest(changed=[target]))
        self.assert_no_unrelated_data(context)
        payload = json.loads(context)
        self.assertEqual(payload["fresh_git_status"]["stdout"], f" M {target}")
        self.assertIn(RUN_TOKEN, payload["fresh_git_diff"]["stdout"])
        self.assertEqual(payload["mutation_facts"]["changed_files"], [target])
        self.assertTrue(payload["run_owned_filesystem_evidence"][0]["match"])
        self.assertEqual(payload["task_scope"]["unattributed_git_status"], [])
        self.assertFalse(completeness["critical_for_success"])

    def test_run_created_file_content_is_kept_unrelated_untracked_file_is_not(self):
        created = "work/new.md"
        owned = {created: self.write(created, RUN_TOKEN + "\n")}
        (self.root / "notes").mkdir(exist_ok=True)
        (self.root / UNRELATED_NAME).write_text(MARKER + "=value\n", encoding="utf-8")
        repo = FakeGitRepo(dict(unrelated_dirty_tree(), **{created: ("??", None)}))
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                             backup=manifest(new=[created]))
        self.assert_no_unrelated_data(context)
        payload = json.loads(context)
        self.assertEqual([item["path"] for item in payload["new_file_evidence"]], [created])
        self.assertIn(RUN_TOKEN, payload["new_file_evidence"][0]["content"])
        self.assertEqual(payload["fresh_git_status"]["stdout"], f"?? {created}")
        self.assertFalse(completeness["critical_for_success"])

    def test_run_deleted_file_stays_in_scope(self):
        deleted = "work/old.md"
        repo = FakeGitRepo(dict(unrelated_dirty_tree(), **{deleted: (" D", diff_for(deleted, "removed"))}))
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1,
                                             run_owned={deleted: {"state": "absent"}},
                                             backup=manifest(deleted=[deleted]))
        self.assert_no_unrelated_data(context)
        payload = json.loads(context)
        self.assertEqual(payload["fresh_git_status"]["stdout"], f" D {deleted}")
        self.assertEqual(sorted(set(repo.calls)), [("diff", (deleted,)), ("status", (deleted,))])
        self.assertTrue(payload["run_owned_filesystem_evidence"][0]["match"])
        self.assertFalse(completeness["critical_for_success"])

    def test_truncated_own_git_evidence_is_fail_closed_without_planner(self):
        """Planner OFF must not be a weaker policy: truncated mandatory evidence blocks SUCCESS in both modes."""
        target = "work/target.md"
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        huge = diff_for(target, RUN_TOKEN) + "+x\n" * 70_000
        repo = FakeGitRepo({target: (" M", huge)})
        _context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                              backup=manifest(changed=[target]))
        self.assertTrue(completeness["critical_for_success"])
        self.assertIn("fresh_git_diff_truncated", completeness["critical_reasons"])

    def test_non_git_workspace_is_explicit_and_not_critical(self):
        target = "work/target.md"
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        repo = FakeGitRepo(available=False)
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                             backup=manifest(changed=[target]))
        payload = json.loads(context)
        self.assertFalse(payload["fresh_git_status"]["available"])
        self.assertFalse(payload["fresh_git_diff"]["available"])
        self.assertTrue(payload["run_owned_filesystem_evidence"][0]["match"])
        self.assertFalse(completeness["critical_for_success"])

    def test_out_of_scope_run_path_is_critical_and_leaks_nothing(self):
        policy = self.policy(read_scope="work")
        repo = FakeGitRepo(unrelated_dirty_tree())
        context, completeness = self.collect(repo, policy=policy, write_revision=1, tool_calls=1,
                                             backup=manifest(changed=["notes/private_draft.md"]))
        self.assertIn("task_scope_contains_unreadable_or_out_of_scope_paths", completeness["critical_reasons"])
        self.assertNotIn(MARKER, context)
        self.assertNotIn("постороннего черновика", context)

    def test_false_candidate_claims_remain_conflicts_without_planner(self):
        repo = FakeGitRepo(unrelated_dirty_tree())
        claims = ("Файл work/target.md изменён через write_file, readback выполнен, git_status проверен.",
                  "I modified and verified the file with replace_text and python_compile.")
        for claim in claims:
            with self.subTest(claim=claim[:30]):
                context, completeness = self.collect(repo, candidate=claim)
                self.assertTrue(completeness["candidate_fact_conflicts"], completeness)
                self.assertNotIn(MARKER, context)

    def test_semantics_describe_the_scoped_contract(self):
        payload = json.loads(self.collect(FakeGitRepo(unrelated_dirty_tree()))[0])
        semantics = payload["evidence_semantics"]["fresh_git_state"]
        self.assertIn("run_scoped_v1", semantics)
        self.assertIn("pre-existing or external", semantics)
        self.assertNotIn("legacy_workspace_compat", json.dumps(payload))

    def test_context_byte_accounting_is_exact_and_bounded(self):
        target = "work/target.md"
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        repo = FakeGitRepo({target: (" M", diff_for(target, RUN_TOKEN + " ü€😀"))})
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1, run_owned=owned,
                                             backup=manifest(changed=[target]))
        self.assertEqual(completeness["context_bytes"], len(context.encode("utf-8")))
        self.assertLessEqual(completeness["context_bytes"], self.server.MAX_FINAL_AUDIT_CONTEXT_BYTES)

    def test_task_scoped_discovery_directory_does_not_pull_unrelated_diffs(self):
        """Adversarial: a Planner requirement to list/search a DIRECTORY must not import every uncommitted
        change under it; the requirement's own server-observed result is its evidence."""
        (self.root / "notes").mkdir(exist_ok=True)
        (self.root / "notes" / "index.md").write_text("index\n", encoding="utf-8")
        for tool, arguments in (("list_dir", {"path": "notes"}), ("find_text", {"path": "notes", "text": "x"}),
                                ("git_diff", {"paths": ["notes"]}), ("find_text", {"path": "notes/index.md",
                                                                                 "text": "index"})):
            plan = {"task_block_id": "tb_" + "1" * 32, "run_id": "run-m1", "plan_id": "plan-m1", "plan_version": 1,
                    "stages": [{"stage_id": "s1", "goal": "inspect", "stage_type": "analysis",
                                "persistence_required": False, "allowed_capabilities": ["READ"], "artifacts": [],
                                "completion_mode": "server_evidence",
                                "evidence_requirements": [{"evidence_id": "e1", "tool": tool, "arguments": arguments}],
                                "completion_criteria": ["inspected"]}],
                    "stage_states": {"s1": {"status": "SATISFIED", "obligations": {}, "evidence_generation": 0}},
                    "replans": []}
            freshness = {"task_block_id": plan["task_block_id"], "run_id": "run-m1", "plan_id": "plan-m1",
                         "plan_version": 1, "stages": []}
            repo = FakeGitRepo(unrelated_dirty_tree())
            with self.subTest(tool=tool, arguments=arguments):
                context, _ = self.collect(repo, task_plan=plan, freshness=freshness, tool_calls=1)
                self.assert_no_unrelated_data(context)
                self.assertEqual(repo.calls, [])
                self.assertEqual(json.loads(context)["task_scope"]["paths"], [])
        # an out-of-READ-scope discovery path is still rejected mechanically
        plan["stages"][0]["evidence_requirements"] = [{"evidence_id": "e1", "tool": "list_dir",
                                                       "arguments": {"path": "notes"}}]
        _context, completeness = self.collect(FakeGitRepo(), policy=self.policy(read_scope="work"),
                                              task_plan=plan, freshness=freshness, tool_calls=1)
        self.assertIn("task_scope_contains_unreadable_or_out_of_scope_paths", completeness["critical_reasons"])

    def test_file_target_that_is_a_directory_is_critical_and_not_observed(self):
        """Adversarial: a (malformed) artifact path naming a directory must not pull its contents into FINAL."""
        (self.root / "notes").mkdir(exist_ok=True)
        plan, freshness = task_plan_for("notes")
        repo = FakeGitRepo(unrelated_dirty_tree())
        context, completeness = self.collect(repo, task_plan=plan, freshness=freshness, tool_calls=1)
        self.assert_no_unrelated_data(context)
        self.assertEqual(repo.calls, [])
        self.assertIn("task_scope_contains_unreadable_or_out_of_scope_paths", completeness["critical_reasons"])

    def test_mutating_run_without_any_scoped_path_is_critical(self):
        """write_revision>0 with no RUN-owned/mutation/verification path is an inconsistent server state."""
        repo = FakeGitRepo(unrelated_dirty_tree())
        context, completeness = self.collect(repo, write_revision=1, tool_calls=1)
        self.assertIn("mutating_run_without_scoped_paths", completeness["critical_reasons"])
        self.assertEqual(repo.calls, [])
        self.assert_no_unrelated_data(context)

    def test_run_scoped_unattributed_status_is_reported_like_task_scoped(self):
        """A scoped path the RUN did not mutate (here: a verification target) is an explicit negative fact."""
        target, extra = "work/target.md", "work/check.py"
        owned = {target: self.write(target, RUN_TOKEN + "\n")}
        self.write(extra, "x = 1\n")
        state = dict(R03X["verification_state"], write_revision=1, changed_python_paths=[extra])
        repo = FakeGitRepo({target: (" M", diff_for(target, RUN_TOKEN)), extra: (" M", diff_for(extra, "x = 1"))})
        context, _ = self.collect(repo, tool_calls=1, run_owned=owned, backup=manifest(changed=[target]),
                                  verification_state=state)
        self.assertEqual(json.loads(context)["task_scope"]["unattributed_git_status"], [f" M {extra}"])

    def test_task_scoped_file_requirement_still_observed(self):
        """Counter-check: a file the contract verifies stays in Git scope (its own diff is task evidence)."""
        target = "work/target.md"
        self.write(target, RUN_TOKEN + "\n")
        plan = {"task_block_id": "tb_" + "1" * 32, "run_id": "run-m1", "plan_id": "plan-m1", "plan_version": 1,
                "stages": [{"stage_id": "s1", "goal": "verify", "stage_type": "verification",
                            "persistence_required": False, "allowed_capabilities": ["VERIFY"], "artifacts": [],
                            "completion_mode": "server_evidence",
                            "evidence_requirements": [{"evidence_id": "e1", "tool": "verify_file_content",
                                                       "arguments": {"path": target, "kind": "contains",
                                                                     "value": RUN_TOKEN}}],
                            "completion_criteria": ["verified"]}],
                "stage_states": {"s1": {"status": "SATISFIED", "obligations": {}, "evidence_generation": 0}},
                "replans": []}
        freshness = {"task_block_id": plan["task_block_id"], "run_id": "run-m1", "plan_id": "plan-m1",
                     "plan_version": 1, "stages": []}
        repo = FakeGitRepo(dict(unrelated_dirty_tree(), **{target: (" M", diff_for(target, RUN_TOKEN))}))
        context, _ = self.collect(repo, task_plan=plan, freshness=freshness, tool_calls=1)
        self.assert_no_unrelated_data(context)
        self.assertEqual(sorted(set(repo.calls)), [("diff", (target,)), ("status", (target,))])
        self.assertIn(RUN_TOKEN, json.loads(context)["fresh_git_diff"]["stdout"])

    def test_read_disabled_runs_no_git_in_either_mode(self):
        target = "work/target.md"
        plan, freshness = task_plan_for(target)
        for kwargs in ({}, {"task_plan": plan, "freshness": freshness}):
            repo = FakeGitRepo(unrelated_dirty_tree())
            context, _ = self.collect(repo, policy=self.policy(allow_read=False), **kwargs)
            self.assertEqual(repo.calls, [])
            self.assertFalse(json.loads(context)["fresh_git_status"]["available"])


# --------------------------------------------------------------------------- outbound (real verifier, fake HTTP)

VERIFIER_SYSTEM_PREFIX = "You are an independent one-shot verifier"


class FakeResponse:
    status_code = 200

    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return copy.deepcopy(self._data)


def chat_reply(content: str = "", *, function_call: dict | None = None) -> dict:
    message = {"content": content}
    if function_call:
        message["function_call"] = function_call
    return {"choices": [{"message": message, "finish_reason": "function_call" if function_call else "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}}


def verdict(result: str) -> dict:
    body = {"result": result, "check_type": "FINAL", "violations": [] if result == "PASS" else ["synthetic"],
            "reason": "synthetic verdict", "required_action": "None." if result == "PASS" else "Fix it.",
            "route": "NONE" if result == "PASS" else "EXECUTION_DEFECT", "affected_stage_ids": []}
    return chat_reply(json.dumps(body))


class RoutingClient:
    """One fake httpx.AsyncClient for Executor and Verifier (both resolve to the same httpx module)."""

    def __init__(self, executor_replies: list[dict], verifier_replies: list[dict]):
        self.executor_replies = list(executor_replies)
        self.verifier_replies = list(verifier_replies)
        self.executor_bodies: list[dict] = []
        self.verifier_bodies: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, _url, *, headers, json):
        body = copy.deepcopy(json)
        first = (body.get("messages") or [{}])[0].get("content") or ""
        if first.startswith(VERIFIER_SYSTEM_PREFIX):
            self.verifier_bodies.append(body)
            return FakeResponse(self.verifier_replies.pop(0) if self.verifier_replies else verdict("PASS"))
        self.executor_bodies.append(body)
        return FakeResponse(self.executor_replies.pop(0) if self.executor_replies else chat_reply("Готово."))


class OutboundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import server
        self.server = server
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        (self.root / "work").mkdir(parents=True)
        (self.root / "notes").mkdir()
        (self.root / UNRELATED_NAME).write_text(MARKER + "=value\n", encoding="utf-8")
        self.runtime = Path(self.temp.name) / "runtime"
        self.events: list[dict] = []

    async def run_direct(self, client: RoutingClient, repo: FakeGitRepo, *, task: str, **permission_overrides):
        import httpx
        import verifier_runtime
        permissions = {"allow_read": True, "allow_write": False, "allow_delete": False, "allow_verify": True,
                       "allow_guard_p1": False, "read_scope": ".", "write_scope": ".", "delete_scope": ".",
                       "tool_limit": 5, "auto_backup": False}
        permissions.update(permission_overrides)
        backup_dir = self.runtime / "backup" / "run"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = {"backup_dir": backup_dir, "backed_up_paths": set(), "delete_backed_up_paths": set(),
                  "manifest": {"core_files": [], "changed_files": [], "new_files": [], "deleted_files": []}}
        workspace_info = {"workspace_id": "ws_m1", "storage_created": False, "workspace_created": False,
                          "project_context_created": False}
        with ExitStack() as stack:
            for target in (self.server, verifier_runtime):
                stack.enter_context(patch.object(target, "get_access_token", AsyncMock(return_value="token")))
            stack.enter_context(patch.object(httpx, "AsyncClient", side_effect=lambda *a, **k: client))
            stack.enter_context(patch.object(self.server, "ensure_workspace_storage", return_value=workspace_info))
            stack.enter_context(patch.object(self.server, "load_project_context", return_value=""))
            stack.enter_context(patch.object(self.server, "load_agent_global_context", return_value="ROLE"))
            stack.enter_context(patch.object(self.server, "ensure_workspace_runtime_dirs", return_value={
                "backup_dir": str(self.runtime / "backup"), "log_dir": str(self.runtime / "logs")}))
            stack.enter_context(patch.object(self.server, "_create_backup_session", return_value=backup))
            stack.enter_context(patch.object(self.server, "_request_audit_diagnostic",
                                             AsyncMock(return_value="Краткое основание.")))
            stack.enter_context(patch.object(self.server, "_run_verify_process", repo))
            return await self.server.run_agent_task(task, str(self.root), permissions=permissions,
                                                    on_event=self.events.append, planner_enabled=False,
                                                    final_audit_enabled=True)

    def outbound_text(self, client: RoutingClient) -> str:
        return json.dumps(client.verifier_bodies, ensure_ascii=False)

    async def test_outbound_final_audit_request_has_no_unrelated_workspace_data(self):
        client = RoutingClient([chat_reply("Привет! Чем могу помочь?")], [verdict("PASS")])
        repo = FakeGitRepo(unrelated_dirty_tree(56))
        result = await self.run_direct(client, repo, task="привет")
        self.assertEqual(result, "Привет! Чем могу помочь?")
        self.assertEqual(len(client.verifier_bodies), 1)         # Final Audit still runs exactly once
        outbound = self.outbound_text(client)
        self.assertNotIn(MARKER, outbound)
        self.assertNotIn(MARKER.lower(), outbound)
        self.assertNotIn("постороннего черновика", outbound)
        self.assertEqual(repo.calls, [])
        user = client.verifier_bodies[0]["messages"][1]["content"]
        _OBSERVATIONS["outbound_greeting_user_chars"] = len(user)
        self.assertIn("run_scoped_v1", user)

    async def test_outbound_fail_verdict_still_blocks_success(self):
        client = RoutingClient([chat_reply("Привет!")], [verdict("FAIL"), verdict("FAIL"), verdict("FAIL")])
        repo = FakeGitRepo(unrelated_dirty_tree())
        with self.assertRaises(self.server.FinalAuditSemanticError):
            await self.run_direct(client, repo, task="привет")
        self.assertGreaterEqual(len(client.verifier_bodies), 1)
        self.assertNotIn(MARKER, self.outbound_text(client))
        self.assertIn("final_audit_failed", [e["event"] for e in self.events])
        self.assertNotIn("SUCCESS", [e.get("status") for e in self.events if e["event"] == "run_finished"])

    async def test_outbound_mutation_run_sends_its_own_evidence_only(self):
        created = "work/result.md"
        client = RoutingClient([
            chat_reply(function_call={"name": "write_file",
                                      "arguments": {"path": created, "content": RUN_TOKEN + "\n"}}),
            chat_reply("Файл work/result.md создан."),
        ], [verdict("PASS")])
        repo = FakeGitRepo(dict(unrelated_dirty_tree(), **{created: ("??", None)}))
        result = await self.run_direct(client, repo, task="создай файл work/result.md", allow_write=True)
        self.assertEqual(result, "Файл work/result.md создан.")
        outbound = self.outbound_text(client)
        self.assertEqual(len(client.verifier_bodies), 1)
        self.assertIn(RUN_TOKEN, outbound)                       # the RUN's own new-file evidence is present
        self.assertIn(f"?? {created}", outbound)
        self.assertNotIn(MARKER, outbound)
        self.assertNotIn("постороннего черновика", outbound)
        self.assertTrue(repo.calls)
        self.assertTrue(all(specs == (created,) for _sub, specs in repo.calls), repo.calls)

    async def test_outbound_false_write_claim_never_succeeds(self):
        """The Executor claims a write it never made; even a (wrong) PASS from the model must not give SUCCESS."""
        client = RoutingClient([chat_reply("Файл work/result.md изменён через write_file, readback выполнен.")],
                               [verdict("PASS")])
        repo = FakeGitRepo(unrelated_dirty_tree())
        with self.assertRaises(Exception):
            await self.run_direct(client, repo, task="измени файл work/result.md")
        self.assertNotIn("SUCCESS", [e.get("status") for e in self.events if e["event"] == "run_finished"])
        self.assertNotIn(MARKER, self.outbound_text(client))


# --------------------------------------------------------------------------- isolation

class IsolationTests(unittest.TestCase):
    def test_manifest_matches_the_loaded_collection(self):
        collected = []

        def flatten(item):
            if isinstance(item, unittest.TestSuite):
                for child in item:
                    flatten(child)
            else:
                collected.append(s1._short_id(item))

        flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
        self.assertEqual(sorted(collected), sorted(MANIFEST))

    def test_no_real_child_process_or_network_was_possible(self):
        import socket
        import subprocess
        with self.assertRaises(PermissionError):
            subprocess.run(["git", "--version"], capture_output=True)
        with self.assertRaises(PermissionError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)


# --------------------------------------------------------------------------- guarded runner

def _file_hashes(names):
    return {name: _sha256((ROOT / name).read_bytes()) for name in names}


def main() -> int:
    global _ISOLATED, _SANDBOX
    sys.dont_write_bytecode = True
    args = sys.argv[1:]
    base = Path(tempfile.mkdtemp(prefix="claude-rt002-m1-"))
    _SANDBOX = base
    production_before = _file_hashes(PRODUCTION_FILES)
    for key in ("LOCALAPPDATA", "APPDATA", "TEMP", "TMP"):
        location = base / key.lower()
        location.mkdir()
        os.environ[key] = str(location)
    tempfile.tempdir = str(base / "temp")
    for key in ("GIGACHAT_CREDENTIALS", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        os.environ.pop(key, None)
    violations = s1._install_guards(base)
    _ISOLATED = True
    already = sorted(m for m in ("server", "planner_runtime", "verifier_runtime", "compressor_runtime",
                                 "run_store") if m in sys.modules)
    if already:
        raise SystemExit("Runtime modules imported before guards: " + ", ".join(already))
    import server  # noqa: F401  (only after guards and sandbox redirection)
    collected_tests = []

    def flatten(item):
        if isinstance(item, unittest.TestSuite):
            for child in item:
                flatten(child)
        else:
            collected_tests.append(item)

    flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    collected = [s1._short_id(t) for t in collected_tests]
    selected = unresolved = None
    tests = collected_tests
    if args:
        requested = list(dict.fromkeys(args))
        resolved = {r: [t for t in collected_tests if s1._short_id(t) == r or t.id().split(".")[-1] == r]
                    for r in requested}
        unresolved = [r for r, found in resolved.items() if not found]
        tests = [t for t in collected_tests if any(t in found for found in resolved.values())]
        selected = [s1._short_id(t) for t in tests]
    started = time.time()
    log_path = base / "unittest.log"
    s1._RecordingResult.started_ids = []
    with log_path.open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=s1._RecordingResult).run(
            unittest.TestSuite(tests))
    counts = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses)}
    production_after = _file_hashes(PRODUCTION_FILES)
    problems = [f"production file changed during run: {n}" for n in PRODUCTION_FILES
                if production_before[n] != production_after[n]]
    expected_blocks = {"subprocess.Popen", "socket.connect", "socket.getaddrinfo"}   # the deliberate probes
    unexpected = [v for v in violations if v["event"] not in expected_blocks]
    probe_only = [v for v in violations if v["event"] in expected_blocks]
    if len(probe_only) > 2:
        problems.append(f"more blocked child/network attempts than the isolation probes: {len(probe_only)}")
    gate = s1.evaluate_gate(manifest=list(MANIFEST), collected=collected, selected=selected,
                            unresolved_selectors=unresolved or [], started=s1._RecordingResult.started_ids,
                            counts=counts, evidence_problems=problems, violations=unexpected)
    report = {
        "task": "CLAUDE-RT002-FA-M1-001", "sandbox": str(base), "python": sys.version.split()[0], "gate": gate,
        "counts": counts, "manifest_size": len(MANIFEST), "failures": [t.id() for t, _ in result.failures],
        "errors": [t.id() for t, _ in result.errors], "skipped": [(t.id(), r) for t, r in result.skipped],
        "isolation_violations": unexpected, "isolation_probe_blocks": len(probe_only), "problems": problems,
        "selected": selected, "production_hashes": production_after,
        "elapsed_seconds": round(time.time() - started, 3), "observations": _OBSERVATIONS,
        "log": str(log_path), "log_sha256": _sha256(log_path.read_bytes()),
    }
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "production_hashes"}, ensure_ascii=False, indent=2))
    if result.failures or result.errors:
        print(log_path.read_text(encoding="utf-8").split("=" * 70, 1)[-1][:20000])
    return gate["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
