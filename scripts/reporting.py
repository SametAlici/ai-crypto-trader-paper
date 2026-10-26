"""Report engine trades separately from terminal forced valuations."""

FEE = 0.0015
START_DATE = '2026-10-27'
INITIAL = 1000.0


def build_summary(track, stats, candles, start, updated, fee=FEE):
    import pandas as pd
    start = pd.Timestamp(start)
    if start.tzinfo is None:
        start = start.tz_localize('UTC')
    frames = {p: df.loc[df.date >= start].set_index('date') for p, df in candles.items()}
    dates = pd.date_range(start, max((f.index.max() for f in frames.values() if len(f)),
                                    default=start - pd.Timedelta(days=1)), freq='D')
    trades = stats.get('trades', [])
    closed = [t for t in trades if t['exit_reason'] != 'force_exit']
    opened = [t for t in trades if t['exit_reason'] == 'force_exit']
    rows = [{'date': start.isoformat(), 'equity': INITIAL, 'buy_hold_equity': INITIAL}]
    daily = []
    for day in dates:
        equity = INITIAL
        coin_pnl = {p: 0.0 for p in frames}
        fees = 0.0
        trade_pnl = {}
        for trade_id, t in enumerate(trades):
            if pd.Timestamp(t['open_date']) > day:
                continue
            fees += t['amount'] * t['open_rate'] * t.get('fee_open', fee)
            if pd.Timestamp(t['close_date']) <= day:
                fees += t['amount'] * t['close_rate'] * t.get('fee_close', fee)
            if t['exit_reason'] != 'force_exit' and pd.Timestamp(t['close_date']) <= day:
                pnl = t['profit_abs']
            else:
                mark = float(frames[t['pair']].loc[day, 'close'])
                # Freqtrade 2026.9 forces terminal exits at the last candle's OPEN.
                if day == dates[-1] and t['exit_reason'] == 'force_exit':
                    pnl = t['profit_abs']
                else:
                    pnl = (t['amount'] * mark * (1 - t.get('fee_close', fee))
                               - t['amount'] * t['open_rate'] * (1 + t.get('fee_open', fee)))
            equity += pnl
            coin_pnl[t['pair']] += pnl
            trade_pnl[str(trade_id)] = pnl
        # Unlisted constituents stay in cash until their first available opening.
        benchmark = INITIAL * sum(
            float(f.loc[day, 'close']) / float(f.iloc[0]['open'])
            * (1 - fee) / (1 + fee) if len(f) and day >= f.index[0] else 1.0
            for f in frames.values()) / len(frames)
        bh_coin = {p: INITIAL / len(frames) * (float(f.loc[day, 'close'])
                   / float(f.iloc[0]['open']) * (1 - fee) / (1 + fee) - 1)
                   if len(f) and day >= f.index[0] else 0.0 for p, f in frames.items()}
        daily.append({'date': day.date().isoformat(),
                      'return_pct': (equity / rows[-1]['equity'] - 1) * 100,
                      'buy_hold_return_pct': (benchmark / rows[-1]['buy_hold_equity'] - 1) * 100,
                      'fees_cumulative': fees, 'per_coin_cumulative': coin_pnl,
                      'per_trade_cumulative': trade_pnl, 'buy_hold_per_coin_cumulative': bh_coin})
        rows.append({'date': (day + pd.Timedelta(days=1)).isoformat(),
                     'equity': equity, 'buy_hold_equity': benchmark})
    equity_df = pd.DataFrame(rows)
    final = float(equity_df.equity.iloc[-1])
    engine_final = float(stats.get('final_balance', INITIAL))
    if abs(final - engine_final) > 0.02:
        raise ValueError(f'Equity/engine mismatch: {final} vs {engine_final}')
    drawdown = (1 - equity_df.equity / equity_df.equity.cummax()).max() * 100
    net = engine_final - INITIAL
    fees = sum(t['amount'] * (t['open_rate'] * t.get('fee_open', fee)
                              + t['close_rate'] * t.get('fee_close', fee)) for t in trades)
    profits = sorted((t['profit_abs'] for t in closed), reverse=True)
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    best = max(profits, default=0)
    def trade_record(t, is_open):
        return {'trade_id': trades.index(t), 'pair': t['pair'], 'entry_date': t['open_date'], 'entry_price': t['open_rate'],
                'amount': t['amount'], 'profit_usdt': t['profit_abs'],
                'fees_usdt': t['amount'] * (t['open_rate'] * t.get('fee_open', fee)
                                           + t['close_rate'] * t.get('fee_close', fee)),
                'profit_pct': t['profit_abs'] / (t['amount'] * t['open_rate']
                                               * (1 + t.get('fee_open', fee))) * 100,
                'holding_days': (pd.Timestamp(t['close_date'])
                                 - pd.Timestamp(t['open_date'])).total_seconds() / 86400,
                'status': 'açık (değerleme)' if is_open else 'kapalı',
                'exit_date': None if is_open else t['close_date'],
                'exit_price': None if is_open else t['close_rate'],
                'valuation_date': t['close_date'] if is_open else None,
                'valuation_price': t['close_rate'] if is_open else None,
                'exit_reason': None if is_open else t['exit_reason']}
    return {
        'gross_profit_usdt': net + fees, 'total_fees_usdt': fees, 'net_profit_usdt': net,
        'top3_profit_share_pct': sum(profits[:3]) / net * 100 if net > 0 else None,
        'best_trade_profit_share_pct': best / net * 100 if net > 0 and profits else None,
        'net_without_best_trade_usdt': net - best,
        'net_without_best_trade_pct': (net - best) / INITIAL * 100,
        'per_coin_contribution': daily[-1]['per_coin_cumulative'] if daily else
                                 {p: 0.0 for p in frames},
        'win_rate_pct': len(wins) / len(closed) * 100 if closed else None,
        'avg_win_usdt': sum(wins) / len(wins) if wins else None,
        'avg_loss_usdt': sum(losses) / len(losses) if losses else None,
        'avg_win_loss_ratio': (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))
                              if wins and losses else None,
        'daily_returns': daily,
        'trade_metrics_method': 'Closed trades only for win rate and concentration; net includes terminal valuation. Shares undefined for net <= 0. Fees include modeled terminal liquidation.',
        'track': track, 'start_date': start.date().isoformat(), 'updated_utc': updated,
        'date': dates[-1].date().isoformat() if len(dates) else None,
        'status': 'active' if len(dates) else 'not_started',
        'balance': engine_final, 'profit_pct': (engine_final / INITIAL - 1) * 100,
        'trades': len(closed), 'entries': len(trades),
        'open_positions': [trade_record(t, True) for t in opened],
        'closed_trades': [trade_record(t, False) for t in closed],
        'max_drawdown_pct': float(drawdown),
        'engine_max_drawdown_pct': stats.get('max_drawdown_account', 0) * 100,
        'buy_hold_profit_pct': (equity_df.buy_hold_equity.iloc[-1] / INITIAL - 1) * 100
        if len(dates) else None,
        'buy_hold_pairs': list(candles), 'fee_per_side': fee,
        'equity_method': 'Daily close net liquidation; terminal force_exit uses engine last open.',
    }, equity_df


def render_readme(summaries, updated):
    lines = ['# İleriye dönük sanal işlem kaydı', '', f'Son güncelleme (UTC): {updated}', '',
             '| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |',
             '|---|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        bh = '—' if s['buy_hold_profit_pct'] is None else f"%{s['buy_hold_profit_pct']:.2f}"
        state = ('Evren snapshot bekleniyor' if s.get('universe_pending') else
                 'Başlamadı' if s['status'] == 'not_started' else s['date'])
        lines.append(f"| {s['track'].upper()} | {state} | {s['balance']:.2f} | "
                     f"%{s['profit_pct']:.2f} | {bh} | {s['trades']} / "
                     f"{len(s['open_positions'])} | %{s['max_drawdown_pct']:.2f} |")
    lines += ['', 'Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.', '',
              ('Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti '
              'her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.'), '',
              ('Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. '
              'Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak '
              'ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar '
              'gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin '
              'motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.'), '',
              '**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**', '']
    return '\n'.join(lines)
