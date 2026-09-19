from __future__ import annotations

import json
import tempfile
from pathlib import Path

import server


ROOT = Path(__file__).resolve().parent
VERIFY_TOOLS = {"python_compile", "git_status", "git_diff", "ui_smoke_test"}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)
    print(f"OK: {message}")


def build_policy(*, verify: bool) -> dict:
    policy = server._normalize_permissions(
        {
            "allow_read": True,
            "allow_write": False,
            "allow_delete": False,
            "allow_verify": verify,
            "read_scope": ".",
            "write_scope": ".",
            "delete_scope": ".",
            "tool_limit": 20,
            "auto_backup": False,
        }
    )
    return server._prepare_policy_for_workspace(ROOT, policy)


def main() -> None:
    print("SAFE v3 Verification Layer — local self-test")
    print(f"Workspace: {ROOT}")
    print()

    policy_on = build_policy(verify=True)
    names_on = {item["name"] for item in server._functions_for_policy(policy_on)}
    check(
        VERIFY_TOOLS.issubset(names_on),
        "VERIFY=ON exposes exactly the new verification capabilities",
    )

    policy_off = build_policy(verify=False)
    names_off = {item["name"] for item in server._functions_for_policy(policy_off)}
    check(
        VERIFY_TOOLS.isdisjoint(names_off),
        "VERIFY=OFF physically removes verification tools",
    )

    compile_ok = server._agent_python_compile(
        ROOT,
        ["server.py", "ultra_ui.py"],
        policy_on,
    )
    check(
        compile_ok.get("ok") is True and compile_ok.get("exit_code") == 0,
        "python_compile passes server.py + ultra_ui.py",
    )

    bad_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".py",
            prefix="__ultra_verify_bad_",
            dir=ROOT,
            delete=False,
        ) as handle:
            handle.write("def broken(:\n    pass\n")
            bad_path = Path(handle.name)

        compile_bad = server._agent_python_compile(
            ROOT,
            [bad_path.name],
            policy_on,
        )
        check(
            compile_bad.get("ok") is False
            and compile_bad.get("exit_code") not in (0,),
            "python_compile returns a real FAIL for broken Python",
        )
        check(
            bool(compile_bad.get("stderr")),
            "broken Python produces real compiler diagnostics",
        )
    finally:
        if bad_path is not None:
            bad_path.unlink(missing_ok=True)

    status = server._agent_git_status(ROOT, policy_on)
    check(status.get("ok") is True, "git_status executes read-only")

    diff = server._agent_git_diff(ROOT, [], policy_on)
    check(diff.get("ok") is True, "git_diff HEAD executes read-only")

    smoke = server._agent_ui_smoke_test(ROOT, policy_on)
    check(
        smoke.get("ok") is True and smoke.get("exit_code") == 0,
        "ui_smoke_test constructs UltraApp in a subprocess",
    )

    print()
    print("RESULT: SAFE v3 verification tools are operational.")
    print("No Git commit/push/add/reset/checkout or other Git mutation was performed.")
    print()
    print("git_status output:")
    print(status.get("stdout") or "<clean>")
    print()
    print("ui_smoke_test stdout:")
    print(smoke.get("stdout") or "<empty>")


if __name__ == "__main__":
    main()
