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
