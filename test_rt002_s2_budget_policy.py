"""RT-002/B2 S2 (CLAUDE-RT002-S2-001) — offline tests of the budget policy contract.

Acceptance command:
    .venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py
Optional provenance mode (needs the local Run Stores the dataset was derived from):
    .venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py --provenance
Exit codes (same gate as S1): 0 = full MANIFEST passed; 1 = FAIL (failure, error, skip, collection
mismatch, zero tests, unresolved selector, isolation violation, dataset/production drift);
3 = PARTIAL_SELECTION (positional selectors). The core suite is self-contained: the calibration
dataset below holds only derived numbers and run locators, pinned by SHA-256, so it runs without
local RAW. --provenance re-derives it from local RAW and fails if any embedded row is not reproduced.
Ordinary unittest discovery skips this module; such a run is NOT an S2 acceptance result.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import replace
import glob
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

import test_rt002_s1_routes as s1  # shared F1 gate, guard and recording result (no runtime import)

ROOT = Path(__file__).resolve().parent
_ISOLATED = False
_SANDBOX: Path | None = None
_PROVENANCE = False
_PROVENANCE_ROWS: list | None = None
_PROVENANCE_PROBLEMS: list[str] = []
_OBSERVATIONS: dict = {}

PRODUCTION_FILES = ("server.py", "planner_runtime.py", "task_planner.py", "verifier_runtime.py",
                    "compressor_runtime.py", "provider_accounting.py", "gigachat_transport.py", "run_store.py",
                    "audit_storage.py", "workspace_runtime_settings.py", "model_registry.py", "ultra_ui.py",
                    "context_storage.py", "ultra_budget_policy.py")
# route_id -> S1 physical send site (module, owner); S3b binds these constants at the send sites
ROUTE_SEND_SITES = {"executor": ("server.py", "_run_agent_task_impl"),
                    "audit_diagnostic": ("server.py", "_request_audit_diagnostic"),
                    "planner_session": ("planner_runtime.py", "PlannerSession.call"),
                    "planner_direct": ("planner_runtime.py", "run_planner"),
                    "verifier_final": ("verifier_runtime.py", "_request_gigachat"),
                    "verifier_permission": ("verifier_runtime.py", "_request_gigachat"),
                    "planner_review": ("verifier_runtime.py", "_request_gigachat"),
                    "compressor": ("compressor_runtime.py", "_request_gigachat"),
                    "mcp_chat": ("server.py", "ask_gigachat"),
                    "oauth": ("gigachat_transport.py", "get_access_token")}
# body max_tokens per route as sent today (S1): the exact output reserve of each physical attempt
ROUTE_MAX_TOKENS = {"executor": 32768, "audit_diagnostic": 160, "planner_session": 8192, "planner_direct": 8192,
                    "verifier_final": 2048, "verifier_permission": 2048, "planner_review": 2048,
                    "compressor": 32768, "mcp_chat": 32768}
RUN_NAMES = {"project/20260930_233622_70cc6c": "R-025", "project/20260930_233733_1f2fee": "R-026",
             "project/20261001_002149_2d20df": "R-027", "project/20261001_004240_a734f1": "R-029",
             "project/20261001_004705_96dc2e": "R-030", "project/20261001_182057_e90f93": "R-031",
             "project/20261009_211347_6efe8c": "R-032", "project/20261009_211440_30b40f": "R-033",
             "project/20261009_223343_3f4fef": "R-034", "project/20261009_223401_874b8d": "R-035"}

# Calibration dataset: (run locator, record sequence, route, provider model, wire bytes, terminal outcome,
# prompt_tokens, precached_prompt_tokens, completion_tokens) for every physical attempt found in the local
# Run Stores (project + TASK151A/B live benches) and compressor logs, first terminal per attempt.
DATASET_SHA256 = "8a3ea10b75280ece550138af9a912b161997e17f5f3f17c894686961babf90ce"
ROWS = (
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 507),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 18, 'executor', 'GigaChat-3-Ultra', 34938, 'completed', 4728, 0, 80),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 26, 'planner_session', 'GigaChat-3-Ultra', 17252, 'completed', 3868, 0, 43),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 45, 'executor', 'GigaChat-3-Ultra', 32264, 'completed', 4274, 64, 43),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 60, 'executor', 'GigaChat-3-Ultra', 32686, 'completed', 4443, 0, 97),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3982, 0, 92),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 4001, 0, 58),
    ('Alarm/TASK151A_BENCH/B1_clean/20261001_004029_1585f3', 83, 'verifier_final', 'GigaChat-3-Ultra', 14913, 'completed', 3993, 0, 109),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 366),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 18, 'executor', 'GigaChat-3-Ultra', 34974, 'completed', 4740, 0, 80),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 26, 'planner_session', 'GigaChat-3-Ultra', 16644, 'completed', 3733, 0, 56),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 45, 'executor', 'GigaChat-3-Ultra', 32254, 'completed', 4338, 0, 43),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 60, 'executor', 'GigaChat-3-Ultra', 32628, 'completed', 4434, 0, 97),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3988, 0, 72),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 4007, 0, 34),
    ('Alarm/TASK151A_BENCH/B1_clean_02/20261001_144732_50dce3', 83, 'verifier_final', 'GigaChat-3-Ultra', 20259, 'completed', 7146, 0, 102),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 348),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 18, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 4600, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 26, 'planner_session', 'GigaChat-3-Ultra', 16491, 'completed', 3704, 0, 56),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 45, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 4332, 0, 43),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 60, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 4303, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3987, 0, 72),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3878, 128, 69),
    ('Alarm/TASK151A_BENCH/B1_clean_03/20261001_144801_87ef49', 83, 'verifier_final', 'GigaChat-3-Ultra', 21431, 'completed', 7669, 0, 110),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 367),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 18, 'executor', 'GigaChat-3-Ultra', 34974, 'completed', 4611, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 26, 'planner_session', 'GigaChat-3-Ultra', 16648, 'completed', 3736, 0, 56),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 45, 'executor', 'GigaChat-3-Ultra', 32258, 'completed', 4338, 0, 43),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 60, 'executor', 'GigaChat-3-Ultra', 32628, 'completed', 4305, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3986, 0, 92),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 4005, 0, 57),
    ('Alarm/TASK151A_BENCH/B1_clean_04/20261001_144828_6fc843', 83, 'verifier_final', 'GigaChat-3-Ultra', 22444, 'completed', 8176, 0, 102),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 371),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 18, 'executor', 'GigaChat-3-Ultra', 34974, 'completed', 4613, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 26, 'planner_session', 'GigaChat-3-Ultra', 16669, 'completed', 1378, 2368, 56),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 45, 'executor', 'GigaChat-3-Ultra', 32279, 'completed', 4216, 128, 43),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 60, 'executor', 'GigaChat-3-Ultra', 32628, 'completed', 4307, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 401, 3584, 72),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3876, 128, 78),
    ('Alarm/TASK151A_BENCH/B1_clean_05/20261001_144855_02ad28', 83, 'verifier_final', 'GigaChat-3-Ultra', 23615, 'completed', 8710, 0, 107),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 370),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 18, 'executor', 'GigaChat-3-Ultra', 34974, 'completed', 4677, 64, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 26, 'planner_session', 'GigaChat-3-Ultra', 16668, 'completed', 1374, 2368, 56),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 45, 'executor', 'GigaChat-3-Ultra', 32279, 'completed', 4216, 128, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 60, 'executor', 'GigaChat-3-Ultra', 32627, 'completed', 4306, 128, 75),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 67, 'executor', 'GigaChat-3-Ultra', 33597, 'completed', 4689, 0, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 78, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3859, 128, 72),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 85, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 4006, 0, 19),
    ('Alarm/TASK151A_BENCH/B1_dirty/20261001_004215_145316', 90, 'verifier_final', 'GigaChat-3-Ultra', 15568, 'provider_error', None, None, None),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'parse_error', 2824, 0, 356),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 16, 'planner_session', 'GigaChat-3-Ultra', 15379, 'completed', 3280, 0, 348),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 27, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 4598, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 35, 'planner_session', 'GigaChat-3-Ultra', 18564, 'completed', 1347, 2816, 52),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 54, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 4202, 128, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 69, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 4365, 64, 75),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 76, 'executor', 'GigaChat-3-Ultra', 33591, 'completed', 4556, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 87, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3984, 0, 88),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 94, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3939, 64, 45),
    ('Alarm/TASK151A_BENCH/B1_dirty_02/20261001_005308_03a909', 99, 'verifier_final', 'GigaChat-3-Ultra', 17048, 'completed', 5165, 0, 107),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'parse_error', 2824, 0, 357),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 16, 'planner_session', 'GigaChat-3-Ultra', 15386, 'completed', 913, 2368, 349),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 27, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 4603, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 35, 'planner_session', 'GigaChat-3-Ultra', 18578, 'completed', 1803, 2368, 49),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 54, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 4335, 0, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 69, 'executor', 'GigaChat-3-Ultra', 32628, 'completed', 4307, 128, 75),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 76, 'executor', 'GigaChat-3-Ultra', 33598, 'completed', 4562, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 87, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3858, 128, 88),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 94, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3877, 128, 65),
    ('Alarm/TASK151A_BENCH/B1_dirty_03/20261001_145000_42f306', 99, 'verifier_final', 'GigaChat-3-Ultra', 24319, 'completed', 8777, 448, 113),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'parse_error', 2824, 0, 347),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 16, 'planner_session', 'GigaChat-3-Ultra', 15252, 'completed', 884, 2368, 490),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 27, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 4598, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 35, 'planner_session', 'GigaChat-3-Ultra', 19085, 'completed', 1904, 2368, 50),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 54, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 4202, 128, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 69, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 845, 3584, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 80, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 402, 3584, 88),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 87, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3877, 128, 59),
    ('Alarm/TASK151A_BENCH/B1_dirty_04/20261001_145037_15ecb0', 92, 'verifier_final', 'GigaChat-3-Ultra', 25507, 'completed', 9747, 0, 110),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'parse_error', 456, 2368, 356),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 16, 'planner_session', 'GigaChat-3-Ultra', 15379, 'completed', 912, 2368, 348),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 27, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 1148, 3584, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 35, 'planner_session', 'GigaChat-3-Ultra', 18564, 'completed', 1801, 2368, 51),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 54, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 752, 3584, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 69, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 851, 3584, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 80, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3859, 128, 88),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 87, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 3878, 128, 48),
    ('Alarm/TASK151A_BENCH/B1_dirty_05/20261001_145115_092594', 92, 'verifier_final', 'GigaChat-3-Ultra', 26583, 'completed', 10287, 0, 103),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 456, 2368, 348),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 18, 'executor', 'GigaChat-3-Ultra', 34919, 'completed', 4600, 128, 80),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 26, 'planner_session', 'GigaChat-3-Ultra', 16491, 'completed', 3712, 0, 56),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 45, 'executor', 'GigaChat-3-Ultra', 32218, 'completed', 748, 3584, 43),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 60, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 4303, 128, 97),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 399, 3584, 88),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 418, 3584, 91),
    ('Alarm/TASK151A_BENCH/B1_dirty_06/20261001_145147_e92770', 83, 'verifier_final', 'GigaChat-3-Ultra', 27868, 'completed', 10871, 0, 106),
    ('Alarm/TASK151A_BENCH/B2_bounded_01/20261001_143717_a1fda6', 7, 'planner_session', 'GigaChat-3-Ultra', 13934, 'parse_error', 2965, 0, 639),
    ('Alarm/TASK151A_BENCH/B2_bounded_01/20261001_143717_a1fda6', 16, 'planner_session', 'GigaChat-3-Ultra', 17248, 'parse_error', 3673, 0, 905),
    ('Alarm/TASK151A_BENCH/B2_bounded_01/20261001_143717_a1fda6', 23, 'planner_review', 'GigaChat-3-Ultra', 25868, 'completed', 5435, 0, 171),
    ('Alarm/TASK151A_BENCH/B2_bounded_01/20261001_143717_a1fda6', 29, 'planner_session', 'GigaChat-3-Ultra', 22441, 'parse_error', 4776, 0, 909),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'parse_error', 2999, 0, 616),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 16, 'planner_session', 'GigaChat-3-Ultra', 17261, 'parse_error', 1257, 2432, 495),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 23, 'planner_review', 'GigaChat-3-Ultra', 23705, 'completed', 5056, 0, 355),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 29, 'planner_session', 'GigaChat-3-Ultra', 21209, 'completed', 4547, 0, 675),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 40, 'executor', 'GigaChat-3-Ultra', 37732, 'completed', 5192, 0, 63),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 48, 'executor', 'GigaChat-3-Ultra', 38998, 'completed', 5570, 0, 151),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 56, 'planner_session', 'GigaChat-3-Ultra', 26153, 'completed', 5813, 0, 49),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 75, 'executor', 'GigaChat-3-Ultra', 33185, 'completed', 4500, 0, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 90, 'executor', 'GigaChat-3-Ultra', 33457, 'completed', 4597, 0, 105),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 105, 'executor', 'GigaChat-3-Ultra', 33192, 'completed', 4539, 0, 25),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 116, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 4141, 0, 55),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 123, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 4160, 0, 78),
    ('Alarm/TASK151A_BENCH/B2_bounded_02/20261001_143928_3319b9', 128, 'verifier_final', 'GigaChat-3-Ultra', 16484, 'completed', 4828, 0, 120),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'completed', 2999, 0, 484),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 18, 'executor', 'GigaChat-3-Ultra', 37668, 'completed', 5174, 0, 63),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 26, 'executor', 'GigaChat-3-Ultra', 38934, 'completed', 5552, 0, 151),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 34, 'planner_session', 'GigaChat-3-Ultra', 18160, 'completed', 4055, 0, 41),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 53, 'executor', 'GigaChat-3-Ultra', 33224, 'completed', 4512, 0, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 68, 'executor', 'GigaChat-3-Ultra', 33474, 'completed', 4604, 0, 105),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 83, 'executor', 'GigaChat-3-Ultra', 33205, 'completed', 4546, 0, 25),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 94, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 4144, 0, 55),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 101, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 4163, 0, 61),
    ('Alarm/TASK151A_BENCH/B2_bounded_03/20261001_144202_601e70', 106, 'verifier_final', 'GigaChat-3-Ultra', 17593, 'completed', 5378, 0, 114),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'completed', 2999, 0, 670),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 18, 'executor', 'GigaChat-3-Ultra', 37752, 'completed', 5205, 0, 63),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 26, 'executor', 'GigaChat-3-Ultra', 39018, 'completed', 5583, 0, 151),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 34, 'planner_session', 'GigaChat-3-Ultra', 19028, 'completed', 4270, 0, 36),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 53, 'executor', 'GigaChat-3-Ultra', 33209, 'completed', 4513, 0, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 68, 'executor', 'GigaChat-3-Ultra', 33488, 'completed', 4611, 0, 105),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 83, 'executor', 'GigaChat-3-Ultra', 33193, 'completed', 4546, 0, 25),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 94, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 4147, 0, 55),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 101, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 4166, 0, 88),
    ('Alarm/TASK151A_BENCH/B2_bounded_04/20261001_144238_154447', 106, 'verifier_final', 'GigaChat-3-Ultra', 18923, 'completed', 6000, 0, 126),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'parse_error', 567, 2432, 617),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 16, 'planner_session', 'GigaChat-3-Ultra', 17249, 'parse_error', 743, 2944, 488),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 23, 'planner_review', 'GigaChat-3-Ultra', 23680, 'completed', 5047, 0, 262),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 29, 'planner_session', 'GigaChat-3-Ultra', 20816, 'completed', 1518, 2944, 674),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 40, 'executor', 'GigaChat-3-Ultra', 37732, 'completed', 5191, 0, 63),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 48, 'executor', 'GigaChat-3-Ultra', 38998, 'completed', 5569, 0, 151),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 56, 'planner_session', 'GigaChat-3-Ultra', 25814, 'completed', 2452, 3264, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 75, 'executor', 'GigaChat-3-Ultra', 33185, 'completed', 915, 3584, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 90, 'executor', 'GigaChat-3-Ultra', 33457, 'completed', 4596, 0, 105),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 105, 'executor', 'GigaChat-3-Ultra', 33186, 'completed', 4531, 0, 25),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 116, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 4144, 0, 55),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 123, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 579, 3584, 61),
    ('Alarm/TASK151A_BENCH/B2_bounded_05/20261001_144316_dcdf6d', 128, 'verifier_final', 'GigaChat-3-Ultra', 19864, 'completed', 6491, 0, 108),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'parse_error', 2999, 0, 662),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 16, 'planner_session', 'GigaChat-3-Ultra', 17512, 'parse_error', 3730, 0, 673),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 23, 'planner_review', 'GigaChat-3-Ultra', 24929, 'completed', 5312, 0, 147),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 29, 'planner_session', 'GigaChat-3-Ultra', 21522, 'completed', 4577, 0, 679),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 40, 'executor', 'GigaChat-3-Ultra', 37752, 'completed', 1619, 3584, 63),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 48, 'executor', 'GigaChat-3-Ultra', 39018, 'completed', 5581, 0, 151),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 56, 'planner_session', 'GigaChat-3-Ultra', 26552, 'completed', 5856, 0, 53),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 75, 'executor', 'GigaChat-3-Ultra', 33219, 'completed', 928, 3584, 58),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 90, 'executor', 'GigaChat-3-Ultra', 33505, 'completed', 1026, 3584, 105),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 105, 'executor', 'GigaChat-3-Ultra', 33199, 'completed', 958, 3584, 25),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 116, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 561, 3584, 55),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 123, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 580, 3584, 75),
    ('Alarm/TASK151A_BENCH/B2_bounded_06/20261001_144417_c10d33', 128, 'verifier_final', 'GigaChat-3-Ultra', 21155, 'completed', 7091, 0, 130),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'completed', 2790, 0, 236),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 19, 'executor', 'GigaChat-3-Ultra', 32853, 'completed', 4353, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 33, 'executor', 'GigaChat-3-Ultra', 34739, 'completed', 4635, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 41, 'executor', 'GigaChat-3-Ultra', 41484, 'completed', 6347, 0, 440),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 49, 'planner_session', 'GigaChat-3-Ultra', 19134, 'completed', 1418, 2368, 57),
    ('Alarm/TASK151A_BENCH/B3_analytical_02/20261001_145638_e02a80', 57, 'verifier_final', 'GigaChat-3-Ultra', 33302, 'completed', 11675, 0, 163),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'parse_error', 2790, 0, 661),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 16, 'planner_session', 'GigaChat-3-Ultra', 17475, 'completed', 1163, 2368, 225),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 28, 'executor', 'GigaChat-3-Ultra', 32753, 'completed', 4276, 64, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 42, 'executor', 'GigaChat-3-Ultra', 34595, 'completed', 4625, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 50, 'executor', 'GigaChat-3-Ultra', 41340, 'completed', 6273, 64, 266),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 58, 'planner_session', 'GigaChat-3-Ultra', 21539, 'parse_error', 4306, 0, 225),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 67, 'planner_session', 'GigaChat-3-Ultra', 23121, 'completed', 2257, 2368, 40),
    ('Alarm/TASK151A_BENCH/B3_analytical_03/20261001_145705_f21296', 75, 'verifier_final', 'GigaChat-3-Ultra', 31979, 'completed', 11341, 448, 136),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'completed', 2790, 0, 254),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 19, 'executor', 'GigaChat-3-Ultra', 32768, 'completed', 4347, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 33, 'executor', 'GigaChat-3-Ultra', 34747, 'completed', 4655, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 41, 'executor', 'GigaChat-3-Ultra', 41492, 'completed', 6303, 64, 394),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 49, 'planner_session', 'GigaChat-3-Ultra', 18641, 'completed', 1394, 2368, 41),
    ('Alarm/TASK151A_BENCH/B3_analytical_04/20261001_145743_fc61a7', 57, 'verifier_final', 'GigaChat-3-Ultra', 34559, 'completed', 12626, 0, 131),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'completed', 422, 2368, 225),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 19, 'executor', 'GigaChat-3-Ultra', 32843, 'completed', 4345, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 33, 'executor', 'GigaChat-3-Ultra', 34660, 'completed', 1034, 3584, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 41, 'executor', 'GigaChat-3-Ultra', 41405, 'completed', 6330, 0, 366),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 49, 'planner_session', 'GigaChat-3-Ultra', 18550, 'parse_error', 3659, 0, 225),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 58, 'planner_session', 'GigaChat-3-Ultra', 20287, 'completed', 1610, 2368, 47),
    ('Alarm/TASK151A_BENCH/B3_analytical_05/20261001_145809_d2a784', 66, 'verifier_final', 'GigaChat-3-Ultra', 35692, 'completed', 13053, 0, 196),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'parse_error', 2790, 0, 670),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 16, 'planner_session', 'GigaChat-3-Ultra', 17444, 'completed', 3540, 0, 229),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 28, 'executor', 'GigaChat-3-Ultra', 32753, 'completed', 4345, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 42, 'executor', 'GigaChat-3-Ultra', 34616, 'completed', 4634, 0, 42),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 50, 'executor', 'GigaChat-3-Ultra', 41361, 'completed', 6346, 0, 304),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 58, 'planner_session', 'GigaChat-3-Ultra', 21760, 'parse_error', 4364, 0, 229),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 67, 'planner_session', 'GigaChat-3-Ultra', 23363, 'completed', 335, 4352, 38),
    ('Alarm/TASK151A_BENCH/B3_analytical_repair_01/20261001_121011_24b22d', 75, 'verifier_final', 'GigaChat-3-Ultra', 22736, 'completed', 6555, 0, 132),
    ('Alarm/TASK151A_BENCH/B3_semantic_01/20261001_005545_dc8d2e', 7, 'planner_session', 'GigaChat-3-Ultra', 13099, 'completed', 351, 2368, 249),
    ('Alarm/TASK151A_BENCH/B3_semantic_02/20261001_005720_8e5145', 7, 'planner_session', 'GigaChat-3-Ultra', 12831, 'parse_error', 2658, 0, 113),
    ('Alarm/TASK151A_BENCH/B3_semantic_02/20261001_005720_8e5145', 16, 'planner_session', 'GigaChat-3-Ultra', 13822, 'completed', 2849, 0, 119),
    ('Alarm/TASK151A_BENCH/B3_semantic_02/20261001_005720_8e5145', 27, 'executor', 'GigaChat-3-Ultra', 31682, 'completed', 4127, 64, 103),
    ('Alarm/TASK151A_BENCH/B3_semantic_02/20261001_005720_8e5145', 35, 'planner_session', 'GigaChat-3-Ultra', 15805, 'completed', 3302, 0, 54),
    ('Alarm/TASK151A_BENCH/B3_semantic_02/20261001_005720_8e5145', 43, 'verifier_final', 'GigaChat-3-Ultra', 7627, 'completed', 1647, 0, 99),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 7, 'planner_session', 'GigaChat-3-Ultra', 13306, 'completed', 2824, 0, 358),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 18, 'executor', 'GigaChat-3-Ultra', 34969, 'completed', 4734, 0, 80),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 26, 'planner_session', 'GigaChat-3-Ultra', 16590, 'completed', 3720, 0, 48),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 45, 'executor', 'GigaChat-3-Ultra', 32227, 'completed', 4330, 0, 43),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 60, 'executor', 'GigaChat-3-Ultra', 32621, 'completed', 4428, 0, 97),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 71, 'executor', 'GigaChat-3-Ultra', 30459, 'completed', 3984, 0, 76),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 78, 'executor', 'GigaChat-3-Ultra', 30583, 'completed', 4003, 0, 84),
    ('Alarm/TASK151B_BENCH/B1_live_01/20261001_154859_053216', 84, 'verifier_final', 'GigaChat-3-Ultra', 33719, 'completed', 13612, 0, 107),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 7, 'planner_session', 'GigaChat-3-Ultra', 14101, 'parse_error', 2999, 0, 575),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 16, 'planner_session', 'GigaChat-3-Ultra', 17136, 'completed', 3642, 0, 760),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 27, 'executor', 'GigaChat-3-Ultra', 37783, 'completed', 5208, 0, 63),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 35, 'executor', 'GigaChat-3-Ultra', 39049, 'completed', 5586, 0, 151),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 43, 'planner_session', 'GigaChat-3-Ultra', 22544, 'completed', 5003, 0, 57),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 62, 'executor', 'GigaChat-3-Ultra', 33281, 'completed', 4526, 0, 58),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 77, 'executor', 'GigaChat-3-Ultra', 33487, 'completed', 4606, 0, 105),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 92, 'executor', 'GigaChat-3-Ultra', 33212, 'completed', 4543, 0, 25),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 103, 'executor', 'GigaChat-3-Ultra', 31209, 'completed', 4144, 0, 55),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 110, 'executor', 'GigaChat-3-Ultra', 31333, 'completed', 4163, 0, 76),
    ('Alarm/TASK151B_BENCH/B2_live_01/20261001_154927_e54fa7', 116, 'verifier_final', 'GigaChat-3-Ultra', 36577, 'completed', 14623, 0, 124),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 7, 'planner_session', 'GigaChat-3-Ultra', 13608, 'completed', 2790, 0, 247),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 19, 'executor', 'GigaChat-3-Ultra', 32750, 'completed', 4344, 0, 42),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 33, 'executor', 'GigaChat-3-Ultra', 34710, 'completed', 4653, 0, 42),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 41, 'executor', 'GigaChat-3-Ultra', 41455, 'completed', 6365, 0, 368),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 49, 'planner_session', 'GigaChat-3-Ultra', 18294, 'completed', 3726, 0, 43),
    ('Alarm/TASK151B_BENCH/B3_live_01/20261001_155015_f999db', 58, 'verifier_final', 'GigaChat-3-Ultra', 38589, 'completed', 14723, 0, 142),
    ('compressor/cmp_20261001_010013_0b5a4b', 1, 'compressor', 'GigaChat-3-Pro', 5568, 'completed', 908, 0, 59),
    ('project/20260930_231415_c918aa', 7, 'planner_session', 'GigaChat-3-Ultra', 13261, 'parse_error', 2732, 0, 751),
    ('project/20260930_231415_c918aa', 16, 'planner_session', 'GigaChat-3-Ultra', 17460, 'parse_error', 3556, 0, 753),
    ('project/20260930_231415_c918aa', 23, 'planner_review', 'GigaChat-3-Ultra', 25332, 'completed', 5100, 0, 112),
    ('project/20260930_231415_c918aa', 29, 'planner_session', 'GigaChat-3-Ultra', 22079, 'parse_error', 4444, 0, 753),
    ('project/20260930_233622_70cc6c', 7, 'planner_session', 'GigaChat-3-Ultra', 13846, 'completed', 2883, 0, 570),
    ('project/20260930_233622_70cc6c', 18, 'executor', 'GigaChat-3-Ultra', 40558, 'completed', 5404, 0, 42),
    ('project/20260930_233622_70cc6c', 26, 'executor', 'GigaChat-3-Ultra', 328393, 'completed', 70189, 0, 70),
    ('project/20260930_233622_70cc6c', 34, 'executor', 'GigaChat-3-Ultra', 329549, 'completed', 70513, 0, 79),
    ('project/20260930_233622_70cc6c', 42, 'executor', 'GigaChat-3-Ultra', 333683, 'completed', 71595, 0, 168),
    ('project/20260930_233733_1f2fee', 7, 'planner_session', 'GigaChat-3-Ultra', 13823, 'completed', 2879, 0, 569),
    ('project/20260930_233733_1f2fee', 18, 'executor', 'GigaChat-3-Ultra', 40537, 'completed', 5405, 0, 42),
    ('project/20260930_233733_1f2fee', 26, 'executor', 'GigaChat-3-Ultra', 328372, 'completed', 70190, 0, 70),
    ('project/20260930_233733_1f2fee', 34, 'executor', 'GigaChat-3-Ultra', 329528, 'completed', 70514, 0, 225),
    ('project/20260930_233733_1f2fee', 41, 'executor', 'GigaChat-3-Ultra', 332302, 'completed', 71204, 0, 78),
    ('project/20260930_233733_1f2fee', 49, 'executor', 'GigaChat-3-Ultra', 335144, 'completed', 1513, 70464, 190),
    ('project/20260930_233733_1f2fee', 56, 'executor', 'GigaChat-3-Ultra', 337695, 'completed', 72632, 0, 79),
    ('project/20260930_233733_1f2fee', 64, 'executor', 'GigaChat-3-Ultra', 339187, 'completed', 73050, 0, 184),
    ('project/20260930_233733_1f2fee', 71, 'executor', 'GigaChat-3-Ultra', 341733, 'completed', 1763, 71936, 79),
    ('project/20260930_233733_1f2fee', 79, 'executor', 'GigaChat-3-Ultra', 343221, 'completed', 74123, 0, 200),
    ('project/20260930_233733_1f2fee', 86, 'executor', 'GigaChat-3-Ultra', 345833, 'completed', 74788, 0, 79),
    ('project/20260930_233733_1f2fee', 94, 'executor', 'GigaChat-3-Ultra', 347417, 'completed', 9687, 65536, 168),
    ('project/20260930_233733_1f2fee', 102, 'planner_session', 'GigaChat-3-Ultra', 18752, 'completed', 4040, 0, 38),
    ('project/20260930_233733_1f2fee', 115, 'executor', 'GigaChat-3-Ultra', 350250, 'completed', 3361, 72576, 77),
    ('project/20260930_233733_1f2fee', 127, 'executor', 'GigaChat-3-Ultra', 354988, 'completed', 77063, 0, 42),
    ('project/20260930_233733_1f2fee', 135, 'executor', 'GigaChat-3-Ultra', 642823, 'completed', 69880, 71936, 168),
    ('project/20260930_233733_1f2fee', 145, 'executor', 'GigaChat-3-Ultra', 643691, 'timeout', None, None, None),
    ('project/20261001_002149_2d20df', 7, 'planner_session', 'GigaChat-3-Ultra', 13823, 'completed', 2879, 0, 554),
    ('project/20261001_002149_2d20df', 18, 'executor', 'GigaChat-3-Ultra', 40536, 'completed', 5405, 0, 42),
    ('project/20261001_002149_2d20df', 26, 'executor', 'GigaChat-3-Ultra', 328371, 'completed', 70190, 0, 70),
    ('project/20261001_002149_2d20df', 34, 'executor', 'GigaChat-3-Ultra', 329527, 'completed', 70450, 64, 225),
    ('project/20261001_002149_2d20df', 41, 'executor', 'GigaChat-3-Ultra', 332301, 'completed', 71140, 64, 79),
    ('project/20261001_002149_2d20df', 49, 'executor', 'GigaChat-3-Ultra', 333858, 'completed', 71641, 0, 171),
    ('project/20261001_002149_2d20df', 57, 'planner_session', 'GigaChat-3-Ultra', 18736, 'completed', 4033, 0, 50),
    ('project/20261001_002149_2d20df', 75, 'executor', 'GigaChat-3-Ultra', 37672, 'completed', 4976, 0, 42),
    ('project/20261001_002149_2d20df', 83, 'executor', 'GigaChat-3-Ultra', 325554, 'completed', 69771, 0, 70),
    ('project/20261001_002149_2d20df', 91, 'executor', 'GigaChat-3-Ultra', 326894, 'completed', 70161, 0, 78),
    ('project/20261001_002149_2d20df', 99, 'executor', 'GigaChat-3-Ultra', 328906, 'completed', 70729, 0, 82),
    ('project/20261001_002149_2d20df', 107, 'executor', 'GigaChat-3-Ultra', 330301, 'completed', 71063, 64, 40),
    ('project/20261001_002149_2d20df', 115, 'executor', 'GigaChat-3-Ultra', 644137, 'completed', 134170, 0, 70),
    ('project/20261001_002149_2d20df', 123, 'executor', 'GigaChat-3-Ultra', 645477, 'completed', 134560, 0, 78),
    ('project/20261001_002149_2d20df', 131, 'executor', 'GigaChat-3-Ultra', 647489, 'completed', 135128, 0, 70),
    ('project/20261001_002149_2d20df', 139, 'executor', 'GigaChat-3-Ultra', 648829, 'completed', 135454, 64, 79),
    ('project/20261001_002149_2d20df', 147, 'executor', 'GigaChat-3-Ultra', 650248, 'completed', 135936, 0, 40),
    ('project/20261001_002149_2d20df', 155, 'executor', 'GigaChat-3-Ultra', 964083, 'completed', 133442, 65536, 70),
    ('project/20261001_002149_2d20df', 163, 'executor', 'GigaChat-3-Ultra', 965423, 'completed', 64264, 135104, 79),
    ('project/20261001_002149_2d20df', 172, 'executor', 'GigaChat-3-Ultra', 964840, 'completed', 128666, 71104, 134),
    ('project/20261001_002149_2d20df', 180, 'planner_session', 'GigaChat-3-Ultra', 20822, 'completed', 4494, 0, 48),
    ('project/20261001_002149_2d20df', 188, 'executor', 'GigaChat-3-Ultra', 967325, 'completed', 509, 199744, 2),
    ('project/20261001_002149_2d20df', 196, 'planner_session', 'GigaChat-3-Ultra', 22329, 'completed', 4815, 0, 48),
    ('project/20261001_002149_2d20df', 204, 'executor', 'GigaChat-3-Ultra', 969230, 'completed', 135068, 65536, 2),
    ('project/20261001_002149_2d20df', 212, 'planner_session', 'GigaChat-3-Ultra', 23836, 'completed', 5136, 0, 48),
    ('project/20261001_004126_824e74', 7, 'planner_session', 'GigaChat-3-Ultra', 13499, 'parse_error', 2837, 0, 438),
    ('project/20261001_004126_824e74', 16, 'planner_session', 'GigaChat-3-Ultra', 16171, 'completed', 3372, 0, 429),
    ('project/20261001_004126_824e74', 27, 'executor', 'GigaChat-3-Ultra', 39089, 'completed', 5121, 64, 85),
    ('project/20261001_004126_824e74', 35, 'executor', 'GigaChat-3-Ultra', 41557, 'completed', 5692, 0, 73),
    ('project/20261001_004126_824e74', 45, 'verifier_permission', 'GigaChat-3-Ultra', 4091, 'completed', 976, 0, 150),
    ('project/20261001_004126_824e74', 50, 'executor', 'GigaChat-3-Ultra', 46289, 'completed', 6605, 64, 183),
    ('project/20261001_004126_824e74', 60, 'planner_session', 'GigaChat-3-Ultra', 20649, 'completed', 4325, 0, 79),
    ('project/20261001_004240_a734f1', 7, 'planner_session', 'GigaChat-3-Ultra', 13521, 'completed', 473, 2368, 540),
    ('project/20261001_004240_a734f1', 18, 'executor', 'GigaChat-3-Ultra', 38309, 'completed', 5091, 0, 86),
    ('project/20261001_004240_a734f1', 26, 'planner_session', 'GigaChat-3-Ultra', 17994, 'completed', 1568, 2368, 58),
    ('project/20261001_004240_a734f1', 45, 'executor', 'GigaChat-3-Ultra', 35653, 'completed', 4698, 0, 51),
    ('project/20261001_004240_a734f1', 60, 'executor', 'GigaChat-3-Ultra', 36018, 'completed', 4794, 0, 82),
    ('project/20261001_004240_a734f1', 67, 'executor', 'GigaChat-3-Ultra', 37052, 'completed', 5064, 0, 103),
    ('project/20261001_004240_a734f1', 78, 'executor', 'GigaChat-3-Ultra', 33710, 'completed', 4333, 0, 77),
    ('project/20261001_004240_a734f1', 85, 'executor', 'GigaChat-3-Ultra', 33834, 'completed', 4352, 0, 66),
    ('project/20261001_004240_a734f1', 90, 'verifier_final', 'GigaChat-3-Ultra', 165539, 'completed', 38057, 0, 129),
    ('project/20261001_004705_96dc2e', 7, 'planner_session', 'GigaChat-3-Ultra', 13889, 'parse_error', 2858, 0, 341),
    ('project/20261001_004705_96dc2e', 16, 'planner_session', 'GigaChat-3-Ultra', 16031, 'completed', 3271, 0, 493),
    ('project/20261001_004705_96dc2e', 28, 'executor', 'GigaChat-3-Ultra', 35795, 'completed', 4616, 64, 42),
    ('project/20261001_004705_96dc2e', 42, 'executor', 'GigaChat-3-Ultra', 37613, 'completed', 4892, 64, 42),
    ('project/20261001_004705_96dc2e', 50, 'executor', 'GigaChat-3-Ultra', 44358, 'completed', 6604, 64, 310),
    ('project/20261001_004705_96dc2e', 58, 'planner_session', 'GigaChat-3-Ultra', 21705, 'completed', 1985, 2368, 48),
    ('project/20261001_004705_96dc2e', 70, 'executor', 'GigaChat-3-Ultra', 40970, 'completed', 5395, 64, 425),
    ('project/20261001_004705_96dc2e', 78, 'planner_session', 'GigaChat-3-Ultra', 25839, 'completed', 2935, 2368, 44),
    ('project/20261001_004705_96dc2e', 94, 'executor', 'GigaChat-3-Ultra', 37269, 'completed', 4816, 64, 310),
    ('project/20261001_004705_96dc2e', 99, 'verifier_final', 'GigaChat-3-Ultra', 171511, 'completed', 38950, 0, 134),
    ('project/20261001_182057_e90f93', 7, 'planner_session', 'GigaChat-3-Ultra', 13684, 'completed', 2882, 0, 511),
    ('project/20261001_182057_e90f93', 18, 'executor', 'GigaChat-3-Ultra', 40352, 'completed', 5409, 0, 63),
    ('project/20261001_182057_e90f93', 26, 'executor', 'GigaChat-3-Ultra', 42743, 'completed', 5949, 0, 38),
    ('project/20261001_182057_e90f93', 34, 'executor', 'GigaChat-3-Ultra', 48325, 'completed', 7361, 0, 54),
    ('project/20261001_182057_e90f93', 42, 'executor', 'GigaChat-3-Ultra', 49622, 'completed', 7686, 0, 79),
    ('project/20261001_182057_e90f93', 50, 'executor', 'GigaChat-3-Ultra', 50830, 'completed', 8040, 0, 78),
    ('project/20261001_182057_e90f93', 58, 'executor', 'GigaChat-3-Ultra', 52158, 'completed', 8431, 0, 59),
    ('project/20261001_182057_e90f93', 66, 'executor', 'GigaChat-3-Ultra', 53580, 'completed', 822, 8000, 42),
    ('project/20261001_182057_e90f93', 74, 'executor', 'GigaChat-3-Ultra', 341415, 'completed', 68199, 5376, 78),
    ('project/20261001_182057_e90f93', 82, 'executor', 'GigaChat-3-Ultra', 342743, 'completed', 73966, 0, 79),
    ('project/20261001_182057_e90f93', 90, 'executor', 'GigaChat-3-Ultra', 343951, 'completed', 400, 73920, 58),
    ('project/20261001_182057_e90f93', 98, 'executor', 'GigaChat-3-Ultra', 345224, 'completed', 74679, 0, 59),
    ('project/20261001_182057_e90f93', 106, 'executor', 'GigaChat-3-Ultra', 346646, 'completed', 75070, 0, 42),
    ('project/20261001_182057_e90f93', 114, 'executor', 'GigaChat-3-Ultra', 634481, 'completed', 64815, 75008, 78),
    ('project/20261001_182057_e90f93', 122, 'executor', 'GigaChat-3-Ultra', 635809, 'completed', 131830, 8384, 79),
    ('project/20261001_182057_e90f93', 131, 'executor', 'GigaChat-3-Ultra', 635066, 'completed', 131782, 8768, 180),
    ('project/20261009_211347_6efe8c', 7, 'planner_session', 'GigaChat-3-Ultra', 12813, 'completed', 2700, 0, 78),
    ('project/20261009_211347_6efe8c', 18, 'executor', 'GigaChat-3-Ultra', 34191, 'completed', 4417, 0, 6),
    ('project/20261009_211347_6efe8c', 26, 'planner_session', 'GigaChat-3-Ultra', 14124, 'completed', 2996, 0, 50),
    ('project/20261009_211347_6efe8c', 35, 'verifier_final', 'GigaChat-3-Ultra', 9135, 'completed', 2203, 0, 90),
    ('project/20261009_211440_30b40f', 4, 'executor', 'GigaChat-3-Ultra', 87714, 'completed', 12778, 0, 11),
    ('project/20261009_211440_30b40f', 9, 'verifier_final', 'GigaChat-3-Ultra', 80382, 'completed', 17331, 0, 93),
    ('project/20261009_223343_3f4fef', 4, 'executor', 'GigaChat-3-Ultra', 87867, 'completed', 12802, 0, 11),
    ('project/20261009_223343_3f4fef', 9, 'verifier_final', 'GigaChat-3-Ultra', 7670, 'completed', 1713, 0, 92),
    ('project/20261009_223401_874b8d', 7, 'planner_session', 'GigaChat-3-Ultra', 12812, 'completed', 2700, 0, 83),
    ('project/20261009_223401_874b8d', 18, 'executor', 'GigaChat-3-Ultra', 34161, 'completed', 4419, 0, 8),
    ('project/20261009_223401_874b8d', 26, 'planner_session', 'GigaChat-3-Ultra', 14083, 'completed', 3007, 0, 52),
    ('project/20261009_223401_874b8d', 35, 'verifier_final', 'GigaChat-3-Ultra', 9141, 'completed', 2210, 0, 114),
    ('project/20261011_011305_5daea2', 7, 'planner_session', 'GigaChat-3-Ultra', 14497, 'completed', 2988, 0, 1419),
    ('project/20261011_011305_5daea2', 18, 'executor', 'GigaChat-3-Ultra', 41134, 'completed', 5498, 0, 38),
    ('project/20261011_011305_5daea2', 26, 'executor', 'GigaChat-3-Ultra', 50764, 'completed', 7979, 0, 43),
    ('project/20261011_011305_5daea2', 34, 'executor', 'GigaChat-3-Ultra', 53024, 'completed', 8434, 0, 79),
    ('project/20261011_011653_d33022', 7, 'planner_session', 'GigaChat-3-Ultra', 13651, 'completed', 2848, 0, 527),
    ('project/20261011_011653_d33022', 18, 'executor', 'GigaChat-3-Ultra', 38419, 'completed', 5097, 0, 81),
    ('project/20261011_011653_d33022', 26, 'planner_session', 'GigaChat-3-Ultra', 17959, 'completed', 3916, 0, 76),
    ('project/20261011_011653_d33022', 45, 'executor', 'GigaChat-3-Ultra', 35772, 'completed', 4706, 0, 48),
    ('project/20261011_011653_d33022', 60, 'executor', 'GigaChat-3-Ultra', 36101, 'completed', 4800, 0, 98),
    ('project/20261011_011653_d33022', 71, 'executor', 'GigaChat-3-Ultra', 33844, 'completed', 4343, 0, 72),
    ('project/20261011_011653_d33022', 78, 'executor', 'GigaChat-3-Ultra', 33968, 'completed', 4362, 0, 64),
    ('project/20261011_011653_d33022', 84, 'verifier_final', 'GigaChat-3-Ultra', 27046, 'completed', 8411, 0, 100),
)

MANIFEST = (
    "CalibrationTests.test_bytes_div_4_underestimates_audit_packets",
    "CalibrationTests.test_calibrated_estimate_covers_every_observation_and_hard_bound_holds",
    "CalibrationTests.test_calibrated_lower_envelopes",
    "CalibrationTests.test_calibration_input_validation",
    "CalibrationTests.test_embedded_dataset_is_pinned",
    "CalibrationTests.test_estimation_modes",
    "CalibrationTests.test_profile_divisor_is_never_rounded_up",
    "CalibrationTests.test_leave_one_out_coverage_by_margin",
    "DecisionTests.test_attempt_budget_counts_retries_replans_and_unknown_attempts",
    "DecisionTests.test_breached_profile_is_not_trusted_again",
    "DecisionTests.test_final_audit_flag_changes_only_the_reserve",
    "DecisionTests.test_full_read_contract_for_s4",
    "DecisionTests.test_per_role_attempt_cap",
    "DecisionTests.test_dredd_role_cap_never_silently_disables_final_audit",
    "DecisionTests.test_request_byte_and_token_caps_with_exact_boundaries",
    "DecisionTests.test_reserve_is_not_a_bypass_of_the_run_cap",
    "DecisionTests.test_route_registry_matches_the_s1_inventory",
    "DecisionTests.test_routes_and_scopes",
    "DecisionTests.test_run_liability_includes_unknown_and_in_flight",
    "DecisionTests.test_small_greeting_request_is_allowed",
    "DecisionTests.test_unknown_model_needs_calibration_or_hard_bound",
    "DecisionTests.test_verification_reserve_is_protected_from_work_but_available_to_final_audit",
    "LiabilityTests.test_estimate_breach_without_reported_precached",
    "DecisionTests.test_preflight_warnings_for_ui_preview",
    "DecisionTests.test_malformed_measure_is_denied_not_trusted",
    "IsolationTests.test_manifest_matches_the_loaded_collection",
    "IsolationTests.test_no_production_module_imports_the_policy_yet",
    "IsolationTests.test_policy_evaluation_does_not_mutate_inputs",
    "IsolationTests.test_policy_module_is_pure",
    "LiabilityTests.test_conflicting_or_invalid_usage_is_an_anomaly",
    "LiabilityTests.test_estimate_breach_is_detected",
    "LiabilityTests.test_known_terminal_settles_to_provider_processed_tokens",
    "LiabilityTests.test_late_known_reconciles_and_duplicates_are_idempotent",
    "LiabilityTests.test_missing_precached_is_not_zero",
    "LiabilityTests.test_orphan_terminal_blocks_the_scope",
    "LiabilityTests.test_unrecognized_or_silent_record_state_is_an_anomaly",
    "LiabilityTests.test_parse_error_with_usage_is_known",
    "LiabilityTests.test_r026_shaped_second_terminal_is_an_anomaly",
    "LiabilityTests.test_reservation_release_requires_proven_not_sent",
    "LiabilityTests.test_unknown_is_never_zero",
    "PolicyValidationTests.test_cross_field_rules",
    "PolicyValidationTests.test_errors_are_human_readable_with_field_paths",
    "PolicyValidationTests.test_no_implicit_defaults_every_section_is_required",
    "PolicyValidationTests.test_policy_has_no_switch_for_planner_history_or_final_audit",
    "PolicyValidationTests.test_profiles_are_validated",
    "PolicyValidationTests.test_scopes_and_output_reserve_modes",
    "PolicyValidationTests.test_units_types_and_ranges_are_strict",
    "PolicyValidationTests.test_unknown_fields_and_versions_are_rejected",
    "PolicyValidationTests.test_valid_policy_and_revision_identity",
    "SyntheticRunTests.test_candidates_stop_the_heavy_runs_and_never_block_normal_ones",
    "SyntheticRunTests.test_greetings_and_live_benches_complete_under_every_candidate",
    "SyntheticRunTests.test_unknown_terminal_keeps_liability_in_replay",
    "SyntheticRunTests.test_candidate_reserves_cover_observed_final_audits_only_up_to_their_size",
    "SyntheticRunTests.test_without_separate_verification_caps_normal_runs_lose_their_final_audit",
    "WireMeasureTests.test_bytes_are_not_characters_and_not_tokens",
    "WireMeasureTests.test_invalid_output_reserve_or_model_is_rejected",
    "WireMeasureTests.test_measure_is_exact_and_bound_to_the_sent_bytes",
    "WireMeasureTests.test_serialized_body_is_byte_identical_to_the_httpx_wire",
)


def setUpModule():
    if not _ISOLATED:
        raise unittest.SkipTest("NOT AN S2 ACCEPTANCE RUN: use the guarded standalone runner")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dataset_digest(rows) -> str:
    return _sha256(json.dumps([list(r) for r in rows], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def calibration_rows():
    import ultra_budget_policy as b
    role = {k: v.role for k, v in b.ROUTES.items()}
    return [b.CalibrationRow(r[3], role[r[2]], r[4], r[6], r[7], r[8]) for r in ROWS if isinstance(r[6], int)]


def profiles(margin=0.1, min_samples=5):
    import ultra_budget_policy as b
    accepted, _report = b.calibrate_profiles(calibration_rows(), margin=margin, source_sha256=DATASET_SHA256,
                                             min_samples=min_samples)
    return accepted


def policy_dict(**run_overrides):
    run = {"max_request_bytes": 524288, "max_request_input_tokens_est": 96000,
           "max_verification_request_bytes": 1114112, "max_verification_request_input_tokens_est": 160000,
           "max_run_liability_tokens": 240000, "max_run_attempts": 32,
           "max_attempts_per_role": {"planner": None, "executor": None, "dredd": None},
           "verification_reserve_tokens": 48000, "verification_reserve_attempts": 2}
    run.update(run_overrides)
    return {"schema_version": 1, "revision_label": "S2 test policy (synthetic, not a default)", "run": run,
            "estimation": {"profiles": profiles(), "missing_profile": "DENY"}, "output_reserve": "MAX_TOKENS",
            "compressor": {"mode": "DENY"}, "mcp": {"mode": "DENY"}, "read": {"max_full_read_bytes": 65536}}


def snapshot(**run_overrides):
    import ultra_budget_policy as b
    return b.validate_policy(policy_dict(**run_overrides))


# Candidate limit sets for the USER DECISION (derived from calibration; NOT defaults, not shipped)
CANDIDATES = {
    "A": dict(max_request_bytes=262144, max_request_input_tokens_est=48000, max_run_liability_tokens=160000,
              max_run_attempts=24, verification_reserve_tokens=40000, verification_reserve_attempts=2,
              max_verification_request_bytes=1114112, max_verification_request_input_tokens_est=120000),
    "B": dict(max_request_bytes=524288, max_request_input_tokens_est=96000, max_run_liability_tokens=240000,
              max_run_attempts=32, verification_reserve_tokens=48000, verification_reserve_attempts=2,
              max_verification_request_bytes=1114112, max_verification_request_input_tokens_est=160000),
    "C": dict(max_request_bytes=1048576, max_request_input_tokens_est=200000, max_run_liability_tokens=480000,
              max_run_attempts=48, verification_reserve_tokens=64000, verification_reserve_attempts=3,
              max_verification_request_bytes=1114112, max_verification_request_input_tokens_est=240000),
}


def recorded_runs():
    runs: dict[str, list] = {}
    for row in ROWS:
        if not row[0].startswith("compressor/"):
            runs.setdefault(row[0], []).append(row)
    return {key: sorted(items, key=lambda r: r[1]) for key, items in runs.items()}


def simulate_run(snap, rows, *, final_audit_enabled=True):
    """Replay a recorded RUN through the pure engine: decide, reserve, send, settle with recorded usage."""
    import ultra_budget_policy as b
    attempts = []
    for index, row in enumerate(rows, 1):
        measure = b.RequestMeasure(row[2], row[3], row[4], "0" * 64, ROUTE_MAX_TOKENS[row[2]])
        decision = b.evaluate_request(snap, attempts, measure, b.RunContext("run", final_audit_enabled))
        if decision.verdict != b.ALLOW:
            return {"blocked_at": index, "attempts": len(rows), "codes": [r.code for r in decision.reasons],
                    "committed": decision.view.committed_liability_tokens if decision.view else None}
        record = b.mark_sent(b.reserve_attempt(f"a{index}", measure, decision.estimate, "run"))
        usage = None if row[6] is None else {"prompt_tokens": row[6], "completion_tokens": row[8],
                                             "precached_prompt_tokens": row[7]}
        attempts.append(b.apply_terminal(record, row[5] or "timeout", usage))
    view = b.budget_view(snap, attempts, "run", final_audit_enabled=final_audit_enabled)
    return {"blocked_at": None, "attempts": len(rows), "codes": [], "committed": view.committed_liability_tokens}


def run_label(key):
    return RUN_NAMES.get(key, key)


# --------------------------------------------------------------------------- exact measurement

class WireMeasureTests(unittest.TestCase):
    BODIES = [
        {"model": "GigaChat-3-Ultra", "messages": [{"role": "user", "content": "привет"}], "temperature": 0.15,
         "max_tokens": 32768, "stream": False},
        {"z": 1, "model": "GigaChat-3-Ultra", "a": [1, 2, {"ё": "✓"}], "max_tokens": 160,
         "messages": [{"role": "system", "content": "x" * 3000}, {"role": "function", "name": "read_file",
                                                                  "content": json.dumps({"c": "Ж" * 500})}],
         "functions": [{"name": "read_file", "parameters": {"type": "object",
                                                           "properties": {"path": {"type": "string"}}}}],
         "function_call": "auto"},
    ]

    def test_serialized_body_is_byte_identical_to_the_httpx_wire(self):
        import httpx
        import ultra_budget_policy as b
        for body in self.BODIES:
            with self.subTest(keys=list(body)[:3]):
                request = httpx.Request("POST", "https://api.giga.chat/v1/chat/completions", json=body)
                self.assertEqual(b.serialize_request_body(body), request.content)
                self.assertEqual(int(request.headers["content-length"]), len(request.content))

    def test_measure_is_exact_and_bound_to_the_sent_bytes(self):
        import ultra_budget_policy as b
        body = self.BODIES[1]
        measure = b.measure_request("audit_diagnostic", body)
        data = b.serialize_request_body(body)
        self.assertEqual((measure.wire_bytes, measure.wire_sha256, measure.output_reserve_tokens),
                         (len(data), _sha256(data), 160))
        reordered = dict(reversed(list(body.items())))
        self.assertEqual(b.measure_request("audit_diagnostic", reordered).wire_bytes, measure.wire_bytes)
        self.assertNotEqual(b.measure_request("audit_diagnostic", reordered).wire_sha256, measure.wire_sha256)

    def test_bytes_are_not_characters_and_not_tokens(self):
        import ultra_budget_policy as b
        ascii_body = {"model": "m", "max_tokens": 1, "messages": [{"role": "user", "content": "a" * 1000}]}
        cyr_body = {"model": "m", "max_tokens": 1, "messages": [{"role": "user", "content": "я" * 1000}]}
        self.assertEqual(b.measure_request("executor", cyr_body).wire_bytes
                         - b.measure_request("executor", ascii_body).wire_bytes, 1000)

    def test_invalid_output_reserve_or_model_is_rejected(self):
        import ultra_budget_policy as b
        for bad in ({"model": "m", "messages": []}, {"model": "m", "max_tokens": 0}, {"model": "m", "max_tokens": True},
                    {"model": "", "max_tokens": 5}, {"max_tokens": 5}):
            with self.subTest(body=bad):
                with self.assertRaises(b.PolicyInputError):
                    b.measure_request("executor", bad)


# --------------------------------------------------------------------------- policy schema

class PolicyValidationTests(unittest.TestCase):
    def assert_invalid(self, raw, fragment):
        import ultra_budget_policy as b
        with self.assertRaises(b.PolicyValidationError) as ctx:
            b.validate_policy(raw)
        self.assertTrue(any(fragment in p for p in ctx.exception.problems), ctx.exception.problems)

    def test_valid_policy_and_revision_identity(self):
        snap = snapshot()
        again = snapshot()
        self.assertEqual(snap.revision_sha256, again.revision_sha256)
        self.assertNotEqual(snapshot(max_run_attempts=33).revision_sha256, snap.revision_sha256)
        self.assertEqual(len(snap.revision_sha256), 64)

    def test_no_implicit_defaults_every_section_is_required(self):
        for key in ("run", "estimation", "output_reserve", "compressor", "mcp", "read", "revision_label"):
            with self.subTest(missing=key):
                raw = policy_dict()
                del raw[key]
                self.assert_invalid(raw, key)
        raw = policy_dict()
        del raw["run"]["max_run_attempts"]
        self.assert_invalid(raw, "max_run_attempts")

    def test_units_types_and_ranges_are_strict(self):
        cases = {
            "string with unit": ("max_request_bytes", "512KB"), "float": ("max_request_bytes", 512.0),
            "bool": ("max_run_attempts", True), "negative": ("max_run_liability_tokens", -1),
            "zero": ("max_run_attempts", 0), "overflow": ("max_request_bytes", (1 << 30) + 1),
            "huge tokens": ("max_run_liability_tokens", 10 ** 10 + 1), "none": ("max_request_bytes", None),
        }
        for name, (field_name, value) in cases.items():
            with self.subTest(case=name):
                raw = policy_dict()
                raw["run"][field_name] = value
                self.assert_invalid(raw, field_name)

    def test_unknown_fields_and_versions_are_rejected(self):
        raw = policy_dict()
        raw["run"]["max_request_megabytes"] = 1
        self.assert_invalid(raw, "max_request_megabytes")
        raw = policy_dict()
        raw["schema_version"] = 2
        self.assert_invalid(raw, "schema_version")
        raw = policy_dict()
        raw["schema_version"] = True
        self.assert_invalid(raw, "schema_version")

    def test_cross_field_rules(self):
        self.assert_invalid(policy_dict(verification_reserve_tokens=240000), "verification_reserve_tokens")
        self.assert_invalid(policy_dict(verification_reserve_attempts=32), "verification_reserve_attempts")
        self.assert_invalid(policy_dict(max_request_input_tokens_est=240001), "max_request_input_tokens_est")
        self.assert_invalid(policy_dict(max_verification_request_input_tokens_est=240001),
                            "max_verification_request_input_tokens_est")

    def test_profiles_are_validated(self):
        good = profiles()[0]
        cases = {"nan": {"bytes_per_token": float("nan")}, "inf": {"bytes_per_token": float("inf")},
                 "zero": {"bytes_per_token": 0}, "negative": {"bytes_per_token": -1.0},
                 "too large": {"bytes_per_token": 65.0}, "bool": {"bytes_per_token": True},
                 "role": {"profile_key": "auth"}, "sha": {"source_sha256": "xyz"}, "samples": {"samples": 0}}
        for name, change in cases.items():
            with self.subTest(case=name):
                raw = policy_dict()
                raw["estimation"]["profiles"] = [dict(good, **change)]
                self.assert_invalid(raw, "profiles[0]")
        raw = policy_dict()
        raw["estimation"]["profiles"] = [good, dict(good)]
        self.assert_invalid(raw, "повторный профиль")
        raw = policy_dict()
        raw["estimation"]["missing_profile"] = "OPTIMISTIC"
        self.assert_invalid(raw, "missing_profile")

    def test_scopes_and_output_reserve_modes(self):
        raw = policy_dict()
        raw["mcp"] = {"mode": "DENY", "max_request_bytes": 1}
        self.assert_invalid(raw, "policy.mcp.max_request_bytes")
        raw = policy_dict()
        raw["compressor"] = {"mode": "BUDGET", "max_request_bytes": 1000}
        self.assert_invalid(raw, "policy.compressor.max_scope_attempts")
        raw = policy_dict()
        raw["output_reserve"] = "OBSERVED_P99"
        self.assert_invalid(raw, "output_reserve")

    def test_errors_are_human_readable_with_field_paths(self):
        import ultra_budget_policy as b
        raw = policy_dict(max_run_attempts="много")
        with self.assertRaises(b.PolicyValidationError) as ctx:
            b.validate_policy(raw)
        self.assertIn("policy.run.max_run_attempts: ожидается целое число", str(ctx.exception))

    def test_policy_has_no_switch_for_planner_history_or_final_audit(self):
        raw = policy_dict()
        flat = json.dumps(raw).lower()
        for forbidden in ("planner_enabled", "final_audit_enabled", "history_enabled", "dredd_enabled"):
            self.assertNotIn(forbidden, flat)


# --------------------------------------------------------------------------- estimation and calibration

class CalibrationTests(unittest.TestCase):
    def test_embedded_dataset_is_pinned(self):
        self.assertEqual(dataset_digest(ROWS), DATASET_SHA256)
        self.assertEqual((len(ROWS), sum(1 for r in ROWS if isinstance(r[6], int))), (342, 340))
        self.assertEqual(len({r[0] for r in ROWS}), 42)

    def test_calibrated_lower_envelopes(self):
        import ultra_budget_policy as b
        _accepted, report = b.calibrate_profiles(calibration_rows(), margin=0.0, source_sha256=DATASET_SHA256,
                                                 min_samples=5)
        floors = {(e["profile_key"], e["samples"]): e["observed_min_bytes_per_token"] for e in report}
        self.assertEqual(floors, {("compressor", 1): 6.1322, ("dredd", 37): 2.4772, ("executor", 203): 4.5184,
                                  ("planner", 99): 4.4426})
        status = {e["profile_key"]: e["status"] for e in report}
        self.assertEqual(status["compressor"], "NEEDS_CALIBRATION")  # 1 sample < min_samples
        _OBSERVATIONS["calibration_report_margin_0"] = report

    def test_bytes_div_4_underestimates_audit_packets(self):
        rows = calibration_rows()
        import ultra_budget_policy as b
        under = {}
        for row in rows:
            if math.ceil(row.wire_bytes / 4) < b.processed_input_tokens(row):
                under[row.profile_key] = under.get(row.profile_key, 0) + 1
        worst = max(b.processed_input_tokens(r) / math.ceil(r.wire_bytes / 4) for r in rows)
        self.assertEqual(under, {"dredd": 24})
        self.assertAlmostEqual(worst, 1.615, places=3)
        _OBSERVATIONS["bytes_div_4"] = {"underestimates": under, "worst_actual_over_estimate": round(worst, 4)}

    def test_leave_one_out_coverage_by_margin(self):
        import ultra_budget_policy as b
        groups: dict = {}
        for row in calibration_rows():
            groups.setdefault(row.profile_key, []).append(row)
        result = {}
        for margin in (0.0, 0.1, 0.2):
            for key, items in groups.items():
                if len(items) < 5:
                    continue
                under, over = 0, []
                for i, held in enumerate(items):
                    rest = items[:i] + items[i + 1:]
                    floor = min(r.wire_bytes / b.processed_input_tokens(r) for r in rest)
                    estimate = math.ceil(held.wire_bytes / (floor / (1 + margin)))
                    under += estimate < b.processed_input_tokens(held)
                    over.append(estimate / b.processed_input_tokens(held))
                over.sort()
                result[(margin, key)] = (under, round(over[len(over) // 2], 2))
        self.assertEqual({k: v[0] for k, v in result.items() if k[0] == 0.0},
                         {(0.0, "dredd"): 1, (0.0, "executor"): 1, (0.0, "planner"): 1})
        self.assertEqual({k: v[0] for k, v in result.items() if k[0] > 0}, {k: 0 for k in result if k[0] > 0})
        _OBSERVATIONS["leave_one_out"] = {f"{m}/{k}": v for (m, k), v in result.items()}

    def test_calibrated_estimate_covers_every_observation_and_hard_bound_holds(self):
        import ultra_budget_policy as b
        snap = snapshot()
        for row in calibration_rows():
            if row.profile_key == "compressor":
                continue
            estimate = b.estimate_input_tokens(snap, row.provider_model_id, row.profile_key, row.wire_bytes)
            self.assertEqual(estimate.status, b.EST_CALIBRATED)
            self.assertGreaterEqual(estimate.tokens, b.processed_input_tokens(row))
            self.assertGreaterEqual(row.wire_bytes, b.processed_input_tokens(row))  # A-BYTE assumption observed

    def test_profile_divisor_is_never_rounded_up(self):
        import ultra_budget_policy as b
        # 247716 / 100000 = 2.47716: a 4-decimal round() would give 2.4772 and under-cover this very sample
        rows = [b.CalibrationRow("M", "executor", 247716, 100000, 0, 1)] * 5 + calibration_rows()
        for margin in (0.0, 0.1):
            accepted, _report = b.calibrate_profiles(rows, margin=margin, source_sha256=DATASET_SHA256, min_samples=5)
            raw = policy_dict()
            raw["estimation"]["profiles"] = accepted
            snap = b.validate_policy(raw)
            for row in rows:
                if row.profile_key == "compressor":
                    continue
                with self.subTest(margin=margin, model=row.provider_model_id, key=row.profile_key):
                    estimate = b.estimate_input_tokens(snap, row.provider_model_id, row.profile_key, row.wire_bytes)
                    self.assertGreaterEqual(estimate.tokens, b.processed_input_tokens(row))
        self.assertEqual(next(p["bytes_per_token"] for p in b.calibrate_profiles(
            rows, margin=0.0, source_sha256=DATASET_SHA256, min_samples=5)[0] if p["provider_model_id"] == "M"),
            2.4771)

    def test_estimation_modes(self):
        import ultra_budget_policy as b
        snap = snapshot()
        self.assertEqual(b.estimate_input_tokens(snap, "GigaChat-3-Pro", "compressor", 6000).status,
                         b.EST_NEEDS_CALIBRATION)
        raw = policy_dict()
        raw["estimation"]["missing_profile"] = "HARD_BOUND"
        hard = b.validate_policy(raw)
        estimate = b.estimate_input_tokens(hard, "GigaChat-Unknown", "executor", 12345)
        self.assertEqual((estimate.tokens, estimate.status), (12345, b.EST_HARD_BOUND))
        breached = b.estimate_input_tokens(snap, "GigaChat-3-Ultra", "executor", 1000,
                                           breached={("GigaChat-3-Ultra", "executor")})
        self.assertEqual(breached.status, b.EST_NEEDS_CALIBRATION)
        same_bytes = [b.estimate_input_tokens(snap, "GigaChat-3-Ultra", key, 100000).tokens
                      for key in ("executor", "planner", "dredd")]
        self.assertEqual(len(set(same_bytes)), 3)  # bytes alone do not determine tokens
        with self.assertRaises(b.PolicyInputError):
            b.estimate_input_tokens(snap, "GigaChat-3-Ultra", "executor", -1)

    def test_calibration_input_validation(self):
        import ultra_budget_policy as b
        for bad in ({"margin": -0.1}, {"margin": True}, {"margin": 11}, {"min_samples": 0}):
            with self.subTest(bad=bad):
                args = {"margin": 0.1, "min_samples": 5, **bad}
                with self.assertRaises(b.PolicyInputError):
                    b.calibrate_profiles([], source_sha256=DATASET_SHA256, **args)


# --------------------------------------------------------------------------- liability semantics

class LiabilityTests(unittest.TestCase):
    def record(self, estimate=1000, output=500):
        import ultra_budget_policy as b
        measure = b.RequestMeasure("executor", "GigaChat-3-Ultra", 4000, "0" * 64, output)
        return b.reserve_attempt("a1", measure, b.TokenEstimate(estimate, b.EST_CALIBRATED, None, ""), "run")

    def test_known_terminal_settles_to_provider_processed_tokens(self):
        import ultra_budget_policy as b
        sent = b.mark_sent(self.record())
        self.assertEqual((sent.state, sent.liability_tokens), (b.SENT, 1500))
        known = b.apply_terminal(sent, "completed", {"prompt_tokens": 400, "completion_tokens": 50,
                                                     "precached_prompt_tokens": 300, "total_tokens": 450})
        self.assertEqual((known.state, known.liability_tokens), (b.KNOWN_TERMINAL, 750))

    def test_unknown_is_never_zero(self):
        import ultra_budget_policy as b
        for outcome, usage in (("timeout", None), ("transport_error", None), ("cancelled", None),
                               ("provider_error", None), ("completed", None), ("parse_error", None),
                               ("completed", {"other": 1})):
            with self.subTest(outcome=outcome, usage=usage):
                settled = b.apply_terminal(b.mark_sent(self.record()), outcome, usage)
                self.assertEqual((settled.state, settled.liability_tokens), (b.UNKNOWN_TERMINAL, 1500))

    def test_parse_error_with_usage_is_known(self):
        import ultra_budget_policy as b
        settled = b.apply_terminal(b.mark_sent(self.record()), "parse_error",
                                   {"prompt_tokens": 100, "completion_tokens": 9, "precached_prompt_tokens": 0})
        self.assertEqual((settled.state, settled.liability_tokens), (b.KNOWN_TERMINAL, 109))

    def test_late_known_reconciles_and_duplicates_are_idempotent(self):
        import ultra_budget_policy as b
        unknown = b.apply_terminal(b.mark_sent(self.record()), "timeout", None)
        duplicate = b.apply_terminal(unknown, "timeout", None)
        self.assertEqual((duplicate.state, duplicate.liability_tokens), (b.UNKNOWN_TERMINAL, 1500))
        usage = {"prompt_tokens": 600, "completion_tokens": 20, "precached_prompt_tokens": 0}
        late = b.apply_terminal(duplicate, "completed", usage)
        self.assertEqual((late.state, late.liability_tokens), (b.RECONCILED, 620))
        again = b.apply_terminal(late, "completed", usage)
        self.assertEqual((again.state, again.liability_tokens), (b.RECONCILED, 620))

    def test_conflicting_or_invalid_usage_is_an_anomaly(self):
        import ultra_budget_policy as b
        known = b.apply_terminal(b.mark_sent(self.record()), "completed",
                                 {"prompt_tokens": 10, "completion_tokens": 1, "precached_prompt_tokens": 0})
        conflict = b.apply_terminal(known, "completed", {"prompt_tokens": 11, "completion_tokens": 1,
                                                         "precached_prompt_tokens": 0})
        self.assertEqual(conflict.state, b.ANOMALY)
        for bad in ({"prompt_tokens": -1, "completion_tokens": 0}, {"prompt_tokens": True, "completion_tokens": 0},
                    {"prompt_tokens": 1.5, "completion_tokens": 0}, {"prompt_tokens": "7", "completion_tokens": 0},
                    {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 7},
                    {"prompt_tokens": 5, "completion_tokens": 1, "precached_prompt_tokens": -3}, [1, 2]):
            with self.subTest(usage=bad):
                settled = b.apply_terminal(b.mark_sent(self.record()), "completed", bad)
                self.assertEqual(settled.state, b.ANOMALY)
                self.assertGreaterEqual(settled.liability_tokens, 1500)

    def test_r026_shaped_second_terminal_is_an_anomaly(self):
        import ultra_budget_policy as b
        unknown = b.apply_terminal(b.mark_sent(self.record()), "timeout", None)
        self.assertEqual(b.apply_terminal(unknown, "aborted_external_recovery", None).state, b.ANOMALY)

    def test_reservation_release_requires_proven_not_sent(self):
        import ultra_budget_policy as b
        released = b.mark_not_sent(self.record())
        self.assertEqual((released.state, released.liability_tokens), (b.NOT_SENT, 0))
        sent = b.mark_sent(self.record())
        self.assertEqual(b.mark_not_sent(sent).state, b.ANOMALY)
        self.assertEqual(b.mark_sent(sent).state, b.ANOMALY)
        self.assertEqual(b.apply_terminal(self.record(), "completed", None).state, b.ANOMALY)  # never sent

    def test_missing_precached_is_not_zero(self):
        import ultra_budget_policy as b
        settled = b.apply_terminal(b.mark_sent(self.record(estimate=1000)), "completed",
                                   {"prompt_tokens": 400, "completion_tokens": 50})
        self.assertEqual((settled.state, settled.liability_tokens), (b.KNOWN_TERMINAL, 1050))  # max(400, 1000) + 50

    def test_estimate_breach_is_detected(self):
        import ultra_budget_policy as b
        settled = b.apply_terminal(b.mark_sent(self.record(estimate=1000)), "completed",
                                   {"prompt_tokens": 900, "completion_tokens": 5, "precached_prompt_tokens": 200})
        self.assertTrue(settled.estimate_breached)
        self.assertEqual(settled.liability_tokens, 1105)

    def test_estimate_breach_without_reported_precached(self):
        import ultra_budget_policy as b
        settled = b.apply_terminal(b.mark_sent(self.record(estimate=1000)), "completed",
                                   {"prompt_tokens": 1200, "completion_tokens": 5})
        self.assertTrue(settled.estimate_breached)
        within = b.apply_terminal(b.mark_sent(self.record(estimate=1000)), "completed",
                                  {"prompt_tokens": 900, "completion_tokens": 5})
        self.assertFalse(within.estimate_breached)

    def test_orphan_terminal_blocks_the_scope(self):
        import ultra_budget_policy as b
        orphan = b.orphan_terminal_record("ghost", "run", "completed", {"prompt_tokens": 1, "completion_tokens": 1})
        measure = b.RequestMeasure("executor", "GigaChat-3-Ultra", 1000, "0" * 64, 32768)
        decision = b.evaluate_request(snapshot(), [orphan], measure, b.RunContext("run", True))
        self.assertEqual((decision.verdict, decision.reasons[0].code), (b.DENY, "LEDGER_ANOMALY"))

    def test_unrecognized_or_silent_record_state_is_an_anomaly(self):
        """S3a will rehydrate records from storage: a corrupt state must block, never drop its liability."""
        import ultra_budget_policy as b
        measure = b.RequestMeasure("executor", "GigaChat-3-Ultra", 1000, "0" * 64, 32768)
        reserved = b.reserve_attempt("r", measure, b.TokenEstimate(5000, b.EST_CALIBRATED, None, ""), "run")
        for state in ("SETTLED", "known_terminal", b.ANOMALY):
            with self.subTest(state=state):
                record = replace(reserved, state=state)  # ANOMALY without a recorded explanation
                view = b.budget_view(snapshot(), [record], "run", final_audit_enabled=True)
                self.assertEqual(view.committed_liability_tokens, 5000 + 32768)
                decision = b.evaluate_request(snapshot(), [record], measure, b.RunContext("run", True))
                self.assertEqual((decision.verdict, decision.reasons[0].code), (b.DENY, "LEDGER_ANOMALY"))


# --------------------------------------------------------------------------- decisions

class DecisionTests(unittest.TestCase):
    def measure(self, route="executor", wire_bytes=35000, model="GigaChat-3-Ultra", output=None):
        import ultra_budget_policy as b
        return b.RequestMeasure(route, model, wire_bytes, "0" * 64,
                                output if output is not None else ROUTE_MAX_TOKENS[route])

    def decide(self, measure, attempts=(), snap=None, final_audit=True, scope="run"):
        import ultra_budget_policy as b
        return b.evaluate_request(snap or snapshot(), list(attempts), measure, b.RunContext(scope, final_audit))

    def settled(self, index, route, tokens, scope="run"):
        import ultra_budget_policy as b
        measure = self.measure(route, wire_bytes=4000)
        record = b.mark_sent(b.reserve_attempt(f"s{index}", measure, b.TokenEstimate(tokens, b.EST_CALIBRATED,
                                                                                     None, ""), scope))
        return b.apply_terminal(record, "completed", {"prompt_tokens": tokens, "completion_tokens": 0,
                                                      "precached_prompt_tokens": 0})

    def test_small_greeting_request_is_allowed(self):
        import ultra_budget_policy as b
        decision = self.decide(self.measure(wire_bytes=34191))
        self.assertEqual(decision.verdict, b.ALLOW)
        self.assertEqual(decision.reservation_liability_tokens, decision.estimate.tokens + 32768)

    def test_request_byte_and_token_caps_with_exact_boundaries(self):
        import ultra_budget_policy as b
        snap = snapshot(max_request_bytes=100000, max_request_input_tokens_est=96000)
        self.assertEqual(self.decide(self.measure(wire_bytes=100000), snap=snap).verdict, b.ALLOW)
        over = self.decide(self.measure(wire_bytes=100001), snap=snap)
        self.assertEqual([r.code for r in over.reasons], ["REQUEST_BYTES_EXCEEDED"])
        bpt = next(p.bytes_per_token for p in snap.profiles if p.profile_key == "executor")
        limit_bytes = math.floor(20000 * bpt)
        snap_tokens = snapshot(max_request_bytes=524288, max_request_input_tokens_est=20000)
        self.assertEqual(self.decide(self.measure(wire_bytes=limit_bytes), snap=snap_tokens).verdict, b.ALLOW)
        self.assertIn("REQUEST_TOKENS_EXCEEDED",
                      [r.code for r in self.decide(self.measure(wire_bytes=limit_bytes + 5), snap=snap_tokens).reasons])

    def test_run_liability_includes_unknown_and_in_flight(self):
        import ultra_budget_policy as b
        snap = snapshot()
        unknown = b.apply_terminal(b.mark_sent(b.reserve_attempt(
            "u", self.measure(wire_bytes=4000), b.TokenEstimate(100000, b.EST_CALIBRATED, None, ""), "run")),
            "timeout", None)
        in_flight = b.mark_sent(b.reserve_attempt(
            "f", self.measure(wire_bytes=4000), b.TokenEstimate(20000, b.EST_CALIBRATED, None, ""), "run"))
        decision = self.decide(self.measure(wire_bytes=35000), [unknown, in_flight], snap)
        self.assertEqual(decision.view.unknown_liability_tokens, 100000 + 32768)
        self.assertEqual(decision.view.in_flight_liability_tokens, 20000 + 32768)
        self.assertEqual(decision.verdict, b.DENY)
        self.assertIn(decision.reasons[0].code, {"RUN_LIABILITY_EXCEEDED", "VERIFICATION_RESERVE_PROTECTED"})

    def test_verification_reserve_is_protected_from_work_but_available_to_final_audit(self):
        import ultra_budget_policy as b
        snap = snapshot()  # cap 240000, reserve 48000; executor 4000 B -> 974 est + 32768 output
        history = [self.settled(1, "executor", 170000)]  # 170000+33742 fits; +48000 reserve does not
        work = self.decide(self.measure("executor", wire_bytes=4000), history, snap)
        self.assertEqual([r.code for r in work.reasons], ["VERIFICATION_RESERVE_PROTECTED"])
        audit = self.decide(self.measure("verifier_final", wire_bytes=40000), history, snap)
        self.assertEqual(audit.verdict, b.ALLOW)
        no_audit = self.decide(self.measure("executor", wire_bytes=4000), history, snap, final_audit=False)
        self.assertEqual(no_audit.verdict, b.ALLOW)  # without Final Audit nothing is reserved for it

    def test_reserve_is_not_a_bypass_of_the_run_cap(self):
        import ultra_budget_policy as b
        history = [self.settled(1, "executor", 236000)]
        audit = self.decide(self.measure("verifier_final", wire_bytes=40000), history)
        self.assertEqual(audit.verdict, b.DENY)
        self.assertEqual(audit.consequence, "NO_SUCCESS_WITHOUT_AUDIT")
        diag = self.decide(self.measure("audit_diagnostic", wire_bytes=4000),  # 974 est + 160 output
                           [self.settled(1, "executor", 195000)])
        self.assertEqual(diag.verdict, b.DENY)  # optional diagnostic cannot use the verification reserve

    def test_attempt_budget_counts_retries_replans_and_unknown_attempts(self):
        import ultra_budget_policy as b
        snap = snapshot(max_run_attempts=5, verification_reserve_attempts=1)
        history = [self.settled(i, "planner_session" if i % 2 else "executor", 100) for i in range(3)]
        unknown = b.apply_terminal(b.mark_sent(b.reserve_attempt(
            "u", self.measure(wire_bytes=4000), b.TokenEstimate(100, b.EST_CALIBRATED, None, ""), "run")),
            "timeout", None)
        released = b.mark_not_sent(b.reserve_attempt(
            "n", self.measure(wire_bytes=4000), b.TokenEstimate(100, b.EST_CALIBRATED, None, ""), "run"))
        decision = self.decide(self.measure("planner_session", wire_bytes=4000), history + [unknown, released], snap)
        self.assertEqual(decision.view.attempts_used, 4)  # NOT_SENT does not count, UNKNOWN does
        self.assertEqual([r.code for r in decision.reasons], ["VERIFICATION_RESERVE_PROTECTED"])
        self.assertEqual(self.decide(self.measure("verifier_final", wire_bytes=4000), history + [unknown],
                                     snap).verdict, b.ALLOW)

    def test_per_role_attempt_cap(self):
        raw_snap = snapshot(max_attempts_per_role={"planner": 2, "executor": None, "dredd": None})
        history = [self.settled(i, "planner_session", 10) for i in range(2)]
        decision = self.decide(self.measure("planner_session", wire_bytes=4000), history, raw_snap)
        self.assertIn("ROLE_ATTEMPTS_EXCEEDED", [r.code for r in decision.reasons])

    def test_dredd_role_cap_never_silently_disables_final_audit(self):
        import ultra_budget_policy as b
        snap = snapshot(max_attempts_per_role={"planner": None, "executor": None, "dredd": 2})
        work = [self.settled(1, "verifier_permission", 10), self.settled(2, "planner_review", 10)]
        self.assertEqual([r.code for r in self.decide(self.measure("verifier_permission", wire_bytes=4000), work,
                                                      snap).reasons], ["ROLE_ATTEMPTS_EXCEEDED"])
        audit = self.decide(self.measure("verifier_final", wire_bytes=4000), work, snap)
        self.assertEqual(audit.verdict, b.ALLOW)  # bounded by the RUN caps and its protected reserve instead
        after_audit = [self.settled(1, "verifier_permission", 10), self.settled(3, "verifier_final", 10)]
        self.assertEqual(self.decide(self.measure("planner_review", wire_bytes=4000), after_audit, snap).verdict,
                         b.ALLOW)  # a Final Audit attempt does not consume the dredd work cap
        self.assertEqual(self.decide(self.measure("planner_review", wire_bytes=4000), after_audit, snap)
                         .view.attempts_used, 2)  # it still counts against the RUN attempt cap

    def test_unknown_model_needs_calibration_or_hard_bound(self):
        import ultra_budget_policy as b
        decision = self.decide(self.measure(model="GigaChat-4-Future"))
        self.assertEqual((decision.verdict, decision.reasons[-1].code), (b.DENY, b.EST_NEEDS_CALIBRATION))
        raw = policy_dict()
        raw["estimation"]["missing_profile"] = "HARD_BOUND"
        hard = self.decide(self.measure(model="GigaChat-4-Future", wire_bytes=4000), snap=b.validate_policy(raw))
        self.assertEqual((hard.verdict, hard.estimate.tokens), (b.ALLOW, 4000))

    def test_breached_profile_is_not_trusted_again(self):
        import ultra_budget_policy as b
        breach = b.apply_terminal(b.mark_sent(b.reserve_attempt(
            "x", self.measure(wire_bytes=4000), b.TokenEstimate(100, b.EST_CALIBRATED, None, ""), "run")),
            "completed", {"prompt_tokens": 500, "completion_tokens": 1, "precached_prompt_tokens": 0})
        decision = self.decide(self.measure(wire_bytes=4000), [breach])
        self.assertEqual(decision.reasons[-1].code, b.EST_NEEDS_CALIBRATION)

    def test_routes_and_scopes(self):
        import ultra_budget_policy as b
        self.assertEqual(self.decide(self.measure("oauth", output=1)).verdict, b.NOT_APPLICABLE)
        self.assertEqual(self.decide(self.measure("mystery", output=1)).reasons[0].code, "UNKNOWN_ROUTE")
        mcp = self.decide(self.measure("mcp_chat", wire_bytes=200), scope="mcp-session")
        self.assertEqual(mcp.reasons[0].code, "ROUTE_DISABLED_BY_POLICY")
        raw = policy_dict()
        raw["compressor"] = {"mode": "BUDGET", "max_request_bytes": 20000, "max_request_input_tokens_est": 8000,
                             "max_scope_liability_tokens": 60000, "max_scope_attempts": 2}
        raw["estimation"]["missing_profile"] = "HARD_BOUND"
        snap = b.validate_policy(raw)
        first = self.decide(self.measure("compressor", wire_bytes=5000, model="GigaChat-3-Pro", output=8000),
                            snap=snap, scope="compress-job")
        self.assertEqual(first.verdict, b.ALLOW)
        run_history = [self.settled(i, "executor", 10) for i in range(30)]  # RUN attempts do not leak into a job
        job = self.decide(self.measure("compressor", wire_bytes=5000, model="GigaChat-3-Pro", output=8000),
                          run_history, snap=snap, scope="compress-job")
        self.assertEqual(job.view.attempts_used, 0)

    def test_route_registry_matches_the_s1_inventory(self):
        import ultra_budget_policy as b
        self.assertEqual(set(ROUTE_SEND_SITES), set(b.ROUTES))
        expected = {(m, o, t) for (m, o, _k, t) in s1.EXPECTED_SEND_SITES}
        self.assertEqual({(m, o, "OAUTH" if r == "oauth" else "LLM") for r, (m, o) in ROUTE_SEND_SITES.items()},
                         expected)
        # call-site names stay in the runtime and in tests (S1 forbids e.g. ask_gigachat outside server.py)
        text = Path(b.__file__).read_text(encoding="utf-8")
        self.assertEqual([o for (_m, o) in ROUTE_SEND_SITES.values() if o in text], [])
        self.assertEqual(b.ROUTES["planner_direct"].reachability, "UNREACHABLE_PROVEN")
        self.assertEqual(b.ROUTES["oauth"].budget_class, b.CLASS_AUTH)

    def test_final_audit_flag_changes_only_the_reserve(self):
        history = [self.settled(1, "executor", 1000)]
        with_audit = self.decide(self.measure(), history, final_audit=True)
        without = self.decide(self.measure(), history, final_audit=False)
        self.assertEqual((with_audit.verdict, without.verdict), ("ALLOW", "ALLOW"))
        self.assertEqual(with_audit.estimate, without.estimate)
        self.assertEqual(with_audit.view.protected_reserve_tokens, 48000)
        self.assertEqual(without.view.protected_reserve_tokens, 0)

    def test_preflight_warnings_for_ui_preview(self):
        import ultra_budget_policy as b
        risky = snapshot(verification_reserve_tokens=0, verification_reserve_attempts=0)
        codes = [r.code for r in b.preflight_run(risky, b.RunContext("run", True))]
        self.assertEqual(codes, ["RESERVE_ZERO_WITH_FINAL_AUDIT", "RESERVE_ATTEMPTS_ZERO_WITH_FINAL_AUDIT",
                                 "MCP_DISABLED", "COMPRESSOR_DISABLED"])
        self.assertEqual([r.code for r in b.preflight_run(risky, b.RunContext("run", False))],
                         ["MCP_DISABLED", "COMPRESSOR_DISABLED"])

    def test_malformed_measure_is_denied_not_trusted(self):
        """evaluate_request is public: a hand-built measure must not lower liability or skip the estimate."""
        import ultra_budget_policy as b
        good = self.measure(wire_bytes=4000)
        self.assertEqual(self.decide(good).verdict, b.ALLOW)
        for field, value in (("output_reserve_tokens", -30000), ("output_reserve_tokens", 0),
                             ("output_reserve_tokens", True), ("wire_bytes", -1), ("wire_bytes", True),
                             ("wire_bytes", 4000.0), ("provider_model_id", ""), ("wire_sha256", "xyz")):
            with self.subTest(field=field, value=value):
                decision = self.decide(replace(good, **{field: value}))
                self.assertEqual((decision.verdict, [r.code for r in decision.reasons]), (b.DENY, ["INVALID_MEASURE"]))
                self.assertIsNone(decision.reservation_liability_tokens)

    def test_full_read_contract_for_s4(self):
        import ultra_budget_policy as b
        snap = snapshot()
        self.assertEqual(b.evaluate_full_read(snap, 65536).verdict, b.ALLOW)
        denied = b.evaluate_full_read(snap, 65537)
        self.assertEqual((denied.verdict, denied.reasons[0].code), (b.DENY, "FULL_READ_EXCEEDS_CAP"))
        with self.assertRaises(b.PolicyInputError):
            b.evaluate_full_read(snap, -1)


# --------------------------------------------------------------------------- synthetic RUN replays (mock calibration)

class SyntheticRunTests(unittest.TestCase):
    EXPECTED_BLOCKS = {
        "A": {"R-025": 3, "R-026": 3, "R-027": 3, "R-031": 9},
        "B": {"R-025": 4, "R-026": 4, "R-027": 4, "R-031": 10},
        "C": {"R-026": 8, "R-027": 10, "R-031": 13},
    }

    def test_candidates_stop_the_heavy_runs_and_never_block_normal_ones(self):
        runs = recorded_runs()
        self.assertEqual(len(runs), 41)
        observed = {}
        for label, overrides in CANDIDATES.items():
            snap = snapshot(**overrides)
            blocks = {}
            for key, rows in runs.items():
                result = simulate_run(snap, rows)
                if result["blocked_at"] is not None:
                    blocks[run_label(key)] = result["blocked_at"]
            self.assertEqual(blocks, self.EXPECTED_BLOCKS[label], label)
            observed[label] = blocks
        _OBSERVATIONS["candidate_blocks"] = observed

    def test_without_separate_verification_caps_normal_runs_lose_their_final_audit(self):
        overrides = dict(CANDIDATES["A"], max_verification_request_bytes=262144,
                         max_verification_request_input_tokens_est=48000)
        snap = snapshot(**overrides)
        runs = recorded_runs()
        for key in ("project/20261001_004240_a734f1", "project/20261001_004705_96dc2e"):  # R-029, R-030 SUCCESS
            with self.subTest(run=run_label(key)):
                result = simulate_run(snap, runs[key])
                self.assertEqual(result["blocked_at"], len(runs[key]))  # the last call is the Final Audit
                self.assertEqual(runs[key][-1][2], "verifier_final")

    def test_greetings_and_live_benches_complete_under_every_candidate(self):
        runs = recorded_runs()
        normal = [k for k in runs if run_label(k) in {"R-032", "R-033", "R-034", "R-035"} or "/B1_" in k
                  or "/B2_" in k or "/B3_" in k]
        self.assertGreaterEqual(len(normal), 30)
        for label, overrides in CANDIDATES.items():
            snap = snapshot(**overrides)
            for key in normal:
                with self.subTest(candidate=label, run=key):
                    self.assertIsNone(simulate_run(snap, runs[key])["blocked_at"])

    def test_candidate_reserves_cover_observed_final_audits_only_up_to_their_size(self):
        """Mock-calibration fact for the USER DECISION: no candidate reserve fits the largest observed audits."""
        import ultra_budget_policy as b
        audits = [r for r in ROWS if r[2] == "verifier_final"]
        self.assertEqual(len(audits), 32)
        for label, overrides in CANDIDATES.items():
            snap = snapshot(**overrides)
            with self.subTest(candidate=label):
                self.assertIn("RESERVE_BELOW_ONE_MAX_VERIFICATION",
                              [r.code for r in b.preflight_run(snap, b.RunContext("run", True))])
                reserve = snap.run.verification_reserve_tokens
                liabilities = {run_label(r[0]): b.estimate_input_tokens(snap, r[3], "dredd", r[4]).tokens
                               + ROUTE_MAX_TOKENS["verifier_final"] for r in audits}
                self.assertEqual(sorted(k for k, v in liabilities.items() if v > reserve), ["R-029", "R-030"])
                # work has consumed everything except the protected reserve: only audits that fit it can run
                filler = b.apply_terminal(b.mark_sent(b.reserve_attempt(
                    "w", b.RequestMeasure("executor", "GigaChat-3-Ultra", 4000, "0" * 64, 1),
                    b.TokenEstimate(1, b.EST_CALIBRATED, None, ""), "run")), "completed",
                    {"prompt_tokens": snap.run.max_run_liability_tokens - reserve, "completion_tokens": 0,
                     "precached_prompt_tokens": 0})
                for row in audits:
                    if run_label(row[0]) not in ("R-029", "R-033"):
                        continue
                    measure = b.RequestMeasure("verifier_final", row[3], row[4], "0" * 64,
                                               ROUTE_MAX_TOKENS["verifier_final"])
                    decision = b.evaluate_request(snap, [filler], measure, b.RunContext("run", True))
                    if run_label(row[0]) == "R-033":
                        self.assertEqual(decision.verdict, b.ALLOW)
                    else:
                        self.assertEqual((decision.verdict, decision.consequence, decision.reasons[0].code),
                                         (b.DENY, "NO_SUCCESS_WITHOUT_AUDIT", "RUN_LIABILITY_EXCEEDED"))

    def test_unknown_terminal_keeps_liability_in_replay(self):
        runs = recorded_runs()
        r026 = runs["project/20260930_233733_1f2fee"]
        self.assertEqual([r[5] for r in r026].count("timeout"), 1)
        generous = dict(CANDIDATES["C"], max_run_liability_tokens=5_000_000, max_run_attempts=100,
                        max_request_bytes=1048576, max_request_input_tokens_est=400000)
        result = simulate_run(snapshot(**generous), r026)
        known = sum(r[6] + (r[7] or 0) + r[8] for r in r026 if isinstance(r[6], int))
        self.assertGreater(result["committed"], known)  # the timed-out attempt still carries its reservation


# --------------------------------------------------------------------------- isolation and non-enforcement

class IsolationTests(unittest.TestCase):
    def test_policy_evaluation_does_not_mutate_inputs(self):
        import ultra_budget_policy as b
        rows_before = copy.deepcopy(ROWS)
        raw = policy_dict()
        raw_before = copy.deepcopy(raw)
        snap = b.validate_policy(raw)
        attempts = [b.mark_sent(b.reserve_attempt("a", b.RequestMeasure("executor", "GigaChat-3-Ultra", 9, "0" * 64,
                                                                         5), b.TokenEstimate(9, b.EST_CALIBRATED,
                                                                                             None, ""), "run"))]
        attempts_before = copy.deepcopy(attempts)
        b.evaluate_request(snap, attempts, b.RequestMeasure("executor", "GigaChat-3-Ultra", 9, "0" * 64, 5),
                           b.RunContext("run", True))
        simulate_run(snap, recorded_runs()["project/20261001_182057_e90f93"])
        self.assertEqual((ROWS, raw, attempts), (rows_before, raw_before, attempts_before))
        self.assertEqual(dataset_digest(ROWS), DATASET_SHA256)

    def test_policy_module_is_pure(self):
        source = (ROOT / "ultra_budget_policy.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imported, {"__future__", "hashlib", "json", "math", "dataclasses", "typing"})
        calls = {getattr(n.func, "id", None) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        self.assertFalse(calls & {"open", "print", "exec", "eval", "__import__"})

    def test_no_production_module_imports_the_policy_yet(self):
        for module in s1._production_modules():
            if module.name == "ultra_budget_policy.py":
                continue
            tree = ast.parse(module.read_text(encoding="utf-8"))
            names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
            self.assertNotIn("ultra_budget_policy", names, module.name)

    def test_manifest_matches_the_loaded_collection(self):
        loaded = []

        def flatten(item):
            if isinstance(item, unittest.TestSuite):
                for child in item:
                    flatten(child)
            else:
                loaded.append(s1._short_id(item))

        flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
        expected = list(MANIFEST) + (["ProvenanceTests.test_embedded_dataset_is_reproduced_from_local_raw"]
                                     if _PROVENANCE else [])
        self.assertEqual(sorted(t for t in loaded if _PROVENANCE or not t.startswith("ProvenanceTests.")),
                         sorted(expected))


# --------------------------------------------------------------------------- provenance (optional mode)

ROUTE_OF = {("executor", "STAGE"): "executor", ("executor", "DIRECT"): "executor",
            ("executor", "AUDIT_DIAGNOSTIC"): "audit_diagnostic", ("planner", "INITIAL"): "planner_session",
            ("planner", "READINESS"): "planner_session", ("planner", "REPLAN"): "planner_session",
            ("dredd", "FINAL"): "verifier_final", ("dredd", "PERMISSION"): "verifier_permission",
            ("dredd", "PLANNER_REVIEW"): "planner_review"}


def extract_rows(root: Path, compressor_root: Path) -> list:
    """Re-derive the dataset read-only (same rules as the embedded one: first terminal per attempt)."""
    rows = []
    for f in sorted(set(glob.glob(str(root / "**" / ".ultra" / "audit" / "*" / "*" / "*.jsonl"), recursive=True))):
        path = Path(f)
        if path.name not in ("executor.jsonl", "planner.jsonl", "dredd.jsonl"):
            continue
        store = path.parents[4].relative_to(root).as_posix()
        run_key = ("project" if store == "." else store) + "/" + path.parts[-2]
        starts, terminals = {}, {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if '"provider_attempt_' not in line:
                continue
            record = json.loads(line)
            payload = record["payload"]
            if record["event"] == "provider_attempt_started":
                starts[payload["provider_attempt_id"]] = (record["sequence"], payload)
            elif record["event"] == "provider_attempt_terminal":
                terminals.setdefault(payload["provider_attempt_id"], payload)
        for attempt_id, (sequence, start) in starts.items():
            terminal = terminals.get(attempt_id)
            raw = ((terminal or {}).get("provider_usage") or {}).get("raw") or {}
            rows.append((run_key, sequence, ROUTE_OF[(start["role"], start["mode"].split(":")[0])],
                         start["provider_model_id"], start["request_utf8_bytes"], (terminal or {}).get("outcome"),
                         raw.get("prompt_tokens"), raw.get("precached_prompt_tokens"), raw.get("completion_tokens")))
    for f in sorted(glob.glob(str(compressor_root / "*.jsonl"))):
        starts = {}
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            if d.get("event") == "provider_attempt_started":
                starts[d["provider_attempt_id"]] = d
            elif d.get("event") == "provider_attempt_terminal" and d["provider_attempt_id"] in starts:
                s = starts[d["provider_attempt_id"]]
                raw = (d.get("provider_usage") or {}).get("raw") or {}
                rows.append(("compressor/" + Path(f).stem, 1, "compressor", s["provider_model_id"],
                             s["request_utf8_bytes"], d.get("outcome"), raw.get("prompt_tokens"),
                             raw.get("precached_prompt_tokens"), raw.get("completion_tokens")))
    return sorted(rows, key=lambda r: (r[0], r[1]))


class ProvenanceTests(unittest.TestCase):
    def test_embedded_dataset_is_reproduced_from_local_raw(self):
        self.assertEqual(_PROVENANCE_PROBLEMS, [])
        self.assertIsNotNone(_PROVENANCE_ROWS)
        local = {(r[0], r[1]): tuple(r) for r in _PROVENANCE_ROWS}
        missing = [r[:2] for r in ROWS if local.get((r[0], r[1])) != tuple(r)]
        self.assertEqual(missing, [])
        _OBSERVATIONS["provenance"] = {"embedded": len(ROWS), "local": len(local),
                                       "new_local_rows": len(set(local) - {(r[0], r[1]) for r in ROWS})}


# --------------------------------------------------------------------------- guarded runner

def _file_hashes(names):
    return {name: _sha256((ROOT / name).read_bytes()) for name in names}


def main() -> int:
    global _ISOLATED, _SANDBOX, _PROVENANCE, _PROVENANCE_ROWS
    sys.dont_write_bytecode = True
    args = [a for a in sys.argv[1:] if a != "--provenance"]
    _PROVENANCE = "--provenance" in sys.argv[1:]
    base = Path(tempfile.mkdtemp(prefix="claude-rt002-s2-"))
    _SANDBOX = base
    production_before = _file_hashes(PRODUCTION_FILES)
    if _PROVENANCE:  # read-only, before guards; absence is a FAIL in this mode, never a skip
        try:
            _PROVENANCE_ROWS = extract_rows(ROOT, Path(os.environ.get("LOCALAPPDATA", "")) / "GigaChatUltra"
                                            / "compressor_logs")
        except Exception as exc:  # noqa: BLE001 - reported through the gate
            _PROVENANCE_PROBLEMS.append(f"provenance extraction failed: {type(exc).__name__}: {exc}")
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
                                 "run_store", "ultra_budget_policy") if m in sys.modules)
    if already:
        raise SystemExit("Runtime modules imported before guards: " + ", ".join(already))
    import ultra_budget_policy  # noqa: F401  (only after guards)
    collected_tests = []

    def flatten(item):
        if isinstance(item, unittest.TestSuite):
            for child in item:
                flatten(child)
        else:
            collected_tests.append(item)

    flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not _PROVENANCE:
        collected_tests = [t for t in collected_tests if not s1._short_id(t).startswith("ProvenanceTests.")]
    manifest = list(MANIFEST) + (["ProvenanceTests.test_embedded_dataset_is_reproduced_from_local_raw"]
                                 if _PROVENANCE else [])
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
    problems = list(_PROVENANCE_PROBLEMS)
    production_after = _file_hashes(PRODUCTION_FILES)
    problems += [f"production file changed during run: {n}" for n in PRODUCTION_FILES
                 if production_before[n] != production_after[n]]
    if dataset_digest(ROWS) != DATASET_SHA256:
        problems.append("embedded calibration dataset digest mismatch")
    gate = s1.evaluate_gate(manifest=manifest, collected=collected, selected=selected,
                            unresolved_selectors=unresolved or [], started=s1._RecordingResult.started_ids,
                            counts=counts, evidence_problems=problems, violations=violations)
    report = {
        "task": "CLAUDE-RT002-S2-001", "mode": "provenance" if _PROVENANCE else "core", "sandbox": str(base),
        "python": sys.version.split()[0], "gate": gate, "counts": counts, "manifest_size": len(manifest),
        "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
        "skipped": [(t.id(), reason) for t, reason in result.skipped], "isolation_violations": violations,
        "problems": problems, "selected": selected, "dataset_sha256": DATASET_SHA256,
        "production_hashes": production_after, "elapsed_seconds": round(time.time() - started, 3),
        "observations": _OBSERVATIONS, "log": str(log_path), "log_sha256": _sha256(log_path.read_bytes()),
    }
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"observations", "production_hashes"}},
                     ensure_ascii=False, indent=2))
    if result.failures or result.errors:
        print(log_path.read_text(encoding="utf-8").split("=" * 70, 1)[-1])
    return gate["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
