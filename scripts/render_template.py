"""Render one reviewed source template. Never imports or runs the result."""
import argparse
import ast
import json
from pathlib import Path
import re

TOKEN = re.compile(r"@@([A-Z0-9_]+)@@")

def render(text, config):
    required = set(TOKEN.findall(text))
    missing = sorted(key for key in required if not config.get(key))
    if missing:
        raise ValueError("Missing configuration " + ", ".join(missing))
    for key in required:
        value = config[key]
        if not isinstance(value, str) or any(c in value for c in "\\\"'\r\n\x00"):
            raise ValueError("Use forward-slash paths and plain values without quotes for " + key)
        if value.endswith("/"):
            raise ValueError("Use roots without trailing slash for " + key)
    return TOKEN.sub(lambda m: config[m[1]], text)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_root = Path(__file__).resolve().parent.parent
    template = args.template.resolve()
    output = args.output.resolve()
    if not template.is_relative_to(source_root / "scripts") or not template.name.endswith(".in"):
        parser.error("Choose a repository script template ending in .in")
    if output.is_relative_to(source_root):
        parser.error("Render outside the repository, never over a source template")
    text = render(template.read_text(encoding="utf-8"), json.loads(args.config.read_text(encoding="utf-8")))
    if template.name.endswith(".py.in"):
        ast.parse(text)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    print("Rendered source only. Review dependencies and side effects before running.")

if __name__ == "__main__":
    main()
