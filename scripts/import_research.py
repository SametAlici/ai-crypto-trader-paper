"""Copy only scanned export files from the private read-only source."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.secret_scan import inspect_file

SOURCE = ROOT.parent / 'Trade_Bot/exports'


def import_research(source=SOURCE, target=ROOT / 'research'):
    files = [source / 'research_snapshot.json', *sorted((source / 'research_equity').glob('*.csv'))]
    if len(files) == 1:
        raise ValueError('Research equity exports missing')
    if any(inspect_file(p) for p in files):
        raise ValueError('Research source secret scan failed; nothing copied')
    json.loads(files[0].read_text())
    for p in files:
        dest = target / p.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    print(f'Research source scan passed; copied {len(files)} files.')


if __name__ == '__main__':
    import_research()
