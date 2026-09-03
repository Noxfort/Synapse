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
# File: tests/unit/test_security_monitor.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
from src.engine.security_monitor import SecurityMonitor


def test_security_monitor_default_threshold():
    monitor = SecurityMonitor(threshold=0.75)
    
    # Below threshold -> No alert
    assert monitor.evaluate(0.50) is None
    assert monitor.evaluate(0.74) is None
    
    # Above threshold -> Alert
    alert = monitor.evaluate(0.80)
    assert alert is not None
    assert alert["title"] == "Integrity Violation"
    assert alert["payload"]["status"] == "ATTACK"
    assert alert["payload"]["loss"] == 0.80
    assert alert["payload"]["threshold"] == 0.75


def test_security_monitor_dynamic_threshold():
    monitor = SecurityMonitor(threshold=0.50)
    
    # Dynamic threshold overrides default threshold
    assert monitor.evaluate(0.60, threshold=0.75) is None
    
    alert = monitor.evaluate(0.80, threshold=0.75)
    assert alert is not None
    assert alert["payload"]["loss"] == 0.80
    assert alert["payload"]["threshold"] == 0.75
