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
# File: tests/unit/test_mei_fallback.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.meh.fallback_engine import FallbackEngine
from src.meh.playback_engine import PlaybackEngine

@pytest.fixture
def mock_data_loader():
    loader = MagicMock()
    loader.is_loaded = True
    loader.group_column = 'sensor_id'
    
    # Create a simple valid dataframe
    times = pd.date_range(start='2026-03-01 10:00:00', periods=5, freq='1min')
    df = pd.DataFrame({
        'timestamp': times,
        'sensor_id': ['S1'] * 5,
        'value': [10, 20, 30, 40, 50],
        'corrupted_col': ['A', 'B', 'C', 'D', 'E'] # Should be ignored by Fallback Engine
    })
    
    loader.data = df
    loader.sensor_ids = ['S1']
    loader.ontology = None
    return loader

def test_fallback_engine_builds_profiles_safely(mock_data_loader):
    """Test that FallbackEngine ignores string columns and builds profile successfully."""
    engine = FallbackEngine(mock_data_loader)
    engine.build_profiles()
    
    assert engine.is_ready is True
    assert 'S1' in engine.sensor_profiles
    assert 'S1' in engine.sensor_frequencies
    
    # Assert frequency is 60.0 seconds (1 minute diff in our mock data)
    assert engine.sensor_frequencies['S1'] == 60.0

def test_fallback_engine_empty_data_rejection():
    """Test that FallbackEngine safely rejects empty data."""
    empty_loader = MagicMock()
    empty_loader.is_loaded = True
    empty_loader.data = pd.DataFrame()
    
    engine = FallbackEngine(empty_loader)
    engine.build_profiles()
    
    assert engine.is_ready is False

def test_playback_engine_sequential_loop(mock_data_loader):
    """Test Playback Engine returns frames and rewinds correctly."""
    engine = PlaybackEngine(mock_data_loader)
    
    # Pull frames 1 to 5
    for i in range(1, 6):
        frame = engine.get_next_frame()
        expected_value = i * 10
        assert frame['value'] == expected_value
        assert 'corrupted_col' not in frame  # Should filter out strings
        
    # Frame 6 should rewind to Frame 1
    rewind_frame = engine.get_next_frame()
    assert rewind_frame['value'] == 10

def test_playback_engine_handles_underlying_data_corruption(mock_data_loader):
    """Test Playback Engine doesn't crash if rows are suddenly dropped from data."""
    engine = PlaybackEngine(mock_data_loader)
    
    # Advance to cursor 2
    engine.get_next_frame()
    engine.get_next_frame()
    
    # Suddenly data becomes shorter than cursor
    mock_data_loader.data = mock_data_loader.data.iloc[:1]
    
# Should catch IndexError and reset to 0 safely
    recovered_frame = engine.get_next_frame()
    assert recovered_frame['value'] == 10
    assert engine._playback_cursor == 0 # Advanced after reset, then rewound to 0 due to len=1

def test_fallback_level_1_exact_match(mock_data_loader):
    """Test Level 1 fallback properly finds an exact time+day match."""
    # Data is '2026-03-01 10:00:00' (Sunday = Day 6)
    # The first row value is 10
    engine = FallbackEngine(mock_data_loader)
    engine.build_profiles()
    
    # Matching target: Sunday, 10:00:00
    target = datetime(2026, 3, 1, 10, 0, 0)
    state = engine.get_fallback_state(target)
    
    assert state['value'] == 10.0 # Strict exact match

def test_fallback_level_2_broad_match():
    """Test Level 2 broad match averages data from same bin across different days."""
    loader = MagicMock()
    loader.is_loaded = True
    loader.group_column = 'sensor_id'
    
    # Create rows at 10:00:00 but on different days (Monday, Tuesday)
    times = pd.DatetimeIndex(['2026-03-02 10:00:00', '2026-03-03 10:00:00'])
    df = pd.DataFrame({
        'timestamp': times,
        'sensor_id': ['S1', 'S1'],
        'value': [40, 60]  # Values that should be averaged to 50
    })
    loader.data = df
    loader.sensor_ids = ['S1']
    loader.ontology = None
    
    engine = FallbackEngine(loader)
    engine.build_profiles()
    
    # Target: Wednesday (no exact match), but same time bin (10:00:00)
    target = datetime(2026, 3, 4, 10, 0, 0)
    state = engine.get_fallback_state(target)
    
    # Level 2 should trigger and average 40 + 60 = 50
    assert state['value'] == 50.0
