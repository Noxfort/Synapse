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
# File: tests/unit/test_process_utils.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
from unittest.mock import patch, MagicMock
from src.utils.process_utils import hard_kill

def test_hard_kill_executes_os_exit():
    """Test that hard_kill calls psutil kill on children and os._exit."""
    with patch("os._exit") as mock_exit, patch("psutil.Process") as mock_psutil_proc, patch("os.killpg") as mock_killpg:
        mock_child = MagicMock()
        mock_psutil_proc.return_value.children.return_value = [mock_child]
        
        hard_kill(exit_code=0)
        
        mock_child.kill.assert_called_once()
        mock_exit.assert_called_once_with(0)
