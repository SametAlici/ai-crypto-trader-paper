import io
import json

import pytest

from scripts import build_universes as u
from scripts.tracks import TRACKS, all_pairs, configs


def candles(count=430, volume=10):
    return [[u.END-(count-i)*u.DAY, '1', '1', '1', '1', '1',
             u.END-(count-i-1)*u.DAY-1, str(volume)] for i in range(count)]


@pytest.mark.parametrize('symbol', ['USDT','USDC','USDE','FDUSD','WBTC','STETH','WEETH','CBBTC','EUR','TRY','ETHUP','BTCDOWN','FOOBULL','FOOBEAR'])
def test_exclusions(symbol):
    assert u.excluded(symbol)


def test_category_and_name():
    assert u.excluded('ABC', {'categories': ['Stablecoins']})
    assert u.excluded('ABC', {'name': 'Bridged Bitcoin'})
    assert not u.excluded('BTC', {'name': 'Bitcoin'})
    assert not u.excluded('JUP', {'name': 'Jupiter'})
    assert not u.excluded('WBT', {'name': 'WhiteBIT Coin'})


def test_spot_and_history_filters():
    symbols = [{'baseAsset': s, 'symbol': s+'USDT', 'quoteAsset': 'USDT',
                'status': status, 'isSpotTradingAllowed': spot} for s,status,spot in
               [('BTC','TRADING',True),('ETH','BREAK',True),('SOL','TRADING',False)]]
    assert u.active_pairs({'symbols': symbols}) == {'BTC':'BTCUSDT'}
    assert u.eligible(candles(400))
    assert not u.eligible(candles(399))
    assert not u.eligible(candles(399)+candles(1))


def test_ordering_and_incomplete_window():
    active={s:s+'USDT' for s in ['AAA','BBB','USDC','WBTC','NEW']}
    histories={s:candles(399 if s=='NEW' else 430, 20 if s=='BBB' else 10) for s in active}
    assert [p for p,_ in u.rank_volume(active,histories)] == ['BBB/USDT','AAA/USDT']
    coins=[{'symbol':s.lower(),'id':s,'market_cap_rank':r} for s,r in [('BBB',3),('AAA',1),('USDC',2),('NEW',4)]]
    assert u.rank_market(coins,active,histories)==['AAA/USDT','BBB/USDT']
    histories['AAA']=histories['AAA'][:-1]
    with pytest.raises(ValueError,match='incomplete'):
        u.rank_volume(active,histories)


def test_backoff_and_abort(monkeypatch):
    attempts=[]
    def fail(*args, **kwargs):
        attempts.append(1)
        raise OSError('offline')
    sleeps=[]
    monkeypatch.setattr(u,'urlopen',fail)
    monkeypatch.setattr(u.time,'sleep',sleeps.append)
    with pytest.raises(RuntimeError,match='no list invented'):
        u.get(u.GECKO)
    assert len(attempts)==5 and sleeps==[1,2,4,8]
    monkeypatch.setattr(u,'urlopen',lambda *a,**k:io.BytesIO(b'[]'))
    assert u.get(u.GECKO)==[]


def test_registry_config_only_differences():
    from scripts.tracks import ROOT
    assert list(TRACKS)==['r1','r5','r6','r7','r8']
    base=json.loads((ROOT/'user_data/config_r5.json').read_text())
    for t in ('r6','r7','r8'):
        c=json.loads((ROOT/f'user_data/config_{t}.json').read_text())
        assert TRACKS[t]['strategy']=='R5_TSMomentum'
        assert c['max_open_trades']==c['r5']['position_cap_slots']==TRACKS[t]['slots']
        for d in (base,c):
            d['exchange']['pair_whitelist']=[]
            d['max_open_trades']=5
            d['r5']['position_cap_slots']=5
        assert c==base
    assert all_pairs({'a':{'exchange':{'pair_whitelist':['B','A']}},
                      'b':{'exchange':{'pair_whitelist':['A','C']}}})==['B','A','C']
    # Pending snapshots must fail closed rather than trading an invented universe.
    if any(json.loads((ROOT/f'user_data/config_{t}.json').read_text())['exchange']['pair_whitelist']==[] for t in TRACKS):
        with pytest.raises(ValueError,match='snapshot pending'):
            configs()


def test_market_fill_down_and_unique_symbols():
    names=['USDC','WBTC','NEW','OFF']+[f'C{i}' for i in range(12)]
    coins=[{'symbol':s,'id':s,'market_cap_rank':i+1} for i,s in enumerate(names)]
    active={s:s+'USDT' for s in names if s!='OFF'}
    histories={s:candles(399 if s=='NEW' else 430) for s in names}
    coins.append({'symbol':'C0','id':'duplicate','market_cap_rank':6})
    assert u.rank_market(coins,active,histories)==[f'C{i}/USDT' for i in range(10)]


def test_r6_rebuild_refused(monkeypatch):
    monkeypatch.setattr(u, 'get', lambda url: pytest.fail('R6 must never fetch data'))
    with pytest.raises(SystemExit, match='R6 is frozen'):
        u.main(['--only', 'r6'])
    with pytest.raises(ValueError, match='R6 is frozen'):
        u.save_config('r6', [], 5)


@pytest.fixture
def snapshot_root(tmp_path, monkeypatch):
    import shutil

    from scripts.freeze_check import FILES, ROOT

    for name in (*FILES, 'frozen.json', 'listing_dates.json'):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    from scripts.freeze_check import hashes
    for track in ('r7', 'r8'):
        u.write(tmp_path / f'universes/{track}.json', {'status': 'pending'})
        config = json.loads((tmp_path / f'user_data/config_{track}.json').read_text())
        config['exchange']['pair_whitelist'] = []
        u.write(tmp_path / f'user_data/config_{track}.json', config)
    u.write(tmp_path / 'frozen.json', {'sha256': hashes(tmp_path)})
    monkeypatch.setattr(u, 'ROOT', tmp_path)
    monkeypatch.delenv('FREEZE_BASE_REF', raising=False)
    monkeypatch.delenv('FREEZE_TRANSITION', raising=False)
    from datetime import UTC, datetime
    class ClosedWindow(datetime):
        @classmethod
        def now(cls, tz=UTC):
            return cls(2026, 10, 27, 0, 20, tzinfo=tz)
    monkeypatch.setattr(u, 'datetime', ClosedWindow)
    return tmp_path


def test_snapshot_updates_only_registered_hashes(snapshot_root, monkeypatch):
    from scripts.freeze_check import TRANSITION_FILES, check, hashes

    root = snapshot_root
    before = hashes(root)
    def api(url):
        if 'exchangeInfo' in url:
            return {'symbols': [{'baseAsset': f'C{i:02}', 'symbol': f'C{i:02}USDT',
                'quoteAsset': 'USDT', 'status': 'TRADING', 'isSpotTradingAllowed': True}
                for i in range(71)]}
        if url.endswith('time'):
            return {'serverTime': u.END}
        return candles()
    monkeypatch.setattr(u, 'get', api)
    u.main(['--only', 'r7'])
    after = hashes(root)
    assert {n for n in before if before[n] != after[n]} == TRANSITION_FILES
    r7 = json.loads((root / 'universes/r7.json').read_text())
    assert r7['snapshot_utc'] == '2026-10-27T00:20:00+00:00'
    assert r7['source'] == u.HOST
    expected = [f'C{i:02}/USDT' for i in range(70)]
    assert r7['pairs'] == expected
    for track in ('r7', 'r8'):
        config = json.loads((root / f'user_data/config_{track}.json').read_text())
        assert config['exchange']['pair_whitelist'] == expected
    check(root)
    with pytest.raises(SystemExit, match='already frozen'):
        u.main(['--only', 'r7'])


def test_late_api_failure_publishes_nothing(snapshot_root, monkeypatch):
    from scripts.freeze_check import hashes

    before = hashes(snapshot_root)
    listings = (snapshot_root / 'listing_dates.json').read_bytes()
    manifest = (snapshot_root / 'frozen.json').read_bytes()
    def api(url):
        if 'exchangeInfo' in url:
            return {'symbols': [{'baseAsset': f'C{i:02}', 'symbol': f'C{i:02}USDT',
                'quoteAsset': 'USDT', 'status': 'TRADING', 'isSpotTradingAllowed': True}
                for i in range(70)]}
        if url.endswith('time'):
            return {'serverTime': u.END}
        if 'startTime=0' in url:
            raise RuntimeError('listing API unavailable')
        return candles()
    monkeypatch.setattr(u, 'get', api)
    with pytest.raises(RuntimeError, match='listing API unavailable'):
        u.main(['--only', 'r7'])
    assert hashes(snapshot_root) == before
    assert (snapshot_root / 'listing_dates.json').read_bytes() == listings
    assert (snapshot_root / 'frozen.json').read_bytes() == manifest


def test_window_must_close_before_any_api_call(snapshot_root, monkeypatch):
    from datetime import UTC, datetime

    class OpenWindow(datetime):
        @classmethod
        def now(cls, tz=UTC):
            return cls(2026, 10, 26, 23, 59, 59, tzinfo=tz)
    monkeypatch.setattr(u, 'datetime', OpenWindow)
    monkeypatch.setattr(u, 'get', lambda url: pytest.fail('Window is still open'))
    with pytest.raises(SystemExit, match='UTC close'):
        u.main(['--only', 'r7'])
