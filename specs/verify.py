"""Copy as specs/verify.py; validate links and optionally run linked test files."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true')
args = parser.parse_args()
mapping = json.loads((root/'specs/traceability.json').read_text(encoding='utf-8'))
ids, tests = set(), set()
for item in mapping['requirements']:
    assert item['id'] not in ids and item['statement']
    ids.add(item['id'])
    for kind in ['code','tests']:
        assert item[kind]
        for rel in item[kind]:
            file = (root/rel).resolve()
            assert file.is_relative_to(root) and file.is_file(), (item['id'], rel)
    tests.update(item['tests'])
print(f'SDD links verified: {len(ids)} requirements')
if args.test:
    raise SystemExit(subprocess.call([sys.executable,'-m','pytest','-q',*sorted(tests)],cwd=root))
