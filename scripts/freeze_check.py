"""Fail closed if frozen strategy bytes or canonical config content changes."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('user_data/strategies/R1_TSMomentum.py', 'user_data/strategies/R5_TSMomentum.py',
         'user_data/config_r1.json', 'user_data/config_r5.json',
         'user_data/config_r6.json', 'user_data/config_r7.json', 'user_data/config_r8.json',
         'universes/PROTOCOL.md', 'universes/r6.json', 'universes/r7.json', 'universes/r8.json',
         'scripts/tracks.py')
TRANSITION_FILES = frozenset(('universes/r7.json', 'universes/r8.json',
    'user_data/config_r7.json', 'user_data/config_r8.json'))
MESSAGE = 'Strateji dosyaları değişmiş — test donduruldu'


def hashes(root=ROOT):
    result = {}
    for name in FILES:
        raw = (root / name).read_bytes()
        if name.endswith('.json'):
            # Freeze ALL config values, including safety and network settings. Whitespace is immaterial.
            raw = json.dumps(json.loads(raw), sort_keys=True, separators=(',', ':')).encode()
        result[name] = hashlib.sha256(raw).hexdigest()
    return result


def committed(root, ref, name):
    return json.loads(subprocess.run(
        ['git', '-C', str(root), 'show', f'{ref}:{name}'],
        capture_output=True, check=True).stdout)


def check(root=ROOT):
    try:
        expected = json.loads((root / 'frozen.json').read_text())['sha256']
        current = hashes(root)
        if expected != current:
            raise ValueError(MESSAGE)
        # Nightly pins HEAD before building. A receipt exists only in this run's
        # temporary directory, and binds the exact bytes published by the builder.
        ref = os.environ.get('FREEZE_BASE_REF')
        try:
            baseline = committed(root, ref or 'HEAD', 'frozen.json')['sha256']
        except subprocess.CalledProcessError:
            if ref:
                raise
            baseline = current  # Initial checkout has no committed manifest yet.
        if baseline != current:
            receipt = json.loads(Path(os.environ['FREEZE_TRANSITION']).read_text())
            changed = {n for n in baseline.keys() | current.keys()
                       if baseline.get(n) != current.get(n)}
            previous = committed(root, ref or 'HEAD', 'universes/r7.json')
            r7 = json.loads((root / 'universes/r7.json').read_text())
            r8 = json.loads((root / 'universes/r8.json').read_text())
            if (changed != TRANSITION_FILES or previous.get('status') != 'pending'
                    or r7.get('status') != 'ready' or r8.get('status') != 'ready'
                    or receipt != {'before': baseline, 'after': current}):
                raise ValueError(MESSAGE)
    except (OSError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        raise ValueError(MESSAGE) from error


if __name__ == '__main__':
    try:
        check()
    except ValueError:
        print(MESSAGE)
        raise SystemExit(1) from None
    print('Frozen strategies and configs verified.')
