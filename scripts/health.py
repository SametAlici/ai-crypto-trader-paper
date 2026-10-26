"""Daily candle continuity and durable run ledger; no credentials or raw errors."""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.reporting import START_DATE


def data_health(candles, pairs, today, start=START_DATE, listings=None):
    import pandas as pd
    today = pd.Timestamp(today)
    today = today.tz_localize('UTC') if today.tzinfo is None else today.tz_convert('UTC')
    yesterday = today - pd.Timedelta(days=1)
    start = pd.Timestamp(start, tz='UTC')
    listings = listings or {}
    details = {}
    for pair in pairs:
        frame = candles.get(pair)
        dates = pd.DatetimeIndex([], tz='UTC') if frame is None else pd.DatetimeIndex(frame.date)
        # Feather data may arrive tz-naive depending on the loader; compare in UTC.
        dates = dates.tz_localize('UTC') if dates.tz is None else dates.tz_convert('UTC')
        listing = pd.Timestamp(listings.get(pair, start.isoformat()))
        if listing.tzinfo is None:
            listing = listing.tz_localize('UTC')
        first = max(start, listing.normalize())
        expected = pd.date_range(first, yesterday, freq='D')
        actual = dates[(dates >= first) & (dates < today)]
        missing = expected.difference(actual)
        fresh = bool(len(dates) and dates.max() == yesterday)
        invalid = False
        if frame is not None and {'open', 'high', 'low', 'close', 'volume'} <= set(frame):
            invalid = bool(frame.isna().any().any()
                           or (frame[['open', 'high', 'low', 'close']] <= 0).any().any()
                           or (frame.volume < 0).any())
        ok = fresh and not len(missing) and not dates.has_duplicates and not invalid
        details[pair] = {'ok': ok, 'latest_closed': dates.max().date().isoformat()
                         if len(dates) else None, 'missing_days': [d.date().isoformat()
                         for d in missing], 'listing_date': listing.date().isoformat(),
                         'listing_gap_days': max(0, (listing.normalize() - start).days),
                         'duplicate_days': dates.has_duplicates, 'invalid_ohlcv': invalid}
    return {'expected_latest': yesterday.date().isoformat(),
            'data_freshness': all(d['latest_closed'] == yesterday.date().isoformat()
                                  for d in details.values()),
            'pairs_ok': [p for p, d in details.items() if d['ok']],
            'pairs_missing': [p for p, d in details.items() if not d['ok']], 'pairs': details}


def record_run(path, started, success, before, after, duration, reason=None):
    path = Path(path)
    ledger = json.loads(path.read_text()) if path.exists() else {'runs': []}
    ledger['runs'].append({'run_date': started, 'success': success,
                           'data_freshness': after.get('data_freshness', False),
                           'pairs_ok': after.get('pairs_ok', []),
                           'pairs_missing': after.get('pairs_missing', []),
                           'duration_seconds': round(duration, 3),
                           'before': before, 'after': after, 'reason': reason})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def run_counts(ledger, now):
    # A run is due at 00:20 UTC after the first forward day closes.
    now = datetime.fromisoformat(str(now)).astimezone(UTC)
    first = datetime.fromisoformat(START_DATE).replace(tzinfo=UTC) + timedelta(
        days=1, minutes=20)
    expected = max(0, (now - first).days + 1)
    last_due = (now - timedelta(minutes=20)).date()
    dates = {datetime.fromisoformat(r['run_date']).date() for r in ledger.get('runs', [])
             if r['success'] and first.date() <= datetime.fromisoformat(r['run_date']).date()
             <= last_due}
    return {'expected': expected, 'actual': len(dates), 'missing': max(0, expected - len(dates))}
