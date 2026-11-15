"""Intentional in-memory model-version weakening; the existing oracle MUST fail."""
from pathlib import Path
import gigachat_runtime as runtime
source=Path(runtime.__file__).read_text(encoding='utf-8')
old="decoded.get('model') not in c.response_models"
assert source.count(old)==1
exec(compile(source.replace(old,'False'),runtime.__file__,'exec'),runtime.__dict__)
from test_web_alarm_gigachat_multimodel import ProtocolTests
