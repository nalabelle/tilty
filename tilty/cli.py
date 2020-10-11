# -*- coding: utf-8 -*-
""" Main Click methods """

import configparser
import logging
import pathlib
import signal
import sys
import threading
import traceback
from functools import partial
from time import sleep
from typing import List

import click

from tilty import tilt_device
from tilty.exceptions import ConfigurationFileNotFoundException
from tilty.tilty import LOGGER, emit, parse_config

CONFIG = configparser.ConfigParser()


def terminate_process(
    device: tilt_device.TiltDevice,
    keep_running_flag: threading.Event,
    signal_number: int,
    frame: None
):  # noqa  # pylint: disable=unused-argument
    """ handle SIGTERM

    Args:
        device (TiltDevice): The bluetooth device to operate on.
        signal_number (int): The signal to operate on
        frame (TODO): The TODO

    """
    keep_running_flag.clear()
    device.stop()
    sys.exit()


def scan_and_emit(device: tilt_device.TiltDevice, emitters: List[dict]):
    """ Scans and emits the data via the loaded emitters.

    Args:
        device (TiltDevice): The bluetooth device to operate on.
        emitters ([dict]): The emitters to use.
    """
    LOGGER.debug('Starting device scan')
    tilt_data = device.scan_for_tilt_data()
    if tilt_data:
        LOGGER.debug('tilt data retrieved')
        LOGGER.info(tilt_data)
        emit(emitters=emitters, tilt_data=tilt_data)
    else:
        LOGGER.debug('No tilt data')


def scan_and_emit_thread(
    device: tilt_device.TiltDevice,
    config: configparser.ConfigParser,
    keep_running: threading.Event
) -> None:
    """ method that calls the needful

    Args:
        device (TiltDevice): The bluetooth device to operate on.
        config (dict): The parsed configuration
        keep_running (threading.Event): Whether or not to keep running. Default: False
    """
    emitters = parse_config(config)
    click.echo('Scanning for Tilt data...')
    scan_and_emit(device, emitters)
    while keep_running.is_set():
        LOGGER.debug('Scanning for Tilt data...')
        try:
            scan_and_emit(device, emitters)
        except Exception as exception:  # pylint: disable=broad-except
            LOGGER.error(
                "%s\n%s",
                str(exception),
                traceback.format_tb(exception.__traceback__)
            )
        sleep_time = int(CONFIG['general'].get('sleep_interval', '1'))
        LOGGER.debug('Sleeping for %s....', sleep_time)
        sleep(sleep_time)


@click.command()
@click.option(
    '--keep-running',
    '-r',
    is_flag=True,
    help="Keep running until SIGTERM",
)
@click.option(
    '--config-file',
    '-c',
    default='config.ini',
    help="configuration file path",
)
def run(
    keep_running: bool,
    config_file: str = 'config.ini',
):
    """
    main cli entrypoint

    Args:
        keep_running (bool): Whether or not to keep running. Default: False
        config_file (str): The configuration file location to load.
    """
    file = pathlib.Path(config_file)
    if not file.exists():
        raise ConfigurationFileNotFoundException()

    CONFIG.read(config_file)

    handler = logging.StreamHandler(sys.stdout)
    logging_level = 'INFO'
    try:
        logging_level = CONFIG['general'].get('logging_level', 'INFO')
        logfile = CONFIG['general'].get('logfile', None)
        if logfile:
            handler = logging.FileHandler(filename=logfile)
    except KeyError:
        pass
    LOGGER.setLevel(logging.getLevelName(logging_level))
    handler.setLevel(logging_level)
    LOGGER.addHandler(handler)

    keep_running_flag = threading.Event()
    if keep_running:
        keep_running_flag.set()

    device = tilt_device.TiltDevice()
    signal.signal(signal.SIGINT, partial(terminate_process, device, keep_running_flag))
    device.start()
    main_thread = threading.Thread(
        target=scan_and_emit_thread,
        name='tilty_daemon',
        args=(device, CONFIG, keep_running_flag)
    )
    main_thread.start()
    main_thread.join()
