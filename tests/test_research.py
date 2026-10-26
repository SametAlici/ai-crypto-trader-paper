import json
from pathlib import Path

import pytest

from scripts.build_site import build_site, load_research
from scripts.import_research import import_research


def test_research_and_five_tracks(reports,tmp_path):
    html=build_site(reports,tmp_path/'site').read_text()
    data=json.loads(html.split('<script id="report-data" type="application/json">')[1].split('</script>')[0])
    assert set(data['registry'])==set(data['views']['forward'])=={'r1','r5','r6','r7','r8'}
    assert len(data['research']['strategies'])==14
    assert len(data['research']['equity_series'])==12
    assert all(s['curve'] for s in data['research']['equity_series'])
    assert 'data-view="research"' in html
    assert 'Tarihsel simülasyon; bu veriler strateji geliştirmede kullanıldı; ileriye dönük test değildir' in html
    assert all('source' not in s for s in data['research']['evaluations'])
    assert load_research()['ai_summary']['verdict']


def test_scan_before_copy(tmp_path):
    source=tmp_path/'private';(source/'research_equity').mkdir(parents=True)
    (source/'research_equity/a.csv').write_text('date,value\n2024-01-01,100\n')
    (source/'research_snapshot.json').write_text(json.dumps({'sec'+'ret':'bad'}))
    with pytest.raises(ValueError,match='nothing copied'):
        import_research(source,tmp_path/'public')
    assert not (tmp_path/'public').exists()


def test_scan_research_before_site(tmp_path):
    (tmp_path/'research_snapshot.json').write_text(json.dumps({'sec'+'ret':'bad'}))
    with pytest.raises(ValueError,match='secret scan'):
        load_research(tmp_path)


def test_csv_import_identical():
    root=Path(__file__).resolve().parents[1]
    source=root.parent/'Trade_Bot/exports'
    # This optional local verification never requires the private repo in CI.
    if source.exists():
        for p in (root/'research').rglob('*'):
            if p.is_file():
                assert p.read_bytes()==(source/p.relative_to(root/'research')).read_bytes()
