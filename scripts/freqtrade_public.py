"""Run Freqtrade with a fail-closed public network guard in both ccxt clients."""
import sys
from urllib.parse import urlsplit

import ccxt
import ccxt.async_support as async_ccxt


def check_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'data-api.binance.vision':
        raise RuntimeError(f'Blocked non-Vision endpoint: {parsed.netloc}')
    print(f'VISION request: {url}', flush=True)


def install_guard():
    sync_fetch = ccxt.Exchange.fetch
    async_fetch = async_ccxt.Exchange.fetch

    def fetch(self, url, *args, **kwargs):
        check_url(url)
        return sync_fetch(self, url, *args, **kwargs)

    async def fetch_async(self, url, *args, **kwargs):
        check_url(url)
        return await async_fetch(self, url, *args, **kwargs)

    ccxt.Exchange.fetch = fetch
    async_ccxt.Exchange.fetch = fetch_async


if __name__ == '__main__':
    install_guard()
    from freqtrade.main import main
    main(sys.argv[1:])
