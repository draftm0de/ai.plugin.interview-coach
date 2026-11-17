#!/usr/bin/env python3
"""Build deterministic portable skill ZIP. No private workspace files included."""
import argparse
from pathlib import Path
import zipfile

def package(source, output):
    source = Path(source)
    output = Path(output)
    if not (source / "SKILL.md").is_file():
        raise ValueError("SKILL.md missing from source")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not (source / "scripts" / "interview_workspace.py").is_file():
        raise ValueError("Required bundled workspace CLI missing")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob("*")):
            if not file.is_file():
                continue
            if file.is_symlink():
                raise ValueError("Symlinks are not permitted in portable skill packages")
            if any(p.startswith(".") or p == "__pycache__" for p in file.relative_to(source).parts):
                continue
            archive.write(file, arcname=str(Path(source.name) / file.relative_to(source)))
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(package(args.source, args.output))
