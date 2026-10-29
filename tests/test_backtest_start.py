from scripts.run_forward import backtest_start


def test_backtest_starts_one_day_before_forward_start():
    # Signal of 2026-10-26 must be able to fill at the 2026-10-27 open.
    assert backtest_start('2026-10-27') == '20261026'
    assert backtest_start('2026-03-01') == '20260228'
