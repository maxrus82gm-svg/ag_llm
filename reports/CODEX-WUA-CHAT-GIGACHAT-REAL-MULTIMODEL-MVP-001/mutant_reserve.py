"""Intentional in-memory reserve weakening; durable/physical oracle MUST fail."""
from pathlib import Path
import gigachat_runtime as runtime
source=Path(runtime.__file__).read_text(encoding='utf-8')
old='admission.authorize(wire, self)'
assert source.count(old)==1
exec(compile(source.replace(old,'None'),runtime.__file__,'exec'),runtime.__dict__)
from test_web_alarm_gigachat_multimodel import ProtocolTests
