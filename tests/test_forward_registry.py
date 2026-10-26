import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import run_forward as forward
from scripts.tracks import ROOT, TRACKS


@pytest.mark.parametrize('snapshot_failure', [False, True])
@pytest.mark.parametrize('health_ok', [True, False])
def test_five_tracks_union_benchmarks_stress_and_atomic_validation(tmp_path, monkeypatch, health_ok, snapshot_failure):
    if snapshot_failure:
        import shutil
        from datetime import UTC, datetime

        from scripts import build_universes as u
        from scripts.freeze_check import FILES, hashes

        for name in (*FILES, 'frozen.json', 'listing_dates.json'):
            dest = tmp_path / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        for track in ('r7', 'r8'):
            u.write(tmp_path / f'universes/{track}.json', {'status': 'pending'})
        u.write(tmp_path / 'frozen.json', {'sha256': hashes(tmp_path)})
        before = hashes(tmp_path)
        monkeypatch.delenv('FREEZE_BASE_REF', raising=False)
        monkeypatch.delenv('FREEZE_TRANSITION', raising=False)
        monkeypatch.setattr(u, 'ROOT', tmp_path)
        class ClosedWindow(datetime):
            @classmethod
            def now(cls, tz=UTC):
                return cls(2026, 10, 27, tzinfo=tz)
        monkeypatch.setattr(u, 'datetime', ClosedWindow)
        def offline(url):
            raise RuntimeError('API unavailable')
        monkeypatch.setattr(u, 'get', offline)
        with pytest.raises(RuntimeError, match='API unavailable'):
            u.main(['--only', 'r7'])
        assert hashes(tmp_path) == before
    configurations={t:json.loads((ROOT/f'user_data/config_{t}.json').read_text()) for t in TRACKS}
    for i,c in enumerate(configurations.values()):
        c['exchange']['pair_whitelist']=[f'COIN{i}/USDT']
    expected=[f'COIN{i}/USDT' for i in range(5)]
    (tmp_path/'user_data').mkdir(exist_ok=True)
    (tmp_path/'user_data/config_r5.json').write_text(json.dumps(configurations['r5']))
    (tmp_path/'listing_dates.json').write_text('{}')
    candles={p:pd.DataFrame({'date':pd.date_range('2026-10-20',periods=6,tz='UTC'),
                'open':[100]*6,'high':[200]*6,'low':[90]*6,
                'close':[100+i*10]*6,'volume':[1]*6}) for i,p in enumerate(expected)}
    if snapshot_failure:
        expected = expected[:3]
        for track, config in configurations.items():
            if track in ('r7', 'r8'):
                config['exchange']['pair_whitelist'] = []
            (tmp_path / f'user_data/config_{track}.json').write_text(json.dumps(config))
    downloads=[];calls=[];checked=[]
    monkeypatch.setattr(forward,'ROOT',tmp_path)
    monkeypatch.setattr(forward,'START_DATE','2026-10-20')
    monkeypatch.setattr(forward,'track_configs',lambda:copy.deepcopy(configurations))
    if snapshot_failure:
        def pending_configs():
            raise ValueError('snapshot pending')
        monkeypatch.setattr(forward, 'track_configs', pending_configs)
    monkeypatch.setattr(forward,'freeze_check',lambda:None)
    monkeypatch.setattr(forward.subprocess,'run',lambda *a,**k:None)
    def download(args):
        downloads.append(json.loads(Path(args[args.index('-c')+1]).read_text()))
    monkeypatch.setattr(forward,'run_freqtrade',download)
    monkeypatch.setattr(forward,'load_closed',lambda pairs,*a,**k:{p:candles[p] for p in pairs})
    def health(c,pairs,*a,**k):
        checked.append(pairs[:])
        return {'pairs_missing':[] if health_ok else [expected[-1]]}
    monkeypatch.setattr(forward,'data_health',health)
    def engine(config,strategy,start,output,end='',fee=0.0015):
        calls.append((json.loads(config.read_text()),strategy,fee))
        return {'trades':[],'final_balance':1000}
    monkeypatch.setattr(forward,'backtest',engine)
    # execute changes cwd; monkeypatch restores it after the temporary directory is gone.
    monkeypatch.chdir(tmp_path)
    if not health_ok:
        with pytest.raises(ValueError,match='Data health'):
            forward.execute()
        assert not list((tmp_path/'results').glob('*/summary.json'))
        assert not calls
        return
    forward.execute()
    assert downloads[0]['exchange']['pair_whitelist']==expected
    assert checked==[expected,expected]
    if snapshot_failure:
        assert len(calls) == 3
        for track in ('r7', 'r8'):
            summary = json.loads((tmp_path / f'results/{track}/summary.json').read_text())
            assert summary['universe_pending']
        monkeypatch.setenv('SNAPSHOT_RESULT', 'failure')
        from scripts.notify_telegram import build_message
        assert 'Uyarı: R7/R8' in build_message(tmp_path / 'results')
        return
    assert len(calls)==7
    assert [s for _,s,_ in calls].count('R5_TSMomentum')==6
    assert [fee for _,_,fee in calls].count(0.0025)==2
    for i,t in enumerate(TRACKS):
        s=json.loads((tmp_path/f'results/{t}/summary.json').read_text())
        assert s['buy_hold_pairs']==[expected[i]]
        if t in ('r7','r8'):
            assert s['fee_stress']['fee_per_side']==0.0025
            curve=pd.read_csv(tmp_path/f'results/{t}/equity.csv')
            assert s['fee_stress']['curve'][-1]['buy_hold_equity']<curve.buy_hold_equity.iloc[-1]
