import json

import pandas as pd

from scripts.health import data_health, record_run, run_counts


def frame(dates):
    return pd.DataFrame({'date': pd.to_datetime(dates, utc=True)})


def test_fresh_missing_stale_duplicate_and_listing():
    candles = {'good': frame(['2026-10-27', '2026-10-28', '2026-10-29']),
               'gap': frame(['2026-10-27', '2026-10-29']),
               'stale': frame(['2026-10-27', '2026-10-28']),
               'new': frame(['2026-10-29']),
               'dup': frame(['2026-10-27', '2026-10-28', '2026-10-29', '2026-10-29'])}
    result = data_health(candles, list(candles) + ['absent'],
                         pd.Timestamp('2026-10-30', tz='UTC'),
                         listings={'new': '2026-10-29T00:00:00+00:00'})
    assert result['pairs_ok'] == ['good', 'new']
    assert result['pairs']['new']['listing_gap_days'] == 2
    assert result['pairs']['gap']['missing_days'] == ['2026-10-28']
    assert result['pairs']['dup']['duplicate_days']
    assert not result['data_freshness']


def test_unproven_leading_gap_is_failure():
    result = data_health({'x': frame(['2026-10-29'])}, ['x'],
                         pd.Timestamp('2026-10-30', tz='UTC'))
    assert result['pairs_missing'] == ['x']


def test_run_ledger_and_schedule(tmp_path):
    path = tmp_path / 'health.json'
    result = {'data_freshness': True, 'pairs_ok': ['x'], 'pairs_missing': []}
    for success in [False, True, True]:
        record_run(path, '2026-10-28T00:25:00+00:00', success, result, result, 3.12345)
    ledger = json.loads(path.read_text())
    assert len(ledger['runs']) == 3
    assert ledger['runs'][0]['duration_seconds'] == 3.123
    assert run_counts(ledger, '2026-10-27T23:59:00+00:00')['expected'] == 0
    assert run_counts(ledger, '2026-10-28T00:19:00+00:00')['expected'] == 0
    assert run_counts(ledger, '2026-10-28T00:20:00+00:00') == {
        'expected': 1, 'actual': 1, 'missing': 0}
    assert run_counts(ledger, '2026-10-30T12:00:00+00:00') == {
        'expected': 3, 'actual': 1, 'missing': 2}


def test_freeze_failure_is_recorded_before_any_run(tmp_path, monkeypatch):
    import pytest

    from scripts import run_forward
    from scripts.freeze_check import MESSAGE

    monkeypatch.setattr(run_forward, 'ROOT', tmp_path)
    def fail():
        raise ValueError(MESSAGE)
    monkeypatch.setattr(run_forward, 'freeze_check', fail)
    monkeypatch.setattr(run_forward, 'execute', lambda: pytest.fail('Engine must not run'))
    with pytest.raises(ValueError, match=MESSAGE):
        run_forward.main()
    ledger = json.loads((tmp_path / 'results/health.json').read_text())
    assert ledger['runs'][-1]['reason'] == 'freeze'
    assert not ledger['runs'][-1]['success']


def test_invalid_candles_are_not_healthy():
    f = frame(['2026-10-27'])
    for name in ['open', 'high', 'low', 'close', 'volume']:
        f[name] = 10.
    f['close'] = -1
    result = data_health({'x': f}, ['x'], pd.Timestamp('2026-10-28', tz='UTC'))
    assert result['pairs_missing'] == ['x']
    assert result['pairs']['x']['invalid_ohlcv']


def test_engine_failure_retains_post_health_and_original_error(tmp_path, monkeypatch):
    import pytest

    from scripts import run_forward

    monkeypatch.setattr(run_forward, 'ROOT', tmp_path)
    monkeypatch.setattr(run_forward, 'freeze_check', lambda: None)
    snapshots = iter([{'pairs_missing': ['x']}, {'pairs_missing': ['x'],
                       'data_freshness': False}])
    monkeypatch.setattr(run_forward, 'snapshot', lambda: next(snapshots))
    def fail():
        raise ValueError('engine failed')
    monkeypatch.setattr(run_forward, 'execute', fail)
    with pytest.raises(ValueError, match='engine failed'):
        run_forward.main()
    r = json.loads((tmp_path / 'results/health.json').read_text())['runs'][-1]
    assert r['pairs_missing'] == ['x']
    assert r['reason'] == 'run_failed'
    assert not r['success']
