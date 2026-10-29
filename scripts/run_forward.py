"""Recompute the fixed forward window using only fully closed UTC daily candles."""
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import pandas as pd
from freqtrade.data.history.datahandlers.featherdatahandler import FeatherDataHandler
from freqtrade.enums import CandleType

# Also works as `python scripts/run_forward.py`.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.freeze_check import check as freeze_check
from scripts.health import data_health, record_run
from scripts.reporting import INITIAL, START_DATE, build_summary, render_readme
from scripts.tracks import TRACKS, all_pairs
from scripts.tracks import configs as track_configs

DATA = ROOT / 'data/binance'


def run_freqtrade(args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    # Avoid implicit Freqtrade config overrides in a developer's shell.
    env = {k: v for k, v in env.items() if not k.startswith('FREQTRADE__')}
    subprocess.run([sys.executable, str(ROOT / 'scripts/freqtrade_public.py'), *args],
                   cwd=ROOT, env=env, check=True)


def runtime_config(config, path):
    if config['dry_run'] is not True or config['exchange']['key'] or config['exchange']['secret']:
        raise ValueError('Unsafe exchange configuration')
    if config['api_server']['enabled'] or config['telegram']['enabled']:
        raise ValueError('External interfaces must be disabled')
    # This release requires auth fields even for a disabled api_server section.
    # Omit the unused section altogether instead of introducing any auth material.
    config = {k: v for k, v in config.items() if k != 'api_server'}
    path.write_text(json.dumps(config))
    return path


def load_closed(pairs, today, history_start="2025-01-01", listings=None):
    handler = FeatherDataHandler(DATA)
    result = {}
    expected = pd.date_range(pd.Timestamp(history_start, tz='UTC'),
                             today - pd.Timedelta(days=1), freq='D').as_unit('ms')
    for pair in pairs:
        frame = handler.ohlcv_load(pair, '1d', CandleType.SPOT, fill_missing=False,
                                   drop_incomplete=False)
        frame = frame.loc[(frame.date >= expected[0]) & (frame.date < today)].reset_index(drop=True)
        pair_expected = expected
        if listings and pair in listings:
            pair_expected = expected[expected >= pd.Timestamp(listings[pair])]
        if not pd.DatetimeIndex(frame.date).equals(pair_expected):
            raise ValueError(f'{pair}: missing/stale/duplicate daily candles; refusing partial report')
        if (frame.isna().any().any()
                or (frame[['open', 'high', 'low', 'close']] <= 0).any().any()
                or (frame.volume < 0).any()):
            raise ValueError(f'{pair}: invalid OHLCV value')
        handler.ohlcv_store(pair, '1d', frame, CandleType.SPOT)
        # Read the stored format with Freqtrade itself, without filling gaps.
        loaded = handler.ohlcv_load(pair, '1d', CandleType.SPOT, fill_missing=False,
                                    drop_incomplete=False)
        pd.testing.assert_frame_equal(frame, loaded, check_dtype=False)
        result[pair] = frame
    return result


def backtest_start(start=START_DATE):
    """Backtest timerange begins one day before START_DATE.

    Freqtrade shifts signals by one candle *after* trimming to the timerange, so the
    first candle in range can never enter. Starting a day early lets the signal from
    the day before START_DATE fill at START_DATE's open, exactly like a live bot that
    starts that morning. No position can open before START_DATE.
    """
    return (pd.Timestamp(start) - pd.Timedelta(days=1)).strftime('%Y%m%d')


def backtest(config_path, strategy, start, output, end='', fee=0.0015):
    run_freqtrade(['backtesting', '-c', str(config_path), '--userdir', str(ROOT / 'user_data'),
                   '--datadir', str(DATA), '--strategy', strategy, '--timerange', start + '-' + end,
                   '--fee', str(fee), '--enable-protections', '--export', 'trades',
                   '--cache', 'none', '--export-directory', str(output)])
    archives = sorted(output.glob('*.zip'))
    if len(archives) != 1:
        raise ValueError(f'Expected one backtest archive, found {archives}')
    with zipfile.ZipFile(archives[0]) as archive:
        names = [n for n in archive.namelist() if n.endswith('.json')
                 and not n.endswith(('.meta.json', '_config.json'))]
        reports = [json.loads(archive.read(n)) for n in names]
    return next(r['strategy'][strategy] for r in reports if 'strategy' in r)


def runnable_configs():
    try:
        return track_configs()
    except ValueError:
        # Only explicitly pending preregistered universes may be skipped.
        result = {}
        for track in TRACKS:
            if track in ('r7', 'r8'):
                universe = json.loads((ROOT / f'universes/{track}.json').read_text())
                if universe.get('status') == 'pending':
                    continue
            config = json.loads((ROOT / f'user_data/config_{track}.json').read_text())
            if not config['exchange']['pair_whitelist']:
                raise ValueError(f'{track}: empty ready universe') from None
            result[track] = config
        return result


def execute():
    os.chdir(ROOT)
    freeze_check()
    subprocess.run([sys.executable, 'scripts/secret_scan.py'], check=True)
    now = pd.Timestamp.now(tz='UTC')
    today = now.normalize()
    updated = now.isoformat()
    configs = runnable_configs()
    pairs = all_pairs(configs)
    with tempfile.TemporaryDirectory(prefix='forward-paper-') as temp:
        temp = Path(temp)
        runtime = {t: runtime_config(c, temp / f'{t}.json') for t, c in configs.items()}
        download = json.loads((ROOT / 'user_data/config_r5.json').read_text())
        download['exchange']['pair_whitelist'] = pairs
        download_path = runtime_config(download, temp / 'download.json')
        run_freqtrade(['download-data', '-c', str(download_path), '--datadir', str(DATA),
                       '--timeframes', '1d', '--timerange', '20250101-'])
        listings = json.loads((ROOT / 'listing_dates.json').read_text())
        candles = load_closed(pairs, today, listings=listings)
        health = data_health(candles, pairs, today, listings=listings)
        if health['pairs_missing']:
            raise ValueError('Data health failed')
        summaries = []
        pending = []
        for track, config in configs.items():
            track_pairs = config['exchange']['pair_whitelist']
            stats = {'trades': [], 'final_balance': INITIAL}
            if today > pd.Timestamp(START_DATE, tz='UTC'):
                output = temp / track
                output.mkdir()
                stats = backtest(runtime[track], TRACKS[track]['strategy'],
                                 backtest_start(), output)
            summary, equity = build_summary(track, stats, {p: candles[p] for p in track_pairs},
                                            START_DATE, updated)
            stress_fee = TRACKS[track].get('stress_fee')
            if stress_fee:
                stress_stats = {'trades': [], 'final_balance': INITIAL}
                if today > pd.Timestamp(START_DATE, tz='UTC'):
                    stress_out = temp / (track + '-stress')
                    stress_out.mkdir()
                    stress_stats = backtest(runtime[track], TRACKS[track]['strategy'],
                        backtest_start(), stress_out, fee=stress_fee)
                stress, stress_equity = build_summary(track, stress_stats,
                    {p: candles[p] for p in track_pairs}, START_DATE, updated, fee=stress_fee)
                summary['fee_stress'] = {'fee_per_side': stress_fee,
                    'profit_pct': stress['profit_pct'],
                    'max_drawdown_pct': stress['max_drawdown_pct'],
                    'curve': stress_equity.to_dict(orient='records')}
            summaries.append(summary)
            pending.append((track, summary, equity))
        for track in TRACKS.keys() - configs.keys():
            summary, equity = build_summary(track, {'trades': [], 'final_balance': INITIAL},
                                            {}, START_DATE, updated)
            summary['universe_pending'] = True
            summaries.append(summary)
            pending.append((track, summary, equity))
        summaries.sort(key=lambda s: list(TRACKS).index(s['track']))
        after = data_health(load_closed(pairs, today, listings=listings), pairs, today,
                            listings=listings)
        if after['pairs_missing']:
            raise ValueError('Post-run data health failed')
        # Publish only after ALL tracks validate successfully.
        for track, summary, equity in pending:
            out = ROOT / 'results' / track
            out.mkdir(parents=True, exist_ok=True)
            (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
            write_series(out, summary, equity)
        (ROOT / 'results/README.md').write_text(render_readme(summaries, updated))
    print('Forward reports complete; no live orders, no credentials.')


def write_series(out, summary, equity):
    equity.to_csv(out / 'equity.csv', index=False, float_format='%.8f')
    pd.DataFrame(summary['daily_returns'], columns=[
        'date', 'return_pct', 'buy_hold_return_pct', 'fees_cumulative',
        'per_coin_cumulative', 'per_trade_cumulative',
        'buy_hold_per_coin_cumulative']).to_csv(out / 'daily_returns.csv', index=False)
    fields = ['pair', 'entry_date', 'entry_price', 'amount', 'profit_usdt', 'fees_usdt',
              'profit_pct', 'holding_days', 'status', 'exit_date', 'exit_price',
              'valuation_date', 'valuation_price', 'exit_reason']
    pd.DataFrame(summary['closed_trades'] + summary['open_positions'], columns=fields).to_csv(
        out / 'trades.csv', index=False)


def snapshot():
    pairs = all_pairs(runnable_configs())
    handler = FeatherDataHandler(DATA)
    candles = {p: handler.ohlcv_load(p, '1d', CandleType.SPOT, fill_missing=False,
                                    drop_incomplete=False) for p in pairs}
    today = pd.Timestamp.now(tz='UTC').normalize()
    candles = {p: f.loc[f.date < today] for p, f in candles.items()}
    listings_path = ROOT / 'listing_dates.json'
    listings = json.loads(listings_path.read_text()) if listings_path.exists() else {}
    return data_health(candles, pairs, today, listings=listings)


def main():
    started = pd.Timestamp.now(tz='UTC').isoformat()
    clock = time.monotonic()
    before, after, success, reason = {}, {}, False, None
    try:
        freeze_check()
        before = snapshot()
        execute()
        after = snapshot()
        success = not after['pairs_missing']
        if not success:
            raise ValueError('Data health failed')
    except Exception as error:
        from scripts.freeze_check import MESSAGE
        reason = 'freeze' if str(error) == MESSAGE else 'run_failed'
        if reason != 'freeze':
            try:
                after = snapshot()
            except (OSError, ValueError, KeyError):
                after = {}
        raise
    finally:
        record_run(ROOT / 'results/health.json', started, success, before, after,
                   time.monotonic() - clock, reason)


if __name__ == '__main__':
    main()
