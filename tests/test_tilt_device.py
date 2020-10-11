# -*- coding: utf-8 -*-
from unittest import mock

from tilty import tilt_device

@mock.patch('tilty.tilt_device.bluez.hci_open_dev', return_value=1)
@mock.patch('tilty.blescan.hci_disable_le_scan')
def test_stop(
    mock_disable_le_scan,
    mock_hci_open_dev
):
    t = tilt_device.TiltDevice()
    t.stop()
    mock_hci_open_dev.assert_called()
    mock_disable_le_scan.assert_called_with(t.sock)

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

@mock.patch('tilty.tilt_device.bluez.hci_open_dev', return_value=1)
@mock.patch('tilty.blescan.get_events', return_value=mock_events)
def test_scan_for_tilt_data(
    mock_get_events,
    mock_hci_open_dev
):
    t = tilt_device.TiltDevice()
    data = t.scan_for_tilt_data()

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

mock_no_uuid_event = [
    {
        'mac': '00:0a:95:9d:68:17',
        'uuid': None,
        'major': 65,
        'minor': 1090
    }
]

@mock.patch('tilty.tilt_device.bluez.hci_open_dev', return_value=1)
@mock.patch('tilty.blescan.get_events', return_value=mock_no_uuid_event)
def test_scan_for_tilt_data_no_uuid(
    mock_get_events,
    mock_hci_open_dev
):
    t = tilt_device.TiltDevice()
    data = t.scan_for_tilt_data()
    assert len(data) == 0

