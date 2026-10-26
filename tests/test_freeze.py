import json
import shutil

import pytest

from scripts.freeze_check import FILES, MESSAGE, ROOT, check


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.delenv('FREEZE_BASE_REF', raising=False)
    monkeypatch.delenv('FREEZE_TRANSITION', raising=False)
    for name in (*FILES, 'frozen.json'):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    return tmp_path


def test_current_freeze():
    check()


@pytest.mark.parametrize('name', FILES)
def test_every_frozen_file_detects_changes(frozen, name):
    path = frozen / name
    if name.endswith('.json'):
        config = json.loads(path.read_text())
        config['test_mutation'] = True
        path.write_text(json.dumps(config))
    else:
        path.write_text(path.read_text() + '\n# change\n')
    with pytest.raises(ValueError, match=MESSAGE):
        check(frozen)


def test_json_format_is_not_trading_content(frozen):
    path = frozen / 'user_data/config_r8.json'
    path.write_text(json.dumps(json.loads(path.read_text()), sort_keys=True))
    check(frozen)
    path.unlink()
    with pytest.raises(ValueError, match=MESSAGE):
        check(frozen)


def test_transition_requires_same_run_receipt_and_is_used_once(frozen, monkeypatch):
    import subprocess

    from scripts.build_universes import write
    from scripts.freeze_check import hashes

    monkeypatch.delenv('FREEZE_BASE_REF', raising=False)
    monkeypatch.delenv('FREEZE_TRANSITION', raising=False)
    for track in ('r7', 'r8'):
        write(frozen / f'universes/{track}.json', {'status': 'pending'})
    write(frozen / 'frozen.json', {'sha256': hashes(frozen)})
    subprocess.run(['git', 'init', '-q', str(frozen)], check=True)
    subprocess.run(['git', '-C', str(frozen), 'add', '.'], check=True)
    commit = ['git', '-C', str(frozen), '-c', 'user.name=Test',
              '-c', 'user.email=test@example.org', 'commit', '-qm', 'baseline']
    subprocess.run(commit, check=True)
    monkeypatch.setenv('FREEZE_BASE_REF', 'HEAD')
    receipt = frozen / 'receipt.json'
    monkeypatch.setenv('FREEZE_TRANSITION', str(receipt))
    before = hashes(frozen)
    for name in ('universes/r7.json', 'universes/r8.json',
                 'user_data/config_r7.json', 'user_data/config_r8.json'):
        data = json.loads((frozen / name).read_text())
        data['status'] = 'ready'
        write(frozen / name, data)
    after = hashes(frozen)
    write(frozen / 'frozen.json', {'sha256': after})
    with pytest.raises(ValueError, match=MESSAGE):
        check(frozen)  # Merely updating the manifest cannot authorize a transition.
    write(receipt, {'before': before, 'after': after})
    check(frozen)
    # Even refreshing the manifest cannot change the receipt's exact output.
    path = frozen / 'universes/r7.json'
    data = json.loads(path.read_text())
    data['extra'] = True
    write(path, data)
    write(frozen / 'frozen.json', {'sha256': hashes(frozen)})
    with pytest.raises(ValueError, match=MESSAGE):
        check(frozen)
    del data['extra']
    write(path, data)
    write(frozen / 'frozen.json', {'sha256': after})
    subprocess.run(['git', '-C', str(frozen), 'add', '.'], check=True)
    subprocess.run(commit, check=True)
    # A subsequent run with a ready baseline rejects even a new matching receipt.
    for name in ('universes/r7.json', 'universes/r8.json',
                 'user_data/config_r7.json', 'user_data/config_r8.json'):
        data = json.loads((frozen / name).read_text())
        data['extra'] = True
        write(frozen / name, data)
    second = hashes(frozen)
    write(frozen / 'frozen.json', {'sha256': second})
    write(receipt, {'before': after, 'after': second})
    with pytest.raises(ValueError, match=MESSAGE):
        check(frozen)
