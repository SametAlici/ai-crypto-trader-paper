import pandas as pd

from scripts.health import data_health


def _frame(dates):
    return pd.DataFrame({'date': dates, 'open': 1.0, 'high': 1.0, 'low': 1.0,
                         'close': 1.0, 'volume': 1.0})


def test_naive_and_aware_dates_both_supported():
    naive = pd.date_range('2026-10-27', '2026-10-29', freq='D')
    aware = naive.tz_localize('UTC')
    for dates, today in ((naive, '2026-10-30'), (aware, pd.Timestamp('2026-10-30', tz='UTC'))):
        out = data_health({'BTC/USDT': _frame(dates)}, ['BTC/USDT'], today)
        assert out['pairs_ok'] == ['BTC/USDT']
