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


def test_all_new_metrics_with_fees_and_coin_attribution():
    trades = [trade('exit_signal') for _ in range(4)]
    # Synthetic net results; fixed amount/prices make fee totals independently verifiable.
    for t, profit in zip(trades, [50., 30., 20., -10.], strict=True):
        t['profit_abs'] = profit
    summary, curve = build_summary('r1', {'trades': trades, 'final_balance': 1090},
                                   candles(), '2026-10-27', 'now')
    assert summary['net_profit_usdt'] == 90
    assert summary['total_fees_usdt'] == pytest.approx(4 * .33)
    assert summary['gross_profit_usdt'] == pytest.approx(91.32)
    assert summary['top3_profit_share_pct'] == pytest.approx(100 / 90 * 100)
    assert summary['best_trade_profit_share_pct'] == pytest.approx(50 / 90 * 100)
    assert summary['net_without_best_trade_usdt'] == 40
    assert summary['net_without_best_trade_pct'] == 4
    assert summary['per_coin_contribution'] == {'BTC/USDT': 90}
    assert summary['win_rate_pct'] == 75
    assert summary['avg_win_usdt'] == pytest.approx(100 / 3)
    assert summary['avg_loss_usdt'] == -10
    assert summary['avg_win_loss_ratio'] == pytest.approx(10 / 3)
    assert summary['daily_returns'][-1]['fees_cumulative'] == pytest.approx(1.32)
    assert summary['daily_returns'][-1]['return_pct'] == pytest.approx(
        (curve.equity.iloc[-1] / curve.equity.iloc[-2] - 1) * 100)
    compound = 1
    for day in summary['daily_returns']:
        compound *= 1 + day['return_pct'] / 100
    assert compound == pytest.approx(1.09)


def test_undefined_shares_and_all_losses():
    t = trade('exit_signal')
    t['profit_abs'] = -10
    s, _ = build_summary('r1', {'trades': [t], 'final_balance': 990},
                          candles(), '2026-10-27', 'now')
    assert s['top3_profit_share_pct'] is None
    assert s['best_trade_profit_share_pct'] is None
    assert s['avg_win_usdt'] is None
    assert s['avg_win_loss_ratio'] is None
    assert s['net_without_best_trade_usdt'] == 0


def test_own_universe_benchmark_and_listing_cash():
    frames = candles()
    frames['ETH/USDT'] = frames['BTC/USDT'].copy()
    frames['ETH/USDT']['close'] = [80., 80., 80.]
    s1, _ = build_summary('r1', {}, {'BTC/USDT': frames['BTC/USDT']}, '2026-10-27', 'now')
    s5, curve = build_summary('r5', {}, frames, '2026-10-27', 'now')
    assert s1['buy_hold_pairs'] == ['BTC/USDT']
    assert s5['buy_hold_profit_pct'] == pytest.approx((1.05*.9985/1.0015-1)*100)
    assert sum(s5['daily_returns'][-1]['buy_hold_per_coin_cumulative'].values()) == pytest.approx(
        curve.buy_hold_equity.iloc[-1]-1000)
    frames['ETH/USDT'] = frames['ETH/USDT'].iloc[1:]
    _, curve = build_summary('r5', {}, frames, '2026-10-27', 'now')
    assert curve.buy_hold_equity.iloc[1] == pytest.approx(500+550*.9985/1.0015)
