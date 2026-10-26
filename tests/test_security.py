import json
from pathlib import Path

import pytest

from scripts.freqtrade_public import check_url
from scripts.run_forward import runtime_config
from scripts.secret_scan import inspect_file

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('text', [
    'AK' + 'IA' + 'A'*16,
    'gh' + 'p_' + 'a'*36,
    '-----BEGIN ' + 'PRIVATE KEY-----',
    '"secret": "' + 'not-empty' + '"',
    'api_' + 'key' + ' = ' + chr(34) + 'abc123' + chr(34),
    '123456789:' + 'a'*35,
])
def test_secret_positive(tmp_path, text):
    path = tmp_path / 'config.txt'
    path.write_text(text)
    assert inspect_file(path)


def test_secret_negative_and_env(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text('{"key":"", "secret":"", "token":"", "chat_id":""}')
    assert not inspect_file(path)
    for name in ['.env', '.env.example', '.env.local']:
        env = tmp_path / name
        env.write_text('')
        assert inspect_file(env)


@pytest.mark.parametrize('track,count,slots', [('r1', 3, 3), ('r5', 33, 5)])
def test_configs_safe(track, count, slots, tmp_path):
    config = json.loads((ROOT / f'user_data/config_{track}.json').read_text())
    assert config['dry_run'] is True
    assert config['exchange']['key'] == config['exchange']['secret'] == ''
    assert config['api_server']['enabled'] is False
    assert config['telegram']['enabled'] is False
    assert len(config['exchange']['pair_whitelist']) == count
    assert config['max_open_trades'] == slots
    for kind in ['ccxt_config', 'ccxt_async_config']:
        ccxt = config['exchange'][kind]
        assert ccxt['urls']['api']['public'] == 'https://data-api.binance.vision/api/v3'
        assert ccxt['options']['fetchMarkets']['types'] == ['spot']
    runtime = json.loads(runtime_config(config, tmp_path / 'runtime.json').read_text())
    assert 'api_server' not in runtime
    assert not any(s in json.dumps(runtime) for s in ['jwt_secret_key', 'password', 'username'])


def test_network_guard():
    check_url('https://data-api.binance.vision/api/v3/exchangeInfo')
    with pytest.raises(RuntimeError):
        check_url('https://api.binance.com/api/v3/exchangeInfo')
    with pytest.raises(RuntimeError):
        check_url('https://data-api.binance.vision.attacker.test/api/v3/klines')
