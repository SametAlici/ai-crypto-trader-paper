"""One-time frozen historical reference. Never called by the nightly workflow."""
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.freeze_check import check
from scripts.reporting import build_summary
from scripts.run_forward import (
    DATA,
    ROOT,
    backtest,
    load_closed,
    run_freqtrade,
    runtime_config,
    write_series,
)
from scripts.tracks import REFERENCE_TRACKS

LABEL = ('Geçmiş simülasyon (referans) — ileriye dönük test değildir; '
         'bu dönem strateji geliştirmede kullanıldı')


def main():
    check()
    destination = ROOT / 'results/reference'
    if destination.exists():
        raise SystemExit('Reference already exists; refusing to overwrite the historical snapshot.')
    configs = {t: json.loads((ROOT / f'user_data/config_{t}.json').read_text())
               for t in REFERENCE_TRACKS}
    listings = {}
    for pair in configs['r5']['exchange']['pair_whitelist']:
        query = urlencode({'symbol': pair.replace('/', ''), 'interval': '1d',
                           'startTime': 0, 'limit': 1})
        with urlopen('https://data-api.binance.vision/api/v3/klines?' + query, timeout=30) as r:
            rows = json.load(r)
        listings[pair] = pd.Timestamp(rows[0][0], unit='ms', tz='UTC').isoformat()
    (ROOT / 'listing_dates.json').write_text(json.dumps(listings, indent=2) + '\n')
    with tempfile.TemporaryDirectory(prefix='paper-reference-') as temp:
        temp = Path(temp)
        runtime = {t: runtime_config(c, temp / f'{t}.json') for t, c in configs.items()}
        run_freqtrade(['download-data', '-c', str(runtime['r5']), '--datadir', str(DATA),
                       '--timeframes', '1d', '--timerange', '20221101-20261026', '--prepend'])
        # Prepend drops the stored terminal row; refresh the tail before validation.
        run_freqtrade(['download-data', '-c', str(runtime['r5']), '--datadir', str(DATA),
                       '--timeframes', '1d', '--timerange', '20221101-'])
        candles = load_closed(configs['r5']['exchange']['pair_whitelist'],
                              pd.Timestamp('2026-10-26', tz='UTC'), '2022-11-01', listings)
        pending = []
        for track, config in configs.items():
            out = temp / track
            out.mkdir()
            stats = backtest(runtime[track], f'{track.upper()}_TSMomentum', '20240101', out,
                             end='20261026')
            summary, curve = build_summary(track, stats,
                {p: candles[p] for p in config['exchange']['pair_whitelist']},
                '2024-01-01', pd.Timestamp.now(tz='UTC').isoformat())
            summary.update(label=LABEL, end_exclusive='2026-10-26',
                           frozen_sha256=json.loads((ROOT / 'frozen.json').read_text())['sha256'])
            pending.append((track, summary, curve))
        check()
        for track, summary, curve in pending:
            out = destination / track
            out.mkdir(parents=True)
            (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
            write_series(out, summary, curve)
        (destination / 'README.md').write_text('# ' + LABEL + '\n\n'
            '2024-01-01 ≤ UTC < 2026-10-26. Son kapalı mum: 2026-10-25. '
            'Sabit snapshot; nightly yeniden hesaplamaz. Her yönde ücret: 0.0015; '
            'korumalar etkin. Listeleme öncesi al-tut payı nakitte tutulur.\n')


if __name__ == '__main__':
    main()
