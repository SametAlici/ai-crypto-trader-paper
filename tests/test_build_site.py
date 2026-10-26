import json
from html.parser import HTMLParser

import pytest

from scripts.build_site import benchmark, build_site, load_reports, number, percent
from scripts.secret_scan import inspect_file


def activate(reports):
    for track in ('r1', 'r5', 'r6', 'r7', 'r8'):
        path = reports / track / 'summary.json'
        summary = json.loads(path.read_text())
        summary.update(status='active', profit_pct=12.3, max_drawdown_pct=5.5,
                       trades=1, updated_utc='2026-10-30T22:00:00+00:00')
        record = {'pair': '<img src=x onerror=alert(1)>',
                  'entry_date': '2026-10-27T00:00:00+00:00', 'entry_price': 100,
                  'amount': 2, 'profit_usdt': 12.3,
                  'valuation_date': '2026-10-30T00:00:00+00:00', 'valuation_price': 110,
                  'exit_date': '2026-10-29T00:00:00+00:00', 'exit_price': 120}
        summary['open_positions'] = [record]
        summary['closed_trades'] = [record]
        # Unknown input fields must never be copied to the public page.
        summary['private_note'] = 'gh' + 'p_' + 'x' * 36
        path.write_text(json.dumps(summary))
        (reports / track / 'equity.csv').write_text(
            'date,equity,buy_hold_equity\n'
            '2026-10-27T00:00:00+00:00,1000,1000\n'
            '2026-10-28T00:00:00+00:00,1200,1100\n'
            '2026-10-29T00:00:00+00:00,1123,990\n')


def test_not_started_site_and_safe_output(reports, tmp_path):
    output = tmp_path / 'site'
    path = build_site(reports, output)
    html = path.read_text()
    HTMLParser().feed(html)
    assert '<html lang="tr">' in html
    assert 'Trade Lab — İleriye Dönük Sanal Test' in html
    assert embedded(html)['views']['forward']['r1']['summary']['status'] == 'not_started'
    assert 'Henüz açık pozisyon yok.' in html
    assert 'Henüz kapanmış işlem yok.' in html
    assert 'Sanal işlem / simülasyon — yatırım tavsiyesi değildir' in html
    assert 'metrics.js' in html and 'app.js' in html
    assert 'data-days="365"' in html
    assert (output / 'CNAME').read_text() == 'trade.blacktowhitestudio.com\n'
    assert (output / 'style.css').stat().st_size < 10000
    assert all(not inspect_file(p) for p in output.iterdir())


def test_synthetic_trades_and_benchmark(reports, tmp_path):
    activate(reports)
    path = build_site(reports, tmp_path / 'site')
    html = path.read_text()
    assert 'Başlamadı' not in html
    assert embedded(html)['views']['forward']['r1']['summary']['profit_pct'] == 12.3
    assert '30.10.2026 22:00 UTC · 31.10.2026 01:00 Türkiye saati' in html
    assert 'id="closed"' in html and 'id="open"' in html
    assert '<img' not in html
    assert '\\u003cimg' in html
    assert 'private_note' not in html
    assert not inspect_file(path)
    assert benchmark(load_reports(reports))['max_drawdown_pct'] == pytest.approx(10)


def test_active_zero_trades(reports, tmp_path):
    for track in ('r1', 'r5', 'r6', 'r7', 'r8'):
        path = reports / track / 'summary.json'
        s = json.loads(path.read_text())
        s['status'] = 'active'
        path.write_text(json.dumps(s))
    html = build_site(reports, tmp_path / 'site').read_text()
    assert embedded(html)['views']['forward']['r5']['summary']['status'] == 'active'
    assert 'Henüz kapanmış işlem yok.' in html


def test_number_format():
    assert percent(12.3) == '+12,3%'
    assert percent(-2.5) == '-2,5%'
    assert percent(None) == '—'
    assert number(1234.5) == '1.234,5'
    with pytest.raises(ValueError):
        number(float('nan'))


@pytest.mark.parametrize('bad', ['nan', 'inf', '-1', '0'])
def test_invalid_curve_rejected(reports, tmp_path, bad):
    path = reports / 'r1/equity.csv'
    path.write_text(path.read_text().replace('1000', bad))
    with pytest.raises(ValueError):
        build_site(reports, tmp_path / 'site')
    assert not (tmp_path / 'site/index.html').exists()


def test_mismatched_dates_rejected(reports, tmp_path):
    path = reports / 'r1/equity.csv'
    path.write_text(path.read_text().replace('2026-10-27', '2026-10-28'))
    with pytest.raises(ValueError, match='dates'):
        build_site(reports, tmp_path / 'site')


def embedded(html):
    return json.loads(html.split('<script id="report-data" type="application/json">')[1]
                      .split('</script>')[0])


def test_both_views_and_filter_series(reports, tmp_path):
    import shutil
    activate(reports)
    for track in ('r1', 'r5'):
        directory = reports / 'reference' / track
        shutil.copytree(reports / track, directory)
    data = embedded(build_site(reports, tmp_path / 'site').read_text())
    assert set(data['views']) == {'forward', 'reference'}
    assert len(data['views']['reference']['r1']['curve']) == 3
    assert data['health']['counts']['expected'] >= 0
    html = (tmp_path / 'site/index.html').read_text()
    for label in ['Sistem sağlığı', 'Nasıl okunur?', 'Al-tut R1 evreni',
                  'Geçmiş simülasyon (referans) — ileriye dönük test değildir; bu dönem strateji geliştirmede kullanıldı']:
        assert label in html
    for days in [1, 7, 30, 90, 180, 365, 0]:
        assert f'data-days="{days}"' in html
    assert 'daily_returns' in html


def test_script_breakout_escaped(reports, tmp_path):
    activate(reports)
    path = reports / 'r1/summary.json'
    s = json.loads(path.read_text())
    s['closed_trades'][0]['pair'] = '</script><script>alert(1)</script>'
    path.write_text(json.dumps(s))
    html = build_site(reports, tmp_path / 'site').read_text()
    assert '</script><script>alert' not in html
    assert embedded(html)['views']['forward']['r1']['summary']['closed_trades'][0]['pair'].startswith('</script>')
