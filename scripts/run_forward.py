"""Recompute the fixed forward window using only fully closed UTC daily candles."""
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from freqtrade.data.history.datahandlers.featherdatahandler import FeatherDataHandler
from freqtrade.enums import CandleType

# Also works as `python scripts/run_forward.py`.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.reporting import INITIAL, START_DATE, build_summary, render_readme

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


def load_closed(pairs, today):
    handler = FeatherDataHandler(DATA)
    result = {}
    expected = pd.date_range(pd.Timestamp('2025-01-01', tz='UTC'),
                             today - pd.Timedelta(days=1), freq='D').as_unit('ms')
    for pair in pairs:
        frame = handler.ohlcv_load(pair, '1d', CandleType.SPOT, fill_missing=False,
                                   drop_incomplete=False)
        frame = frame.loc[(frame.date >= expected[0]) & (frame.date < today)].reset_index(drop=True)
        if not pd.DatetimeIndex(frame.date).equals(expected):
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


def backtest(config_path, strategy, start, output):
    run_freqtrade(['backtesting', '-c', str(config_path), '--userdir', str(ROOT / 'user_data'),
                   '--datadir', str(DATA), '--strategy', strategy, '--timerange', start + '-',
                   '--fee', '0.0015', '--enable-protections', '--export', 'trades',
                   '--cache', 'none', '--export-directory', str(output)])
    archives = sorted(output.glob('*.zip'))
    if len(archives) != 1:
        raise ValueError(f'Expected one backtest archive, found {archives}')
    with zipfile.ZipFile(archives[0]) as archive:
        names = [n for n in archive.namelist() if n.endswith('.json')
                 and not n.endswith(('.meta.json', '_config.json'))]
        reports = [json.loads(archive.read(n)) for n in names]
    return next(r['strategy'][strategy] for r in reports if 'strategy' in r)


def main():
    os.chdir(ROOT)
    subprocess.run([sys.executable, 'scripts/secret_scan.py'], check=True)
    now = pd.Timestamp.now(tz='UTC')
    today = now.normalize()
    updated = now.isoformat()
    configs = {t: json.loads((ROOT / f'user_data/config_{t}.json').read_text())
               for t in ('r1', 'r5')}
    with tempfile.TemporaryDirectory(prefix='forward-paper-') as temp:
        temp = Path(temp)
        runtime = {t: runtime_config(c, temp / f'{t}.json') for t, c in configs.items()}
        run_freqtrade(['download-data', '-c', str(runtime['r5']), '--datadir', str(DATA),
                       '--timeframes', '1d', '--timerange', '20250101-'])
        candles = load_closed(configs['r5']['exchange']['pair_whitelist'], today)
        summaries = []
        pending = []
        for track, config in configs.items():
            pairs = config['exchange']['pair_whitelist']
            stats = {'trades': [], 'final_balance': INITIAL}
            if today > pd.Timestamp(START_DATE, tz='UTC'):
                output = temp / track
                output.mkdir()
                stats = backtest(runtime[track], f'{track.upper()}_TSMomentum',
                                 START_DATE.replace('-', ''), output)
            summary, equity = build_summary(track, stats, {p: candles[p] for p in pairs},
                                            START_DATE, updated)
            summaries.append(summary)
            pending.append((track, summary, equity))
        # Publish only after BOTH tracks validate successfully.
        for track, summary, equity in pending:
            out = ROOT / 'results' / track
            out.mkdir(parents=True, exist_ok=True)
            (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
            equity.to_csv(out / 'equity.csv', index=False, float_format='%.8f')
        (ROOT / 'results/README.md').write_text(render_readme(summaries, updated))
    print('Forward reports complete; no live orders, no credentials.')


if __name__ == '__main__':
    main()
