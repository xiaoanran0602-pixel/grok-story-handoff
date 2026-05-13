#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_EXTS = {'.py', '.md', '.ps1', '.yml', '.yaml', '.txt'}
MARKER_RE = re.compile(r'(?m)^(<{7}|={7}|>{7})(?: .*)?$')

bad = []
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in TARGET_EXTS:
        continue
    text = p.read_text(encoding='utf-8', errors='ignore')
    for m in MARKER_RE.finditer(text):
        line = text.count('\n', 0, m.start()) + 1
        bad.append((p.relative_to(ROOT), line, m.group(0)))

if bad:
    for path, line, marker in bad:
        print(f"[FAIL] {path}:{line}: {marker}")
    sys.exit(1)

print('[OK] no merge conflict markers found')
