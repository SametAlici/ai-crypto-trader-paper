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
from scripts.build_site import benchmark, load_reports, percent

SITE_URL = 'https://trade.blacktowhitestudio.com'


def build_message(results=ROOT / 'results', failed=False, run_url=''):
    if failed:
        return f'Trade Lab: çalışma başarısız. Ayrıntılar: {run_url}'
    reports = load_reports(results)
    r1, r5 = reports['r1'][0], reports['r5'][0]
    pending = all(s['status'] == 'not_started' for s in (r1, r5))
    return ('Trade Lab · ' + ('Başlamadı' if pending else 'Günlük sanal test') + '\n'
            f'R1: {percent(r1["profit_pct"])} · R5: {percent(r5["profit_pct"])}\n'
            f'B&H (R5): {percent(benchmark(reports)["profit_pct"])}\n'
            f'Açık pozisyon: R1 {len(r1["open_positions"])} / R5 {len(r5["open_positions"])}\n'
            f'{SITE_URL}\nSanal işlem; yatırım tavsiyesi değildir.')


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
