# TASK151A benchmark inventory

| Profile | Run | Status / Audit | Attempts | Tools | Tokens | Accounting |
|---|---|---|---:|---:|---:|---|
| B1_clean | 20261001_004029_1585f3 | SUCCESS / PASS | 8/8 | 3 | 33142 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_clean_02 | 20261001_144732_50dce3 | SUCCESS / PASS | 8/8 | 3 | 36060 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_clean_03 | 20261001_144801_87ef49 | SUCCESS / PASS | 8/8 | 3 | 36172 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_clean_04 | 20261001_144828_6fc843 | SUCCESS / PASS | 8/8 | 3 | 36875 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_clean_05 | 20261001_144855_02ad28 | SUCCESS / PASS | 8/8 | 3 | 31229 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_dirty | 20261001_004215_145316 | FAILED / ERROR | 9/9 | 3 | UNKNOWN | id=OK, ctx=OK, usage=False, unknown=1 |
| B1_dirty_02 | 20261001_005308_03a909 | SUCCESS / PASS | 10/10 | 3 | 39551 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_dirty_03 | 20261001_145000_42f306 | SUCCESS / PASS | 10/10 | 3 | 41175 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_dirty_04 | 20261001_145037_15ecb0 | SUCCESS / PASS | 9/9 | 3 | 30647 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_dirty_05 | 20261001_145115_092594 | SUCCESS / PASS | 9/9 | 3 | 25158 | id=OK, ctx=OK, usage=True, unknown=0 |
| B1_dirty_06 | 20261001_145147_e92770 | SUCCESS / PASS | 8/8 | 3 | 26416 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_01 | 20261001_143717_a1fda6 | BLOCKED / PENDING | 4/4 | 0 | 19473 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_02 | 20261001_143928_3319b9 | SUCCESS / PASS | 13/13 | 5 | 60044 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_03 | 20261001_144202_601e70 | SUCCESS / PASS | 10/10 | 5 | 46284 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_04 | 20261001_144238_154447 | SUCCESS / PASS | 10/10 | 5 | 47417 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_05 | 20261001_144316_dcdf6d | SUCCESS / PASS | 13/13 | 5 | 45068 | id=OK, ctx=OK, usage=True, unknown=0 |
| B2_bounded_06 | 20261001_144417_c10d33 | SUCCESS / PASS | 13/13 | 5 | 43694 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_analytical_02 | 20261001_145638_e02a80 | SUCCESS / PASS | 6/6 | 2 | 32198 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_analytical_03 | 20261001_145705_f21296 | SUCCESS / PASS | 8/8 | 2 | 38668 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_analytical_04 | 20261001_145743_fc61a7 | SUCCESS / PASS | 6/6 | 2 | 33019 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_analytical_05 | 20261001_145809_d2a784 | SUCCESS / PASS | 7/7 | 2 | 31596 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_analytical_repair_01 | 20261001_121011_24b22d | SUCCESS / PASS | 8/8 | 2 | 34595 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_semantic_01 | 20261001_005545_dc8d2e | BLOCKED / PENDING | 1/1 | 0 | 600 | id=OK, ctx=OK, usage=True, unknown=0 |
| B3_semantic_02 | 20261001_005720_8e5145 | SUCCESS / PASS | 5/5 | 0 | 15071 | id=OK, ctx=OK, usage=True, unknown=0 |

## Max context chars by role
- B1_clean / 20261001_004029_1585f3: {'planner': 16106, 'executor': 23745, 'dredd': 13220}
- B1_clean_02 / 20261001_144732_50dce3: {'planner': 15562, 'executor': 23781, 'dredd': 19014}
- B1_clean_03 / 20261001_144801_87ef49: {'planner': 15409, 'executor': 23726, 'dredd': 20008}
- B1_clean_04 / 20261001_144828_6fc843: {'planner': 15566, 'executor': 23781, 'dredd': 21049}
- B1_clean_05 / 20261001_144855_02ad28: {'planner': 15587, 'executor': 23781, 'dredd': 22141}
- B1_dirty / 20261001_004215_145316: {'planner': 15586, 'executor': 23781, 'dredd': 14049}
- B1_dirty_02 / 20261001_005308_03a909: {'planner': 17238, 'executor': 23726, 'dredd': 15496}
- B1_dirty_03 / 20261001_145000_42f306: {'planner': 17252, 'executor': 23726, 'dredd': 23017}
- B1_dirty_04 / 20261001_145037_15ecb0: {'planner': 17704, 'executor': 23726, 'dredd': 24049}
- B1_dirty_05 / 20261001_145115_092594: {'planner': 17238, 'executor': 23726, 'dredd': 25079}
- B1_dirty_06 / 20261001_145147_e92770: {'planner': 15409, 'executor': 23726, 'dredd': 26278}
- B2_bounded_01 / 20261001_143717_a1fda6: {'planner': 20851, 'dredd': 23186}
- B2_bounded_02 / 20261001_143928_3319b9: {'planner': 24140, 'executor': 27192, 'dredd': 21460}
- B2_bounded_03 / 20261001_144202_601e70: {'planner': 16965, 'executor': 27128, 'dredd': 16286}
- B2_bounded_04 / 20261001_144238_154447: {'planner': 17743, 'executor': 27212, 'dredd': 17594}
- B2_bounded_05 / 20261001_144316_dcdf6d: {'planner': 23866, 'executor': 27192, 'dredd': 21442}
- B2_bounded_06 / 20261001_144417_c10d33: {'planner': 24521, 'executor': 27212, 'dredd': 22534}
- B3_analytical_02 / 20261001_145638_e02a80: {'planner': 16504, 'executor': 29816, 'dredd': 29670}
- B3_analytical_03 / 20261001_145705_f21296: {'planner': 20456, 'executor': 29833, 'dredd': 29233}
- B3_analytical_04 / 20261001_145743_fc61a7: {'planner': 16621, 'executor': 29985, 'dredd': 31568}
- B3_analytical_05 / 20261001_145809_d2a784: {'planner': 17444, 'executor': 29759, 'dredd': 32278}
- B3_analytical_repair_01 / 20261001_121011_24b22d: {'planner': 20723, 'executor': 29854, 'dredd': 19668}
- B3_semantic_01 / 20261001_005545_dc8d2e: {'planner': 12492}
- B3_semantic_02 / 20261001_005720_8e5145: {'planner': 14914, 'executor': 21227, 'dredd': 7213}
