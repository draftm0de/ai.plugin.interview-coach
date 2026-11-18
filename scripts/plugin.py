#!/usr/bin/env python3
"""Generate or check versionless plugin manifests; marketplace catalogs belong to ai.plugins."""
import argparse
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def expected(root=ROOT):
    root=root.resolve()
    manifest=json.loads((root/'plugin.json').read_text())
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', manifest['name']):
        raise ValueError('Plugin name must use lowercase kebab-case')
    if 'version' in manifest:
        raise ValueError('Repository imports must not pin a manifest version')
    host=manifest['extensions']['com.openai']
    interface=host['interface']
    for relative in (host['onboardingSkill'],interface['logo'],interface['composerIcon']):
        if not relative.startswith('./') or '..' in Path(relative).parts:
            raise ValueError('Plugin paths must stay inside the repository')
        path=root/relative
        if not path.is_file() or any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('Missing or symlinked plugin source: '+relative)
    claude={key:manifest[key] for key in ('name','description','author','homepage','repository','license','keywords') if key in manifest}
    claude['displayName']=interface['displayName']
    codex={key:manifest[key] for key in ('name','description','author','homepage','repository','license','keywords') if key in manifest}
    codex.update(skills='./skills/',interface=interface)
    return {'.claude-plugin/plugin.json':claude,'.codex-plugin/plugin.json':codex}

def sync(check=False,root=ROOT):
    root=root.resolve()
    files=expected(root)
    for relative in ('.claude-plugin/marketplace.json','.agents/plugins/marketplace.json'):
        if (root/relative).exists():
            raise ValueError('This plugin must not own a marketplace: '+relative)
    drift=[]
    for relative,data in files.items():
        path=root/relative
        if any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('Host metadata must not use symlinks')
        if not path.exists() or json.loads(path.read_text()) != data:
            drift.append(relative)
    if check and drift:
        raise ValueError('Host manifests are stale; run make sync-plugin: '+', '.join(drift))
    if not check:
        for relative in drift:
            path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(files[relative],ensure_ascii=False,indent=2)+'\n')
    return {'valid':True,'updated':drift}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check','sync'])
    args=parser.parse_args()
    print(json.dumps(sync(args.action=='check'),indent=2))
