"""Small dependency-free public-repository secret gate; never print matched values."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"(?i)[\"']?(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|key|secret|token|password|jwt_secret_key|chat_id|username)[\"']?\s*[:=]\s*[\"'][^\"'\n]+[\"']"),
]
SKIP = {'.git', '.venv', '.uv-cache', '__pycache__', '.pytest_cache', '.ruff_cache'}


def inspect_file(path: Path) -> list[str]:
    if path.name == '.env' or path.name.startswith('.env.'):
        return [f'{path}: forbidden environment file']
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return []
    return [f'{path}:{i}: potential credential' for i, line in enumerate(content.splitlines(), 1)
            if any(pattern.search(line) for pattern in PATTERNS)]


def scan(root: Path) -> list[str]:
    # Include tracked files even if an ignore rule would hide them.
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'],
                             capture_output=True, check=True).stdout.decode().split('\0')
    paths = {root / p for p in tracked if p}
    def walk(directory):
        for p in directory.iterdir():
            if p.is_symlink():
                continue
            if p.is_dir():
                if p.name not in SKIP:
                    walk(p)
            else:
                paths.add(p)
    walk(root)
    return [issue for p in sorted(paths) if p.is_file() for issue in inspect_file(p)]


if __name__ == '__main__':
    issues = scan(ROOT)
    print('\n'.join(issues) if issues else 'Secret scan passed.')
    raise SystemExit(bool(issues))
