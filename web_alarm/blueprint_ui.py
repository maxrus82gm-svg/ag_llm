"""Bundle the dependency-free blueprint editor into the existing local page."""
from pathlib import Path


def install_blueprint_ui(page: str) -> str:
    assets = Path(__file__).with_name("blueprint_assets")
    html = (assets / "editor.html").read_text(encoding="utf-8")
    css = (assets / "editor.css").read_text(encoding="utf-8")
    script = (assets / "editor.js").read_text(encoding="utf-8")
    return (page.replace("<!-- BLUEPRINT_CONTENT -->", html)
            .replace("</head>", "<style>\n" + css + "\n</style>\n</head>")
            .replace("</body>", "<script>\n" + script + "\n</script>\n</body>"))
