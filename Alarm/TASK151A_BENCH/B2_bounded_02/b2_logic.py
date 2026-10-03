STATUS_PREFIX = "READY"

def status_label(name: str) -> str:
    return f"{STATUS_PREFIX}: {name.strip().upper()}"
