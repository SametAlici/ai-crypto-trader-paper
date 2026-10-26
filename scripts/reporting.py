"""Report engine trades separately from terminal forced valuations."""
import pandas as pd

FEE = 0.0015
START_DATE = '2026-10-27'
INITIAL = 1000.0


def build_summary(track, stats, candles, start, updated):
    start = pd.Timestamp(start)
    if start.tzinfo is None:
        start = start.tz_localize('UTC')
    frames = {p: df.loc[df.date >= start].set_index('date') for p, df in candles.items()}
    dates = next(iter(frames.values())).index if frames else pd.DatetimeIndex([])
    trades = stats.get('trades', [])
    closed = [t for t in trades if t['exit_reason'] != 'force_exit']
    opened = [t for t in trades if t['exit_reason'] == 'force_exit']
    rows = [{'date': start.isoformat(), 'equity': INITIAL, 'buy_hold_equity': INITIAL}]
    for day in dates:
        equity = INITIAL
        for t in trades:
            if pd.Timestamp(t['open_date']) > day:
                continue
            if t['exit_reason'] != 'force_exit' and pd.Timestamp(t['close_date']) <= day:
                equity += t['profit_abs']
            else:
                mark = float(frames[t['pair']].loc[day, 'close'])
                # Freqtrade 2026.9 forces terminal exits at the last candle's OPEN.
                if day == dates[-1] and t['exit_reason'] == 'force_exit':
                    equity += t['profit_abs']
                else:
                    equity += (t['amount'] * mark * (1 - t.get('fee_close', FEE))
                               - t['amount'] * t['open_rate'] * (1 + t.get('fee_open', FEE)))
        benchmark = INITIAL * sum(
            float(f.loc[day, 'close']) / float(f.iloc[0]['open'])
            * (1 - FEE) / (1 + FEE) for f in frames.values()) / len(frames)
        rows.append({'date': (day + pd.Timedelta(days=1)).isoformat(),
                     'equity': equity, 'buy_hold_equity': benchmark})
    equity_df = pd.DataFrame(rows)
    final = float(equity_df.equity.iloc[-1])
    engine_final = float(stats.get('final_balance', INITIAL))
    if abs(final - engine_final) > 0.02:
        raise ValueError(f'Equity/engine mismatch: {final} vs {engine_final}')
    drawdown = (1 - equity_df.equity / equity_df.equity.cummax()).max() * 100
    def trade_record(t, is_open):
        return {'pair': t['pair'], 'entry_date': t['open_date'], 'entry_price': t['open_rate'],
                'amount': t['amount'], 'profit_usdt': t['profit_abs'],
                'status': 'açık (değerleme)' if is_open else 'kapalı',
                'exit_date': None if is_open else t['close_date'],
                'exit_price': None if is_open else t['close_rate'],
                'valuation_date': t['close_date'] if is_open else None,
                'valuation_price': t['close_rate'] if is_open else None,
                'exit_reason': None if is_open else t['exit_reason']}
    return {
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
        'buy_hold_pairs': list(candles), 'fee_per_side': FEE,
        'equity_method': 'Daily close net liquidation; terminal force_exit uses engine last open.',
    }, equity_df


def render_readme(summaries, updated):
    lines = ['# İleriye dönük sanal işlem kaydı', '', f'Son güncelleme (UTC): {updated}', '',
             '| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |',
             '|---|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        bh = '—' if s['buy_hold_profit_pct'] is None else f"%{s['buy_hold_profit_pct']:.2f}"
        state = 'Başlamadı' if s['status'] == 'not_started' else s['date']
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
