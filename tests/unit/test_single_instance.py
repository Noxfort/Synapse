# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: tests/unit/test_single_instance.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer

from src.utils.single_instance import SingleInstanceGuard



@pytest.fixture(scope="module")
def qapp():
    """Ensure a single QApplication instance exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_single_instance_primary_acquisition(qapp):
    """Test that the first instance acquires the single instance lock."""
    guard = SingleInstanceGuard(app_key="test_synapse_primary_acq")
    try:
        acquired = guard.try_acquire()
        assert acquired is True
        assert guard.is_primary is True
    finally:
        guard.cleanup()
        assert guard.is_primary is False


def test_single_instance_blocks_secondary_and_notifies(qapp):
    """
    Test that a second instance is blocked when a primary instance is running,
    and the primary instance receives the activation notification signal via IPC.
    """
    import subprocess
    import sys
    import time

    app_key = "test_synapse_secondary_block"
    guard1 = SingleInstanceGuard(app_key=app_key)
    
    received_messages = []
    guard1.activation_requested.connect(lambda msg: received_messages.append(msg))
    
    try:
        # Primary acquires lock
        acquired1 = guard1.try_acquire()
        assert acquired1 is True
        assert guard1.is_primary is True

        # Secondary attempts to acquire lock in separate process
        secondary_code = f"""
import sys
from PyQt6.QtWidgets import QApplication
from src.utils.single_instance import SingleInstanceGuard

app = QApplication([])
guard = SingleInstanceGuard(app_key='{app_key}')
acquired = guard.try_acquire(message='FOCUS_NOW')
sys.exit(0 if not acquired else 1)
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", secondary_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        start_time = time.time()
        while time.time() - start_time < 3:
            qapp.processEvents()
            if received_messages:
                break
            time.sleep(0.05)

        proc.wait(timeout=3)
        assert proc.returncode == 0

        # Verify signal was emitted on primary
        assert len(received_messages) >= 1
        assert "FOCUS_NOW" in received_messages[0]

    finally:
        guard1.cleanup()



def test_single_instance_stale_socket_recovery(qapp):
    """
    Test that if a previous crash left a server name registered,
    a fresh SingleInstanceGuard can clean up and acquire the lock.
    """
    app_key = "test_synapse_stale_recovery"
    guard1 = SingleInstanceGuard(app_key=app_key)
    
    # Acquire and then force close without removing server to simulate abnormal teardown
    guard1.try_acquire()
    if guard1.server:
        guard1.server.close()
        # Deliberately don't call QLocalServer.removeServer
        guard1.server = None

    # Now create a new guard
    guard2 = SingleInstanceGuard(app_key=app_key)
    try:
        acquired = guard2.try_acquire()
        assert acquired is True
        assert guard2.is_primary is True
    finally:
        guard2.cleanup()

