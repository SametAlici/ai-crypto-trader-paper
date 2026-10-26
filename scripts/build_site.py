"""Build a dependency-free public dashboard from allowlisted report fields only."""
import argparse
import csv
import json
import math
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
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


def load_reports(results):
    reports = {}
    for track in ('r1', 'r5'):
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
    if [r['date'] for r in reports['r1'][1]] != [r['date'] for r in reports['r5'][1]]:
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


def chart(reports):
    series = [('R1', 'r1', 'equity', '#65e0bf'), ('R5', 'r5', 'equity', '#a99bff'),
              ('B&H · R5 evreni', 'r5', 'buy_hold_equity', '#ffc97a')]
    curves = [[row[field] / reports[track][1][0][field] * 100
               for row in reports[track][1]] for _, track, field, _ in series]
    low = min(min(c) for c in curves)
    high = max(max(c) for c in curves)
    padding = max((high - low) * .12, 1)
    low, high = low - padding, high + padding
    svg = ['<svg viewBox="0 0 900 300" role="img" aria-labelledby="chart-title chart-desc">',
           '<title id="chart-title">R1, R5 ve al-tut net değer eğrileri</title>',
           '<desc id="chart-desc">Her eğri 100 ile başlar. Ayrıntılı değerler sonuç CSV dosyalarındadır.</desc>']
    for i in range(5):
        y = 22 + i * 59
        svg.append(f'<path d="M65 {y}H880" stroke="#293347"/>')
        svg.append(f'<text x="5" y="{y + 5}" fill="#aebbd0" font-size="13">'
                   f'{number(high - i * (high-low)/4)}</text>')
    for (_, _, _, color), values in zip(series, curves, strict=True):
        points = ' '.join(f'{65 + i * 815 / max(len(values)-1, 1):.2f},'
                          f'{22 + (high-v)/(high-low)*236:.2f}' for i, v in enumerate(values))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" '
                   'stroke-width="3" stroke-linejoin="round"/>')
        if len(values) == 1:
            svg.append(f'<circle cx="65" cy="{22+(high-values[0])/(high-low)*236:.2f}" '
                       f'r="5" fill="{color}"/>')
    dates = reports['r1'][1]
    for x, anchor, date in [(65, 'start', dates[0]['date']), (880, 'end', dates[-1]['date'])]:
        svg.append(f'<text x="{x}" y="290" text-anchor="{anchor}" fill="#aebbd0" '
                   f'font-size="13">{timestamp(date)[:10]}</text>')
    return ''.join(svg) + '</svg>'


def trade_table(reports, opened):
    field = 'open_positions' if opened else 'closed_trades'
    rows = []
    for track, (summary, _) in reports.items():
        for trade in summary[field]:
            values = [track.upper(), escape(str(trade['pair'])),
                      timestamp(trade['entry_date']), number(trade['entry_price'], digits=4),
                      number(trade['amount'], digits=6),
                      timestamp(trade['valuation_date'] if opened else trade['exit_date']),
                      number(trade['valuation_price'] if opened else trade['exit_price'], digits=4),
                      number(trade['profit_usdt'], signed=True, digits=2)]
            rows.append('<tr>' + ''.join(f'<td>{v}</td>' for v in values) + '</tr>')
    if not rows:
        return '<p class="muted">Henüz açık pozisyon yok.</p>' if opened else (
            '<p class="muted">Henüz kapanmış işlem yok.</p>')
    end = 'Değerleme' if opened else 'Çıkış'
    headers = ['İzlek', 'Parite', 'Giriş (UTC)', 'Giriş fiyatı', 'Miktar',
               f'{end} (UTC)', f'{end} fiyatı', 'Net K/Z (USDT)']
    return ('<div class="table-scroll" tabindex="0" role="region" aria-label="İşlemler">'
            '<table><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def build_site(results=ROOT / 'results', output=ROOT / 'site'):
    reports = load_reports(results)
    latest = max((s['updated_utc'] for s, _ in reports.values()),
                 key=lambda v: datetime.fromisoformat(v))
    cards = []
    for track, (summary, _) in reports.items():
        state = 'Başlamadı' if summary['status'] == 'not_started' else 'İleri dönem sürüyor'
        cards.append(f'<article class="card {track}"><h2>{track.upper()}</h2>'
                     f'<p class="muted">{state}</p><strong>{percent(summary["profit_pct"])}</strong>'
                     f'<dl><dt>En büyük düşüş</dt><dd>{number(summary["max_drawdown_pct"])}%</dd>'
                     f'<dt>Kapalı işlem</dt><dd>{summary["trades"]:d}</dd>'
                     f'<dt>Açık pozisyon</dt><dd>{len(summary["open_positions"])}</dd></dl></article>')
    bh = benchmark(reports)
    cards.append('<article class="card bh"><h2>Eşit ağırlıklı al-tut</h2>'
                 '<p class="muted">B&H · R5 evreni / 33 coin</p>'
                 f'<strong>{percent(bh["profit_pct"])}</strong><dl><dt>En büyük düşüş</dt>'
                 f'<dd>{number(bh["max_drawdown_pct"]) + "%" if bh["max_drawdown_pct"] is not None else "—"}</dd>'
                 '<dt>İşlem / açık pozisyon</dt><dd>— / —</dd></dl>'
                 '<small>Pasif sepet; motor işlem sayacı uygulanmaz.</small></article>')
    pending = all(s['status'] == 'not_started' for s, _ in reports.values())
    html = f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="description" content="R1 ve R5 ileriye dönük sanal test sonuçları">
<title>Trade Lab — İleriye Dönük Sanal Test</title><link rel="stylesheet" href="style.css"></head>
<body><main><header><p class="eyebrow">TRADE LAB / GÜNLÜK KAYIT</p>
<h1>Trade Lab — İleriye Dönük Sanal Test</h1><p>İki sabit strateji. Her gün aynı kurallar.</p>
<p class="muted">Son güncelleme: {timestamp(latest)} UTC · {timestamp(latest, 'Europe/Istanbul')} Türkiye saati</p>
<p class="notice">Sanal işlem / simülasyon — yatırım tavsiyesi değildir</p></header>
{'<section class="panel"><h2>Başlamadı</h2><p>Başlangıç: 27 Ekim 2026 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.</p></section>' if pending else ''}
<section class="cards" aria-label="Durum kartları">{''.join(cards)}</section>
<section class="panel"><h2>Net değer · başlangıç 100</h2><p class="legend"><span>● R1</span><span>● R5</span><span>● B&amp;H (R5 evreni)</span></p>
{chart(reports)}<p class="muted">Günlük noktalar; gün içi hareketleri göstermez.</p></section>
<section class="panel"><h2>Açık pozisyonlar</h2>{trade_table(reports, True)}</section>
<section class="panel"><h2>Kapanmış işlemler</h2>{trade_table(reports, False)}</section>
<section class="panel prose"><h2>Bu kayıt ne anlatıyor?</h2>
<p>R1, BTC / ETH / SOL üzerinde en fazla 3; R5, 33 coin üzerinde en fazla 5 sanal pozisyon tutar.
Her izlek 1.000 USDT ile başlar. Günlük kapanmış mumdan sinyal alınır, sonraki mum açılışında giriş yapılır.
Stratejiler sabittir; AI kullanılmaz ve gerçek emir gönderilmez.</p>
<p>Al-tut, R5 evrenindeki coinlere eşit başlangıç ağırlığı verir ve yeniden dengelemez.
R1’in kendi evrenine ait al-tut karşılaştırması sonuç JSON/CSV dosyalarında bulunur.
Her yönde %0,15 maliyet varsayılır. En büyük düşüş, günlük net değerin önceki zirveden kaybıdır.</p>
<p>Dönem sonunda motorun zorunlu çıkışları açık pozisyon değerlemesi sayılır; kapalı işlem sayısına eklenmez.
Son nokta son mum açılışıyla, önceki noktalar kapanışla değerlenir. Son gün sonucu sonraki çalışmada değişebilir.
Gerçek piyasanın emir gerçekleşmesi ve gecikmeleri modellenmez. Geçmiş sonuçlar gelecekteki getiriyi kanıtlamaz.</p>
<a href="https://github.com/SametAlici/ai-crypto-trader-paper/tree/main/results">Kaynak veriler ve yöntem ↗</a></section>
<footer>Sanal işlem / simülasyon — yatırım tavsiyesi değildir</footer></main></body></html>
'''
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / 'style.css').write_text((ROOT / 'scripts/site.css').read_text(), encoding='utf-8')
    (output / 'CNAME').write_text(DOMAIN + '\n', encoding='utf-8')
    return output / 'index.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'results')
    parser.add_argument('--output', type=Path, default=ROOT / 'site')
    args = parser.parse_args()
    build_site(args.results, args.output)
