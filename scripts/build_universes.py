"""One-shot preregistered public API snapshot. Never reads performance results."""
import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOST = 'https://data-api.binance.vision/api/v3/'
GECKO = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1'
END = int(datetime(2026, 10, 27, tzinfo=UTC).timestamp() * 1000)
DAY = 86400000
STABLE = {'USDT', 'USDC', 'FDUSD', 'DAI', 'TUSD', 'USDE', 'SUSDE', 'PYUSD', 'USDD', 'USD1', 'USDS', 'SUSD', 'USDP', 'BUSD', 'UST', 'USTC', 'USDF', 'USDG', 'RLUSD', 'FRAX', 'LUSD', 'GUSD', 'EURC', 'EURI', 'AEUR', 'EURCV', 'XUSD', 'USD0', 'USUALUSD', 'USDDOLD', 'DOLA', 'USDB'}
FIAT = {'EUR', 'TRY', 'BRL', 'ARS', 'GBP', 'AUD', 'BIDR', 'BKRW', 'BVND', 'IDRT', 'NGN', 'PLN', 'RON', 'RUB', 'UAH', 'ZAR', 'UZS', 'JPY', 'CHF', 'CAD'}
WRAPPED = {'WBTC', 'WETH', 'STETH', 'WSTETH', 'WEETH', 'CBBTC', 'CBETH', 'RETH', 'WBETH', 'BETH', 'BTCB', 'WBNB', 'WTRX', 'WSETH', 'METH', 'EZETH', 'RSETH', 'LBTC', 'SOLVBTC', 'MSOL', 'JITOSOL', 'BBSOL', 'JUPSOL', 'STSOL', 'CETH', 'WBTCOLD'}


def excluded(symbol, coin=None):
    s = symbol.upper()
    if s in STABLE or s in FIAT or s in WRAPPED:
        return True
    # Jupiter (JUP) is a spot asset, not a leveraged UP token.
    if s != 'JUP' and s.endswith(('UP', 'DOWN', 'BULL', 'BEAR')):
        return True
    if coin:
        label = (coin.get('name', '') + ' ' + coin.get('id', '')).lower()
        categories = ' '.join(coin.get('categories', [])).lower()
        return any(x in label + ' ' + categories for x in ('stablecoin', 'wrapped', 'bridged', 'staked', 'staking token'))
    return False


def get(url):
    for attempt in range(5):
        try:
            with urlopen(url, timeout=30) as response:
                return json.load(response)
        except (OSError, ValueError):
            if attempt == 4:
                raise RuntimeError('Public universe API unavailable after retries; no list invented') from None
            time.sleep(2 ** attempt)


def active_pairs(payload):
    return {s['baseAsset']: s['symbol'] for s in payload['symbols']
            if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
            and s.get('isSpotTradingAllowed', False)}


def eligible(rows):
    # Count actual distinct daily candles before the frozen cutoff, not listing age.
    return len({r[0] for r in rows if r[0] < END and r[6] < END}) >= 400


def rank_market(coins, active, histories):
    ranked = sorted(coins, key=lambda c: (c.get('market_cap_rank') or 10**9, c['id']))
    return list(dict.fromkeys(c['symbol'].upper() + '/USDT' for c in ranked
            if not excluded(c['symbol'], c) and c['symbol'].upper() in active
            and eligible(histories.get(c['symbol'].upper(), []))))[:10]


def rank_volume(active, histories):
    ranked = []
    expected = list(range(END - 30 * DAY, END, DAY))
    for base in active:
        rows = histories.get(base, [])
        if excluded(base) or not eligible(rows):
            continue
        window = sorted((r for r in rows if END - 30 * DAY <= r[0] < END and r[6] < END), key=lambda r: r[0])
        if [r[0] for r in window] != expected:
            raise ValueError(f'{base}: incomplete 30 closed UTC days; snapshot stopped')
        ranked.append((base + '/USDT', sum(float(r[7]) for r in window)))
    return sorted(ranked, key=lambda r: (-r[1], r[0]))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def freeze_updates(before):
    from scripts.freeze_check import TRANSITION_FILES, hashes
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    current = hashes(ROOT)
    for name in TRANSITION_FILES:
        frozen['sha256'][name] = current[name]
    write(ROOT / 'frozen.json', frozen)
    receipt = os.environ.get('FREEZE_TRANSITION')
    if receipt:
        write(Path(receipt), {'before': before, 'after': frozen['sha256']})


def save_config(track, pairs, slots):
    if track not in ('r7', 'r8'):
        raise ValueError('R6 is frozen; rebuilding it is forbidden')
    config = copy.deepcopy(json.loads((ROOT / 'user_data/config_r5.json').read_text()))
    config['exchange']['pair_whitelist'] = pairs
    config['max_open_trades'] = config['r5']['position_cap_slots'] = slots
    write(ROOT / f'user_data/config_{track}.json', config)


def fetch_listings(pairs, active):
    listings = json.loads((ROOT / 'listing_dates.json').read_text())
    for pair in pairs:
        base = pair.split('/')[0]
        if pair not in listings:
            first = get(HOST + 'klines?' + urlencode({'symbol': active[base],
                'interval': '1d', 'startTime': 0, 'limit': 1}))
            listings[pair] = datetime.fromtimestamp(first[0][0]/1000, UTC).isoformat()
    return listings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=('r7', 'r6'), default='r7')
    args = parser.parse_args(argv)
    if args.only != 'r7':
        raise SystemExit('R6 is frozen; rebuilding it is forbidden')
    from scripts.freeze_check import check
    check(ROOT)
    if json.loads((ROOT / 'universes/r7.json').read_text()).get('status') != 'pending':
        raise SystemExit('Snapshot already frozen; refusing replacement')
    now = datetime.now(UTC)
    if now.timestamp() * 1000 < END:
        raise SystemExit('R7/R8 require 2026-10-26 UTC close')
    stamp = now.isoformat()
    before = json.loads((ROOT / 'frozen.json').read_text())['sha256']
    exchange = get(HOST + 'exchangeInfo')
    active = active_pairs(exchange)
    server = get(HOST + 'time')['serverTime']
    if server < END:
        raise RuntimeError('Binance has not closed the registered volume window')
    candidates = {b: s for b, s in active.items() if not excluded(b)}
    def history(item):
        base, symbol = item
        rows = get(HOST + 'klines?' + urlencode({'symbol': symbol, 'interval': '1d',
                   'endTime': min(END, server // DAY * DAY) - 1, 'limit': 1000}))
        return base, rows
    with ThreadPoolExecutor(max_workers=6) as pool:
        histories = dict(pool.map(history, candidates.items()))
    derived = [{'pair': base + '/USDT', 'daily_candles': len(rows),
        'history_eligible': eligible(rows),
        'window_closed_candles': sum(END-30*DAY <= r[0] < END for r in rows)}
        for base, rows in histories.items()]
    volumes = rank_volume(candidates, histories)
    r7 = [p for p, _ in volumes[:70]]
    if len(r7) != 70:
        raise SystemExit('Insufficient R7 eligible pairs; freeze unchanged')
    listings = fetch_listings(r7, active)
    write(ROOT / 'universes/r7.json', {'status': 'ready', 'snapshot_utc': stamp,
        'source': HOST, 'window_start_inclusive': '2026-09-27', 'window_end_exclusive': '2026-10-27', 'pairs': r7,
        'volume_ranking': [{'pair': p, 'quote_volume_30d': v} for p, v in volumes],
        'candidates': derived})
    write(ROOT / 'universes/r8.json', {'status': 'ready', 'universe_ref': 'r7.json', 'slots': 10})
    save_config('r7', r7, 5)
    save_config('r8', r7, 10)
    write(ROOT / 'listing_dates.json', listings)
    freeze_updates(before)
    print('R7:', ', '.join(r7))


if __name__ == '__main__':
    main()
