import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from autodl_cli.app import app
from autodl_cli.config import ConfigManager
from autodl_cli.errors import AutoDLAuthError, AutoDLConfigError

runner = CliRunner()


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr('autodl_cli.config.keyring.get_password', lambda *a: None)
    monkeypatch.setattr('autodl_cli.config.keyring.delete_password', lambda *a: None)
    m = ConfigManager(data_dir=tmp_path)
    monkeypatch.setattr('autodl_cli.commands.auth.manager_from_ctx', lambda ctx: m)
    monkeypatch.setattr('autodl_cli.commands.instance.manager_from_ctx', lambda ctx: m)
    return m


def test_web_token_prompt_is_hidden_and_separate(manager):
    manager.set_token('default', 'developer-secret', store='file')
    result = runner.invoke(app, ['--json', 'auth', 'web-token', '--token-store', 'file'],
                           input='web-secret\n')
    assert result.exit_code == 0, result.output
    assert 'web-secret' not in result.output
    assert manager.get_token('default') == 'developer-secret'
    assert manager.get_token('default', web=True) == 'web-secret'
    assert manager.get_token('other', web=True) is None
    assert manager._token_path('default', web=True).stat().st_mode & 0o777 == 0o600


def test_web_token_import_profile(manager, tmp_path):
    source = tmp_path / 'input'
    source.write_text('web-secret\n')
    result = runner.invoke(app, ['-P', 'other', 'auth', 'web-token', '--token-file', str(source),
                               '--token-store', 'file'])
    assert result.exit_code == 0
    assert 'web-secret' not in result.output
    assert manager.get_token('other', web=True) == 'web-secret'
    assert manager.get_token('default', web=True) is None


@respx.mock
def test_no_gpu_uses_web_origin_token_and_payload(manager):
    manager.set_token('default', 'web-secret', store='file', web=True)
    route = respx.post('https://www.autodl.com/api/v1/instance/pro/power_on').mock(
        return_value=httpx.Response(200, json={'code': 'Success', 'data': None}))
    result = runner.invoke(app, ['--base-url', 'https://example.invalid', '--token', 'developer',
                               '--json', 'instance', 'start', 'pro-test', '--no-gpu'])
    assert result.exit_code == 0, result.exception
    assert json.loads(result.output) == {'ok': True}
    assert route.call_count == 1
    request = route.calls[0].request
    assert request.headers['Authorization'] == 'web-secret'
    assert json.loads(request.content) == {'instance_uuid': 'pro-test', 'payload': 'non_gpu'}


@respx.mock
def test_expired_web_token_no_fallback(manager):
    manager.set_token('default', 'expired', store='file', web=True)
    route = respx.post('https://www.autodl.com/api/v1/instance/pro/power_on').mock(
        return_value=httpx.Response(200, json={'code': 'AuthorizeFailed', 'msg': 'expired'}))
    result = runner.invoke(app, ['instance', 'start', 'pro-test', '--no-gpu'])
    assert isinstance(result.exception, AutoDLAuthError)
    assert 'auth web-token' in str(result.exception)
    assert route.call_count == 1
    assert len(respx.calls) == 1


@respx.mock
def test_missing_token_no_request(manager):
    result = runner.invoke(app, ['instance', 'start', 'pro-test', '--no-gpu'])
    assert isinstance(result.exception, AutoDLConfigError)
    assert not respx.calls


@pytest.mark.parametrize('options', [['--wait'], ['--start-command', 'echo hi'],
                                    ['--max-attempts', '3']])
def test_no_gpu_rejects_unsupported_options(options):
    result = runner.invoke(app, ['instance', 'start', 'pro-test', '--no-gpu', *options])
    assert result.exit_code == 2


@respx.mock
def test_default_start_still_uses_official_api():
    route = respx.post('https://api.autodl.com/api/v1/dev/instance/pro/power_on').mock(
        return_value=httpx.Response(200, json={'code': 'Success', 'data': None}))
    result = runner.invoke(app, ['--token', 'developer', 'instance', 'start', 'pro-test'])
    assert result.exit_code == 0, result.exception
    assert json.loads(route.calls[0].request.content)['payload'] == 'gpu'
    assert route.calls[0].request.headers['Authorization'] == 'developer'


@respx.mock
def test_no_gpu_name_resolution_uses_developer_token(manager):
    manager.set_token('default', 'web-secret', store='file', web=True)
    lookup = respx.post('https://api.autodl.com/api/v1/dev/instance/pro/list').mock(
        return_value=httpx.Response(200, json={'code': 'Success', 'data': {
            'list': [{'uuid': 'pro-test', 'name': 'pro-3090'}]}}))
    start = respx.post('https://www.autodl.com/api/v1/instance/pro/power_on').mock(
        return_value=httpx.Response(200, json={'code': 'Success', 'data': None}))
    result = runner.invoke(app, ['--token', 'developer', 'instance', 'start',
                               '-n', 'pro-3090', '--no-gpu'])
    assert result.exit_code == 0, result.exception
    assert lookup.calls[0].request.headers['Authorization'] == 'developer'
    assert start.calls[0].request.headers['Authorization'] == 'web-secret'
    assert json.loads(start.calls[0].request.content)['instance_uuid'] == 'pro-test'


def test_web_auto_store_fallback(manager, monkeypatch):
    def unavailable(*args):
        raise RuntimeError('keyring unavailable')
    monkeypatch.setattr('autodl_cli.config.keyring.set_password', unavailable)
    assert manager.set_token('default', 'web-secret', web=True) == 'file'
    assert manager.get_token('default', web=True) == 'web-secret'
    assert manager.get_token('default') is None


def test_web_keyring_namespace(manager, monkeypatch):
    values = {}
    monkeypatch.setattr('autodl_cli.config.keyring.set_password',
                        lambda service, profile, token: values.update({(service, profile): token}))
    monkeypatch.setattr('autodl_cli.config.keyring.get_password',
                        lambda service, profile: values.get((service, profile)))
    manager.set_token('default', 'developer', store='keyring')
    manager.set_token('default', 'web-secret', store='keyring', web=True)
    assert manager.get_token('default') == 'developer'
    assert manager.get_token('default', web=True) == 'web-secret'
