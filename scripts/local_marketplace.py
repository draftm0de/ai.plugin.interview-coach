#!/usr/bin/env python3
"""Forward local development to the configured shared marketplace checkout."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install-local','update-local'])
    parser.add_argument('--target',choices=['claude','codex'],default='claude')
    parser.add_argument('--marketplace')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        config=ROOT/'.local/marketplace.json'
        configured=args.marketplace or (json.loads(config.read_text()).get('marketplace') if config.exists() else None)
        if not configured:
            raise ValueError('Set MARKETPLACE=/path/to/ai.plugins or marketplace in .local/marketplace.json')
        root=Path(configured).expanduser()
        if not root.is_absolute():root=ROOT/root
        root=root.resolve()
        helper=root/'scripts/local_plugins.py'
        if not helper.is_file() or not (root/'marketplace.json').is_file():
            raise ValueError('Not a configured marketplace checkout: '+str(root))
        local=json.loads((root/'.local/marketplace.json').read_text())
        name=json.loads((ROOT/'plugin.json').read_text())['name']
        selected=Path(local.get('sources',{}).get(name,'')).expanduser()
        if not selected.is_absolute():selected=root/selected
        if selected.resolve()!=ROOT.resolve():
            raise ValueError('Marketplace local source does not point to this plugin checkout: '+name)
        command=[sys.executable,str(helper),args.action,'--target',args.target]
        if args.dry_run:command.append('--dry-run')
        return subprocess.run(command,check=False).returncode
    except (ValueError,OSError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
