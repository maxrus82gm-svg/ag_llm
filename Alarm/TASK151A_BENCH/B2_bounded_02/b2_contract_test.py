from b2_logic import status_label

def assert_contract() -> None:
    actual = status_label("bench")
    expected = "READY: BENCH"
    if actual != expected:
        raise AssertionError(f"contract mismatch: {actual!r} != {expected!r}")
