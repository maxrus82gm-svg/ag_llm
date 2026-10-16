"""Replace raw U+2028/U+2029/U+0085 characters inside string literals with their ASCII escape
text (backslash + uXXXX). Written without any backslash-u sequence on purpose (the editor
tooling decodes them). Verifies the module still defines the same translation table."""
import ast
import sys
from pathlib import Path

BS = chr(92)
for name in sys.argv[1:]:
    path = Path(name)
    data = path.read_bytes()
    assert b"\r\n" not in data
    text = data.decode("utf-8")
    before_tree = ast.dump(ast.parse(text))
    fixed = text
    for code in (0x85, 0x2028, 0x2029):
        fixed = fixed.replace(chr(code), BS + "u" + format(code, "04x"))
    assert ast.dump(ast.parse(fixed)) == before_tree, name + ": AST changed"
    assert not any(chr(c) in fixed for c in (0x85, 0x2028, 0x2029))
    assert all(ord(ch) < 128 or ch in fixed for ch in fixed)
    path.write_bytes(fixed.encode("utf-8"))
    print(name, "fixed", text.count(chr(0x2028)), text.count(chr(0x2029)), text.count(chr(0x85)), "-> AST identical")
