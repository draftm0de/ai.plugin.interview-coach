"""Build the installable plugin payload exactly like a local install does (scripts/plugin.py), for contract and native tests.

The payload carries both host manifests: `.claude-plugin/plugin.json` and the generated `.codex-plugin/plugin.json`.
The repository itself only versions `.claude-plugin/plugin.json`."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tool():
    spec = importlib.util.spec_from_file_location('coach_payload_tool', ROOT / 'scripts/plugin.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def build_payload(target):
    """Write the Claude+Codex payload below `target` and return it."""
    tool = _tool()
    _version, portable, claude = tool.payload()
    files = dict(claude)
    files['.codex-plugin/plugin.json'] = tool.codex_payload(portable)['.codex-plugin/plugin.json']
    target = Path(target)
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return target
