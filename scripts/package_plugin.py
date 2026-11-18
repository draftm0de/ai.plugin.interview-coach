#!/usr/bin/env python3
"""Package one canonical interview skill as a Claude or ChatGPT skills-only plugin."""
import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "zyris-interview-coach"

def package(platform, output):
    manifest = ROOT / ("plugin.json" if platform == "chatgpt" else ".claude-plugin/plugin.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["name"] == "zyris-interview-coach"
    assert (SKILL / "SKILL.md").is_file()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest, "plugin.json" if platform == "chatgpt" else ".claude-plugin/plugin.json")
        for file in sorted(SKILL.rglob("*")):
            if not file.is_file():
                continue
            if file.is_symlink():
                raise ValueError("Symlinks cannot be packaged")
            rel = file.relative_to(SKILL)
            if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
                continue
            archive.write(file, str(Path("skills") / SKILL.name / rel))
        assets = ROOT / "assets"
        if assets.is_dir():
            for file in sorted(assets.iterdir()):
                if file.is_file():
                    archive.write(file, "assets/" + file.name)
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=("claude", "chatgpt"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(package(args.platform, args.output))
