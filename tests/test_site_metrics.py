"""Execute the exact browser calculations using synthetic reports, without browser/network."""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def metrics(report, days, field='equity'):
    command = "const m=require('./scripts/site_metrics.js');const r=JSON.parse(process.argv[1]);console.log(JSON.stringify({period:m.period(r," + str(days) + ", '" + field + "'),months:m.months(r.curve)}));"
    return json.loads(subprocess.check_output(['node', '-e', command, json.dumps(report)],
                                              cwd=ROOT))


def synthetic():
    return {'curve': [
        {'date': '2026-10-27T00:00:00Z', 'equity': 1000, 'buy_hold_equity': 1000},
        {'date': '2026-10-28T00:00:00Z', 'equity': 1200, 'buy_hold_equity': 1100},
        {'date': '2026-10-29T00:00:00Z', 'equity': 1100, 'buy_hold_equity': 990}],
        'summary': {'closed_trades': [{'trade_id': 0, 'exit_date': '2026-10-28T00:00:00Z',
                                      'profit_usdt': 100}],
                    'daily_returns': [
                        {'fees_cumulative': 1, 'per_coin_cumulative': {'BTC': 200},
                         'per_trade_cumulative': {'0': 200}},
                        {'fees_cumulative': 3, 'per_coin_cumulative': {'BTC': 100},
                         'per_trade_cumulative': {'0': 100}}]}}


def test_period_rebases_and_counts_carry_in_contribution():
    p = metrics(synthetic(), 1)['period']
    assert p['ret'] == pytest.approx(-100 / 1200 * 100)
    assert p['drawdown'] == pytest.approx(100 / 1200 * 100)
    assert p['fees'] == 2
    assert p['coin'] == {'BTC': -100}
    assert len(p['closed']) == 1
    assert p['without'] == 0
    assert p['win'] == 100  # whole trade won, though this period's contribution is negative
    assert p['share'] is None
    assert p['calmar'] is None


def test_all_fallback_monthly_compounding_and_benchmark():
    p = metrics(synthetic(), 30)
    assert p['period']['insufficient']
    assert p['period']['available'] == 2
    assert p['period']['ret'] == pytest.approx(10)
    assert p['period']['share'] == 100
    assert p['months']['2026-10'] == pytest.approx(10)
    bh = metrics(synthetic(), 0, 'buy_hold_equity')['period']
    assert bh['ret'] == pytest.approx(-1)
    assert bh['drawdown'] == pytest.approx(10)


def test_calmar_threshold_and_empty_history():
    from datetime import UTC, datetime, timedelta
    r = synthetic()
    r['curve'] = [{'date': (datetime(2026, 1, 1, tzinfo=UTC)+timedelta(days=i)).isoformat(),
                   'equity': 1000+i, 'buy_hold_equity': 1000} for i in range(31)]
    r['curve'][10]['equity'] = 900
    p = metrics(r, 0)['period']
    assert p['calmar'] == pytest.approx(((1.03)**(365/30)-1)/(p['drawdown']/100))
    r['curve'] = r['curve'][:1]
    p = metrics(r, 365)['period']
    assert p['ret'] == 0
    assert p['days'] == 0
    assert p['insufficient']
    assert p['win'] is None


def test_health_counts_refresh_even_without_site_rebuild():
    code = """
    const m=require('./scripts/site_metrics.js');
    console.log(JSON.stringify([
      m.healthCounts(['2026-10-28','2026-10-28'],'2026-10-28T00:19:00Z','2026-10-27'),
      m.healthCounts(['2026-10-28','2026-10-28'],'2026-10-30T00:20:00Z','2026-10-27')
    ]));
    """
    before, later = json.loads(subprocess.check_output(['node', '-e', code], cwd=ROOT))
    assert before == {'expected': 0, 'actual': 0, 'missing': 0}
    assert later == {'expected': 3, 'actual': 1, 'missing': 2}


def overview(report, days=0, source='forward'):
    code = "const m=require('./scripts/site_metrics.js');console.log(JSON.stringify(m.overview(JSON.parse(process.argv[1]),Number(process.argv[2]),process.argv[3])));"
    return json.loads(subprocess.check_output(
        ['node', '-e', code, json.dumps(report), str(days), source], cwd=ROOT))


@pytest.mark.parametrize('days,net,base,available,short', [
    (1, -100, 1200, 2, False), (7, 100, 1000, 2, True),
    (30, 100, 1000, 2, True), (0, 100, 1000, 2, False)])
def test_overview_period_math_short_history(days, net, base, available, short):
    result = overview(synthetic(), days)
    assert result['state'] == 'ready'
    assert result['start'] == base
    assert result['end'] == 1100
    assert result['net'] == net
    assert result['ret'] == pytest.approx(net / base * 100)
    assert result['available'] == available
    assert result['insufficient'] is short


def test_overview_week_and_month_use_period_start_not_initial_balance():
    from datetime import UTC, datetime, timedelta
    r = synthetic()
    r['curve'] = [{'date': (datetime(2026, 1, 1, tzinfo=UTC)+timedelta(days=i)).isoformat(),
                   'equity': 1000+i*10, 'buy_hold_equity': 1000+i*5} for i in range(41)]
    for days in (1, 7, 30):
        p = overview(r, days)
        assert p['start'] == 1400-days*10
        assert p['net'] == days*10
        assert p['benchmark'] == pytest.approx((1200/(1200-days*5)-1)*100)
        assert not p['insufficient']


def test_overview_signed_formatting():
    code = "const m=require('./scripts/site_metrics.js');console.log(JSON.stringify([34,-12,0,-0.001,0.001].map(v=>m.signed(v))));"
    values = json.loads(subprocess.check_output(['node', '-e', code], cwd=ROOT))
    assert values == ['+34,0', '−12,0', '0,0', '0,0', '0,0']


def test_overview_pending_and_not_started_hide_results():
    r = synthetic()
    r['summary'].update(status='not_started', universe_pending=True)
    p = overview(r)
    assert p == {'state': 'pending', 'message': 'Coin listesi bu gece belirlenecek'}
    r['summary']['universe_pending'] = False
    p = overview(r)
    assert p['state'] == 'not_started'
    assert "Test 27 Ekim 2026'da başladı" in p['message']
    assert 'net' not in p


def test_overview_reference_availability_and_trade_position_counts():
    reports = {'r1': synthetic(), 'r5': synthetic()}
    for track in ('r1', 'r5', 'r6', 'r7', 'r8'):
        p = overview(reports.get(track), source='reference')
        assert p['state'] == ('ready' if track in reports else 'missing')
        if track not in reports:
            assert p['message'] == 'Geçmiş simülasyon yok (yeni bot)'
    r = synthetic()
    r['summary']['open_positions'] = [
        {'trade_id': 1, 'pair': 'SOL/USDT', 'entry_date': r['curve'][1]['date']},
        {'trade_id': 2, 'pair': 'BTC/USDT', 'entry_date': '2026-10-20T00:00:00Z'}]
    p = overview(r, 1)
    assert p['trades'] == 1  # Carry-in positions are not new trades.
    assert p['positions'] == ['SOL', 'BTC']
    assert p['verdict'] == 'Al-tuttan iyi'

