"""Exercise the actual dependency-free dashboard renderers in Node."""
import subprocess
from pathlib import Path


def test_dashboard_interactions():
    subprocess.run(['node', 'tests/site_dashboard.cjs'],
                   cwd=Path(__file__).resolve().parents[1], check=True)
