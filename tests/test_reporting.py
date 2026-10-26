import pandas as pd
import pytest

from scripts.reporting import build_summary, render_readme


def candles():
    return {'BTC/USDT': pd.DataFrame({
        'date': pd.date_range('2026-10-27', periods=3, tz='UTC'),
        'open': [100., 110., 120.], 'close': [110., 120., 130.]})}


def trade(reason, opened='2026-10-27 00:00:00+00:00', closed='2026-10-29 00:00:00+00:00'):
    return {'pair': 'BTC/USDT', 'open_date': opened, 'close_date': closed,
            'open_rate': 100., 'close_rate': 120., 'amount': 1.,
            'fee_open': .0015, 'fee_close': .0015, 'profit_abs': 19.67,
            'exit_reason': reason}


def test_closed_and_terminal_valuation_reconcile():
    stats = {'trades': [trade('exit_signal'), trade('force_exit')], 'final_balance': 1039.34}
    summary, curve = build_summary('r1', stats, candles(), '2026-10-27', 'now')
    assert summary['trades'] == 1
    assert len(summary['open_positions']) == 1
    assert summary['open_positions'][0]['status'] == 'açık (değerleme)'
    assert summary['open_positions'][0]['exit_date'] is None
    assert summary['closed_trades'][0]['exit_price'] == 120
    assert curve.equity.iloc[-1] == pytest.approx(1039.34)
    assert summary['buy_hold_profit_pct'] == pytest.approx((1.3*.9985/1.0015-1)*100)
    assert summary['profit_pct'] == pytest.approx(3.934)


def test_no_trades_and_no_forward_data():
    empty = {p: f.iloc[:0] for p, f in candles().items()}
    summary, curve = build_summary('r5', {}, empty, '2026-10-27', 'now')
    assert summary['balance'] == 1000
    assert summary['status'] == 'not_started'
    assert summary['buy_hold_profit_pct'] is None
    assert len(curve) == 1
    assert 'Başlamadı' in render_readme([summary], 'now')
    assert 'sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir' in render_readme([], 'now')


def test_active_but_no_trades():
    summary, curve = build_summary('r1', {}, candles(), '2026-10-27', 'now')
    assert summary['status'] == 'active'
    assert summary['max_drawdown_pct'] == 0
    assert (curve.equity == 1000).all()


def test_daily_mark_to_market_drawdown_and_entry_timing():
    f = candles()
    f['BTC/USDT']['close'] = [10., 50., 130.]
    t = trade('force_exit', opened='2026-10-28 00:00:00+00:00')
    summary, curve = build_summary('r1', {'trades': [t], 'final_balance': 1019.67},
                                   f, '2026-10-27', 'now')
    assert curve.equity.iloc[1] == 1000  # no position yet
    assert curve.equity.iloc[2] == pytest.approx(949.775)
    assert summary['max_drawdown_pct'] == pytest.approx(5.0225)


def test_engine_mismatch_fails():
    with pytest.raises(ValueError, match='mismatch'):
        build_summary('r1', {'final_balance': 999}, candles(), '2026-10-27', 'now')
