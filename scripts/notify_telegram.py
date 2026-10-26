"""Optional Telegram delivery; credentials enter only through the process environment."""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from datetime import UTC

from scripts.build_site import load_reports, number, percent
from scripts.freeze_check import MESSAGE
from scripts.health import run_counts

SITE_URL = 'https://trade.blacktowhitestudio.com'


def build_message(results=ROOT / 'results', failed=False, run_url=''):
    snapshot_warning = ('Uyarı: R7/R8 evren snapshot alınamadı; sonraki gece yeniden denenecek.'
                        if os.environ.get('SNAPSHOT_RESULT') == 'failure' else '')
    if failed:
        freeze = os.environ.get('FREEZE_RESULT') == 'failure'
        health_path = results / 'health.json'
        if health_path.exists():
            runs = json.loads(health_path.read_text()).get('runs', [])
            freeze = freeze or bool(runs and runs[-1].get('reason') == 'freeze')
        return ('Trade Lab: çalışma başarısız. ' + (MESSAGE if freeze else
                'Uyarı: çalışma tamamlanmadı; veri/sağlık kontrolü gerekli.')
                + (f'\n{snapshot_warning}' if snapshot_warning else '')
                + f'\nAyrıntılar: {run_url}\n{SITE_URL}')
    reports = load_reports(results)
    pending = all(s['status'] == 'not_started' for s, _ in reports.values())
    lines = ['Trade Lab · ' + ('Başlamadı' if pending else 'Günlük sanal test')]
    for track, (summary, _) in reports.items():
        name = track.upper()
        lines.append(f'{name}: {percent(summary["profit_pct"])} net · '
                     f'B&H ({name}): {percent(summary.get("buy_hold_profit_pct"))} · '
                     f'Komisyon: {number(summary.get("total_fees_usdt", 0), digits=2)} USDT')
        if summary.get('universe_pending'):
            lines.append(f'{name}: evren snapshot bekleniyor')
    if snapshot_warning:
        lines.append(snapshot_warning)
    lines.append('Açık pozisyon: ' + ' / '.join(
        f'{t.upper()} {len(s["open_positions"])}' for t, (s, _) in reports.items()))
    path = results / 'health.json'
    from datetime import datetime
    ledger = json.loads(path.read_text()) if path.exists() else {'runs': []}
    counts = run_counts(ledger, datetime.now(UTC).isoformat())
    last = ledger['runs'][-1] if ledger['runs'] else None
    if counts['missing'] or not last or not last['success'] or not last['data_freshness'] or last['pairs_missing']:
        lines.append('Uyarı: sistem sağlığı / veri tazeliği / eksik çalışma kontrolü gerekli.')
    return '\n'.join(lines + [SITE_URL, 'Sanal işlem; yatırım tavsiyesi değildir.'])



def notify(results=ROOT / 'results', failed=False, run_url='', env=None):
    env = os.environ if env is None else env
    bot = env.get('TELEGRAM_BOT_TOKEN', '')
    chat = env.get('TELEGRAM_CHAT_ID', '')
    if not bot or not chat:
        return False
    message = build_message(results, failed, run_url)
    payload = urlencode({'chat_id': chat, 'text': message,
                         'disable_web_page_preview': 'true'}).encode()
    request = Request(f'https://api.telegram.org/bot{bot}/sendMessage',
                      data=payload, method='POST')
    # Never log request URLs, response bodies or exception details: they may contain credentials.
    try:
        with urlopen(request, timeout=20) as response:
            if not json.load(response).get('ok'):
                raise ValueError('Telegram rejected delivery')
    except (HTTPError, URLError, OSError, ValueError):
        raise RuntimeError('Telegram bildirimi gönderilemedi.') from None
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--failed', action='store_true')
    args = parser.parse_args()
    try:
        notify(failed=args.failed, run_url=os.environ.get('RUN_URL', ''))
    except Exception:  # noqa: BLE001 — redact all errors at the credential boundary
        # A traceback can expose a bot token through urllib's request URL.
        print('Telegram bildirimi hazırlanamadı veya gönderilemedi.', file=sys.stderr)
        raise SystemExit(1) from None
