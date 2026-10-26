import pandas as pd
import pytest
from freqtrade.data.history.datahandlers.featherdatahandler import FeatherDataHandler
from freqtrade.enums import CandleType

from scripts import run_forward


def test_closed_candles_roundtrip_and_missing_day(tmp_path, monkeypatch):
    monkeypatch.setattr(run_forward, 'DATA', tmp_path)
    dates = pd.date_range('2025-01-01', periods=4, tz='UTC').as_unit('ms')
    frame = pd.DataFrame({'date': dates, 'open': 100., 'high': 101.,
                          'low': 99., 'close': 100., 'volume': 10.})
    handler = FeatherDataHandler(tmp_path)
    handler.ohlcv_store('BTC/USDT', '1d', frame, CandleType.SPOT)
    result = run_forward.load_closed(['BTC/USDT'], pd.Timestamp('2025-01-04', tz='UTC'))
    assert len(result['BTC/USDT']) == 3  # open Jan 4 candle removed
    missing = result['BTC/USDT'].drop(index=1)
    handler.ohlcv_store('BTC/USDT', '1d', missing, CandleType.SPOT)
    with pytest.raises(ValueError, match='missing/stale/duplicate'):
        run_forward.load_closed(['BTC/USDT'], pd.Timestamp('2025-01-04', tz='UTC'))
