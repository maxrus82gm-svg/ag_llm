"""Stop-only native-test gate. This file contains NO native process executor.

Not a completed transport harness: case contracts are in native_test_plan.json.
No --force, environment override or user-supplied JSON can activate execution.
The next authorized stage must implement/review the actual containment runner.
Exit 3 means BLOCKED, not a failed tunnel-client test.
"""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    plan = json.loads((root / 'native_test_plan.json').read_text(encoding='utf-8'))
    result = {
        'gate': 'BLOCKED', 'exit_code': 3,
        'reason_codes': ['NO_ENFORCED_NATIVE_EGRESS_BOUNDARY',
                         'EXACT_SOURCE_CORRESPONDENCE_UNPROVEN',
                         'NATIVE_FIXTURE_DRIVER_NOT_IMPLEMENTED'],
        'case_contracts': len(plan['cases']),
        'native_collected': 0, 'native_executed': 0,
        'native_pass': 0, 'native_fail': 0, 'native_error': 0, 'native_skip': 0,
        'case_contracts_blocked': len(plan['cases']),
        'tunnel_client_processes_started': 0,
        'sockets_opened': 0, 'api_keys_read': 0,
        'policy': 'No native executor exists in this stop-only gate.'
    }
    (root / 'native_gate_result.json').write_text(
        json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
