"""Build a dependency-free public dashboard from allowlisted report fields only."""
import argparse
import csv
import json
import math
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.tracks import REFERENCE_TRACKS, TRACKS

DOMAIN = 'trade.blacktowhitestudio.com'


def number(value, signed=False, digits=1):
    if value is None:
        return '—'
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite report value')
    return format(value, f'{"+" if signed else ""},.{digits}f').translate(
        str.maketrans({',': '.', '.': ','}))


def percent(value):
    return '—' if value is None else number(value, signed=True) + '%'


def timestamp(value, zone='UTC'):
    if not value:
        return '—'
    date = datetime.fromisoformat(value)
    if date.tzinfo is None:
        raise ValueError('Report timestamps must have a timezone')
    return date.astimezone(ZoneInfo(zone)).strftime('%d.%m.%Y %H:%M')


def load_reports(results, tracks=None):
    reports = {}
    for track in (tracks if tracks is not None else TRACKS):
        summary = json.loads((results / track / 'summary.json').read_text(encoding='utf-8'))
        with (results / track / 'equity.csv').open(encoding='utf-8', newline='') as source:
            curve = list(csv.DictReader(source))
        if not curve:
            raise ValueError('Empty equity curve')
        for row in curve:
            timestamp(row['date'])
            for field in ('equity', 'buy_hold_equity'):
                value = float(row[field])
                if not math.isfinite(value) or value <= 0:
                    raise ValueError('Invalid equity value')
                row[field] = value
        if [r['date'] for r in curve] != sorted({r['date'] for r in curve}):
            raise ValueError('Equity dates must be unique and ordered')
        reports[track] = (summary, curve)
    if any([r['date'] for r in curve] != [r['date'] for r in reports['r1'][1]]
           for summary, curve in reports.values() if not summary.get('universe_pending')):
        raise ValueError('Track dates do not match')
    return reports


def benchmark(reports):
    summary, curve = reports['r5']
    values = [r['buy_hold_equity'] for r in curve]
    peak = values[0]
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = max(drawdown, (1 - value / peak) * 100)
    started = summary['status'] != 'not_started'
    return {'profit_pct': (values[-1] / values[0] - 1) * 100 if started else None,
            'max_drawdown_pct': drawdown if started else None}



REFERENCE_LABEL = ('Geçmiş simülasyon (referans) — ileriye dönük test değildir; '
                   'bu dönem strateji geliştirmede kullanıldı')
SUMMARY_FIELDS = ('track', 'start_date', 'updated_utc', 'date', 'status', 'profit_pct',
                  'max_drawdown_pct', 'trades', 'total_fees_usdt', 'daily_returns',
                  'buy_hold_pairs', 'open_positions', 'closed_trades', 'fee_stress', 'universe_pending')
TRADE_FIELDS = ('trade_id', 'pair', 'entry_date', 'entry_price', 'amount', 'profit_usdt',
                'fees_usdt', 'profit_pct', 'holding_days', 'exit_date', 'exit_price',
                'valuation_date', 'valuation_price')
DAILY_FIELDS = ('date', 'return_pct', 'buy_hold_return_pct', 'fees_cumulative',
                'per_coin_cumulative', 'per_trade_cumulative', 'buy_hold_per_coin_cumulative')


def public_reports(reports):
    data = {}
    for track, (summary, curve) in reports.items():
        safe = {k: summary[k] for k in SUMMARY_FIELDS if k in summary}
        for name in ('closed_trades', 'open_positions'):
            safe[name] = [{k: t[k] for k in TRADE_FIELDS if k in t} for t in safe[name]]
        safe['daily_returns'] = [{k: d[k] for k in DAILY_FIELDS if k in d}
                                 for d in safe.get('daily_returns', [])]
        data[track] = {'summary': safe, 'curve': curve}
    return data


def public_health(results, latest):
    from scripts.health import run_counts
    from scripts.reporting import START_DATE
    path = results / 'health.json'
    ledger = json.loads(path.read_text()) if path.exists() else {'runs': []}
    fields = ('run_date', 'success', 'data_freshness', 'pairs_ok', 'pairs_missing',
              'duration_seconds', 'reason')
    last_pairs = ledger['runs'][-1].get('after', {}).get('pairs', {}) if ledger['runs'] else {}
    latest_dates = [d.get('latest_closed') for d in last_pairs.values()]
    latest_closed = min(latest_dates) if latest_dates and all(latest_dates) else None
    return {'counts': run_counts(ledger, latest), 'start_date': START_DATE,
            'latest_closed': latest_closed,
            'successful_dates': sorted({r['run_date'][:10] for r in ledger['runs']
                                        if r['success']}),
            'runs': [{k: r[k] for k in fields if k in r} for r in ledger['runs'][-30:]]}


def load_research(directory=ROOT / 'research'):
    from scripts.secret_scan import inspect_file
    source = directory / 'research_snapshot.json'
    if not source.exists():
        return None
    files = [source, *sorted((directory / 'research_equity').glob('*.csv'))]
    if any(inspect_file(p) for p in files):
        raise ValueError('Research secret scan failed')
    raw = json.loads(source.read_text())
    fields = {
        'strategies': ('name', 'family', 'timeframe', 'description', 'status', 'elimination_reason'),
        'evaluations': ('strategy', 'evidence_type', 'universe', 'period', 'fee', 'trades',
                        'net_return_pct', 'max_dd_pct', 'dd_type', 'winrate_pct', 'calmar'),
        'fee_stress': ('strategy', 'evidence_type', 'universe', 'fee', 'net_return_pct'),
        'concentration': ('strategy', 'universe', 'fee', 'top3_share_pct',
                          'without_best1_pct', 'without_best3_pct', 'without_best5_pct'),
    }
    result = {key: [{f: row.get(f) for f in allowed} for row in raw[key]]
              for key, allowed in fields.items()}
    ai = raw['ai_summary']
    result['ai_summary'] = {k: ai[k] for k in ('tried', 'calibration_bug', 'verdict')}
    result['ai_summary']['key_numbers'] = [
        {k: r.get(k) for k in ('experiment', 'trades', 'net_return_pct', 'max_dd_pct',
                               'training_events', 'cv_events', 'cv_auc', 'threshold')}
        for r in ai['key_numbers']]
    result['decision_criteria'] = raw['decision_criteria']
    result['limitations'] = raw['meta']['limitations']
    result['generated_at'] = raw['meta']['generated_at']
    result['equity_series'] = []
    for series in raw['equity_series']:
        path = directory / 'research_equity' / Path(series['csv']).name
        with path.open(newline='') as source_csv:
            curve = [{'date': r['date'], 'value': float(r['value'])}
                     for r in csv.DictReader(source_csv)]
        if not curve or any(not math.isfinite(r['value']) or r['value'] <= 0 for r in curve):
            raise ValueError('Invalid research equity')
        if [r['date'] for r in curve] != sorted({r['date'] for r in curve}):
            raise ValueError('Invalid research dates')
        result['equity_series'].append({k: series[k] for k in
            ('strategy', 'evidence_type', 'fee', 'dd_type', 'sampling')} | {'curve': curve})
    return result


def build_site(results=ROOT / 'results', output=ROOT / 'site'):
    reports = load_reports(results)
    latest = max(s['updated_utc'] for s, _ in reports.values())
    views = {'forward': public_reports(reports)}
    reference = None
    if (results / 'reference/r1/summary.json').exists():
        reference = public_reports(load_reports(results / 'reference', REFERENCE_TRACKS))
    payload = {
        'registry': TRACKS, 'research': load_research(), 'views': views,
        'reference_url': 'reference.json' if reference else None,
        'health': public_health(results, datetime.now(ZoneInfo('UTC')).isoformat()),
    }
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace(
        '&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    # Script JSON is escaped separately from HTML. Never interpolate input into JavaScript.
    encoded = encoded.replace(chr(0x2028), '\\u2028').replace(chr(0x2029), '\\u2029')
    html = (ROOT / 'scripts/site.html').read_text().replace('@@DATA@@', encoded)
    html = html.replace('@@UPDATED@@', escape(timestamp(latest) + ' UTC · '
                        + timestamp(latest, 'Europe/Istanbul') + ' Türkiye saati'))
    html = html.replace('@@REFERENCE@@', REFERENCE_LABEL)
    output.mkdir(parents=True, exist_ok=True)
    if reference is not None:
        (output / 'reference.json').write_text(
            json.dumps(reference, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
            encoding='utf-8')
    else:
        (output / 'reference.json').unlink(missing_ok=True)
    for asset in ('logo.svg', 'favicon.svg'):
        (output / asset).write_bytes((ROOT / 'site_assets' / asset).read_bytes())
    (output / 'index.html').write_text(html, encoding='utf-8')
    for source, target in [('site.css', 'style.css'), ('site.js', 'app.js'),
                           ('site_metrics.js', 'metrics.js')]:
        (output / target).write_text((ROOT / 'scripts' / source).read_text(), encoding='utf-8')
    (output / 'CNAME').write_text(DOMAIN + '\n', encoding='utf-8')
    return output / 'index.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'results')
    parser.add_argument('--output', type=Path, default=ROOT / 'site')
    args = parser.parse_args()
    build_site(args.results, args.output)
