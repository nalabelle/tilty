# -*- coding: utf-8 -*-
import threading
import time
from unittest import mock

import pytest

from tilty import cli
from tilty.exceptions import ConfigurationFileNotFoundException


@mock.patch('tilty.tilt_device')
@mock.patch('tilty.cli.sys')
def test_terminate_process(
    mock_tilt_device,
    mock_sys,
):
    flag = threading.Event()
    cli.terminate_process(mock_tilt_device, flag, None, None)
    assert mock_tilt_device.mock_calls == [
        mock.call.stop(),
        mock.call.exit()
    ]

def test_cli_config_dne():
    ctx = cli.run.make_context('test_tilty', ["--config-file", "/foo"])
    with pytest.raises(ConfigurationFileNotFoundException):
        cli.run.invoke(ctx)

def test_cli_invalid_params():
    with pytest.raises(cli.click.exceptions.NoSuchOption):
        ctx = cli.run.make_context('test_tilty', ["--foo"])

@mock.patch('tilty.cli.scan_and_emit_thread')
@mock.patch('tilty.cli.pathlib.Path.exists', return_value=True)
@mock.patch('tilty.tilt_device.blescan')
def test_cli_keep_running(
    mock_blescan,
    mock_pathlib,
    mock_thread,
):
    ctx = cli.run.make_context('test_tilty', ['--keep-running'])
    assert cli.run.invoke(ctx) is None
    mock_thread.assert_called()
    device, config, event = mock_thread.call_args[0]
    assert isinstance(device, cli.tilt_device.TiltDevice)
    assert isinstance(config, cli.configparser.ConfigParser)
    assert isinstance(event, threading.Event)
    assert event.is_set()

@mock.patch('tilty.cli.scan_and_emit_thread')
@mock.patch('tilty.cli.pathlib.Path.exists', return_value=True)
@mock.patch('tilty.tilt_device.blescan')
def test_cli_log_handler(
    mock_blescan,
    mock_pathlib,
    mock_thread,
    monkeypatch
):
    #using patch seems to make things very angry
    def file_handler(*args, **kwargs):
        assert kwargs == {'filename': '/dev/null'}
    monkeypatch.setattr(cli.logging, "FileHandler", file_handler)

    ctx = cli.run.make_context('test_tilty', [])
    cli.CONFIG.read_dict({'general': {'logfile': '/dev/null'}})
    with pytest.raises(AttributeError):
        cli.run.invoke(ctx)
    cli.CONFIG = cli.configparser.ConfigParser()


@mock.patch('tilty.cli.parse_config', return_value={})
@mock.patch('tilty.cli.pathlib.Path.exists', return_value=True)
@mock.patch('tilty.blescan.get_events', return_value=[{'uuid': 'foo', 'major': 78, 'minor': 1833}]) # noqa
@mock.patch('tilty.tilt_device.blescan')
def test_cli_no_params_no_valid_data(
    mock_blescan,
    bt_events,
    mock_pathlib,
    mock_parse_config,
    capsys
):
    ctx = cli.run.make_context('test_tilty', [])
    assert cli.run.invoke(ctx) is None
    output = capsys.readouterr().out
    assert output == 'Scanning for Tilt data...\n'

@mock.patch('tilty.cli.parse_config', return_value={})
@mock.patch('tilty.cli.pathlib.Path.exists', return_value=True)
@mock.patch('tilty.blescan.get_events', return_value=[]) # noqa
@mock.patch('tilty.blescan.hci_le_set_scan_parameters') # noqa
@mock.patch('tilty.blescan.hci_enable_le_scan') # noqa
def test_cli_no_params_no_data(
    bt_enable_scan,
    bt_set_scan,
    bt_events,
    mock_pathlib,
    mock_parse_config,
    capsys
):
    ctx = cli.run.make_context('test_tilty', [])
    assert cli.run.invoke(ctx) is None
    output = capsys.readouterr().out
    assert output == 'Scanning for Tilt data...\n'


@mock.patch('tilty.cli.parse_config', return_value={})
@mock.patch('tilty.cli.pathlib.Path.exists', return_value=True)
@mock.patch('tilty.blescan.get_events', return_value=[{'mac': '00:0a:95:9d:68:16', 'uuid': 'a495bb30c5b14b44b5121370f02d74de', 'major': 60, 'minor': 1053}]) # noqa
@mock.patch('tilty.blescan.hci_le_set_scan_parameters') # noqa
@mock.patch('tilty.blescan.hci_enable_le_scan') # noqa
def test_cli_no_params_success(
    bt_enable_scan,
    bt_set_scan,
    bt_events,
    mock_pathlib,
    mock_parse_config,
    capsys,
    caplog
):
    ctx = cli.run.make_context('test_tilty', [])
    assert cli.run.invoke(ctx) is None
    output = capsys.readouterr().out
    assert "Scanning for Tilt data...\n{'color': 'Black', 'gravity': 1.053, " \
      + "'temp': 60, 'mac': '00:0a:95:9d:68:16', 'timestamp': " in output

mock_events = [
    {
        'mac': '00:0a:95:9d:68:16',
        'uuid': 'a495bb30c5b14b44b5121370f02d74de',
        'major': 70,
        'minor': 998
    },
    {
        'mac': '00:0a:95:9d:68:17',
        'uuid': 'a495bb60c5b14b44b5121370f02d74de',
        'major': 65,
        'minor': 1090
    }
]

@mock.patch('tilty.cli.emit')
@mock.patch('tilty.tilt_device.bluez.hci_open_dev', return_value=1)
@mock.patch('tilty.blescan.get_events', return_value=mock_events)
@mock.patch('tilty.blescan.hci_le_set_scan_parameters')
@mock.patch('tilty.blescan.hci_enable_le_scan')
def test_cli_scan_and_emit(
        bt_enable_scan,
        bt_set_scan,
        mock_get_events,
        mock_hci_open_dev,
        mock_emit
):
    device = cli.tilt_device.TiltDevice()
    cli.scan_and_emit(device, [])
    mock_get_events.assert_called()
    mock_emit.assert_called()
    data = [c[1]['tilt_data'] for c in mock_emit.call_args_list]
    assert len(data) == 2
    assert data[0]['color'] == 'Black'
    assert data[0]['gravity'] == 0.998
    assert data[0]['temp'] == 70
    assert data[0]['mac'] == '00:0a:95:9d:68:16'
    assert data[0]['uuid'] == 'a495bb30c5b14b44b5121370f02d74de'

    assert data[1]['color'] == 'Blue'
    assert data[1]['gravity'] == 1.090
    assert data[1]['temp'] == 65
    assert data[1]['mac'] == '00:0a:95:9d:68:17'
    assert data[1]['uuid'] == 'a495bb60c5b14b44b5121370f02d74de'

@mock.patch('tilty.cli.parse_config', return_value={})
@mock.patch('tilty.cli.scan_and_emit')
@mock.patch('tilty.tilt_device.bluez.hci_open_dev', return_value=1)
@mock.patch('tilty.blescan.get_events', return_value=mock_events)
@mock.patch('tilty.blescan')
def test_cli_scan_and_emit_thread(
        mock_blescan,
        mock_get_events,
        mock_hci_open_dev,
        mock_emit,
        mock_parse_config
):
    device = cli.tilt_device.TiltDevice()
    config = cli.CONFIG
    event = threading.Event()
    event.set()

    config.add_section('general')
    config['general']['sleep_interval'] = "0"
    thread = threading.Thread(
        target=cli.scan_and_emit_thread,
        name='tilty_daemon',
        args=(device, config, event)
    )
    start_time = time.time()
    end_time = start_time + 1

    # we need to guarantee that we wait long enough to test the loop, but
    # we should also timeout so the tests don't infinitely loop in a bad case
    thread.start()
    while len(mock_emit.call_args_list) < 2 and time.time() < end_time:
        cli.sleep(1)
    event.clear()
    thread.join()

    assert len(mock_emit.call_args_list) >= 2
