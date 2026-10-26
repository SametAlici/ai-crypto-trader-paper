"""Historical smoke test; temporary artifacts only, never writes forward results."""
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.reporting import build_summary
from scripts.run_forward import ROOT, backtest, load_closed, runtime_config


def main():
    today = pd.Timestamp.now(tz='UTC').normalize()
    broad = json.loads((ROOT / 'user_data/config_r5.json').read_text())
    candles = load_closed(broad['exchange']['pair_whitelist'], today)
    with tempfile.TemporaryDirectory(prefix='paper-smoke-') as directory:
        directory = Path(directory)
        cases = [('r1', '20260901'), ('r5', '20260901'),
                 ('r1', (today - pd.Timedelta(days=1)).strftime('%Y%m%d'))]
        for track, start in cases:
            config = json.loads((ROOT / f'user_data/config_{track}.json').read_text())
            path = runtime_config(config, directory / f'{track}.json')
            output = directory / f'{track}-{start}'
            output.mkdir()
            stats = backtest(path, f'{track.upper()}_TSMomentum', start, output)
            summary, curve = build_summary(
                track, stats, {p: candles[p] for p in config['exchange']['pair_whitelist']},
                pd.Timestamp(start).isoformat(), today.isoformat())
            print(f"VALIDATED {track} {start}: entries={summary['entries']}, closed={summary['trades']}, "
                  f"open={len(summary['open_positions'])}, balance={summary['balance']:.8f}, "
                  f"equity_rows={len(curve)}", flush=True)


if __name__ == '__main__':
    main()
