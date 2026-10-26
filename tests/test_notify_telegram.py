import io
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest

from scripts import notify_telegram as telegram

BOT_ENV = 'TELEGRAM_BOT_' + 'TOKEN'
CHAT_ENV = 'TELEGRAM_' + 'CHAT_ID'


def test_message(reports):
    message = telegram.build_message(reports)
    assert 'R1: +0,0%' in message
    assert 'R5: +0,0%' in message
    assert 'B&H (R5): —' in message
    assert 'Başlamadı' in message
    assert 'Açık pozisyon: R1 0 / R5 0' in message
    assert 'https://trade.blacktowhitestudio.com' in message
    assert len(message) < 1000


def test_failure_message_does_not_need_reports(tmp_path):
    message = telegram.build_message(tmp_path, failed=True, run_url='https://example.org/run/1')
    assert 'başarısız' in message
    assert 'https://example.org/run/1' in message


@pytest.mark.parametrize('env', [{}, {CHAT_ENV: 'example'},
                                {BOT_ENV: 'example'}])
def test_missing_environment_skips_silently(monkeypatch, capsys, tmp_path, env):
    def forbidden(*args, **kwargs):
        pytest.fail('Network must not be used')
    monkeypatch.setattr(telegram, 'urlopen', forbidden)
    assert telegram.notify(tmp_path, env=env) is False
    assert capsys.readouterr() == ('', '')


def test_delivery_is_mocked(monkeypatch, reports):
    sent = []
    def fake_open(request, timeout):
        sent.append(request)
        assert timeout == 20
        return io.BytesIO(b'{"ok": true}')
    monkeypatch.setattr(telegram, 'urlopen', fake_open)
    assert telegram.notify(reports, env={BOT_ENV: 'example', CHAT_ENV: '42'})
    assert sent[0].method == 'POST'
    form = parse_qs(sent[0].data.decode())
    assert form['chat_id'] == ['42']
    assert 'R1: +0,0%' in form['text'][0]


def test_errors_hide_url_and_credentials(monkeypatch, reports):
    def failing(*args, **kwargs):
        raise URLError('sensitive request URL')
    monkeypatch.setattr(telegram, 'urlopen', failing)
    with pytest.raises(RuntimeError) as error:
        telegram.notify(reports, env={BOT_ENV: 'example', CHAT_ENV: '42'})
    assert 'sensitive' not in str(error.value)
    assert error.value.__suppress_context__
