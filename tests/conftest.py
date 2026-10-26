import json

import pytest


@pytest.fixture
def reports(tmp_path):
    """Stable reports independent of the live forward period or repository results."""
    dest = tmp_path / 'results'
    for track in ('r1', 'r5'):
        directory = dest / track
        directory.mkdir(parents=True)
        summary = {'track': track, 'start_date': '2026-10-27',
                   'updated_utc': '2026-10-26T15:51:48+00:00', 'date': None,
                   'status': 'not_started', 'profit_pct': 0, 'max_drawdown_pct': 0,
                   'trades': 0, 'open_positions': [], 'closed_trades': []}
        (directory / 'summary.json').write_text(json.dumps(summary))
        (directory / 'equity.csv').write_text('date,equity,buy_hold_equity\n'
                                             '2026-10-27T00:00:00+00:00,1000,1000\n')
    return dest
