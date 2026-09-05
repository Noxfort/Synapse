# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""
Unit Tests for Dedicated HFT Transmitter Process & AFB Fallback.
"""

import time
import asyncio
import threading
import multiprocessing
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.transmission.transmitter_process import (
    TransmitterWorker,
    start_transmitter_process,
)


@pytest.mark.asyncio
async def test_transmitter_worker_normal_flow():
    """Test transmitter receives frame via Pipe and enqueues to connector."""
    pipe_receiver, pipe_sender = multiprocessing.Pipe(duplex=False)
    emergency_flag = threading.Event()
    stop_event = threading.Event()

    mock_connector = MagicMock()
    mock_connector.enqueue_traffic_frame = AsyncMock()

    worker = TransmitterWorker(
        pipe_receiver=pipe_receiver,
        emergency_flag=emergency_flag,
        stop_event=stop_event,
        connector=mock_connector,
        poll_timeout=0.05,
    )

    # Run worker in background task
    task = asyncio.create_task(worker.run())

    # Send normal frame
    test_frame = {
        "timestamp": time.time(),
        "edges": {"E1": {"speed": 45.0, "density": 15.0}},
        "source": "synapse_core_ai"
    }
    pipe_sender.send(test_frame)

    # Allow worker loop to process
    await asyncio.sleep(0.08)

    # Verify frame was received and enqueued
    assert mock_connector.enqueue_traffic_frame.called
    calls = [call[0][0] for call in mock_connector.enqueue_traffic_frame.call_args_list]
    normal_calls = [c for c in calls if c.get("source") == "synapse_core_ai"]
    assert len(normal_calls) > 0
    assert "E1" in normal_calls[0]["edges"]

    # Shutdown
    stop_event.set()
    await task


@pytest.mark.asyncio
async def test_transmitter_worker_silence_timeout_triggers_afb():
    """Test that if Core fails to send frame within deadline, AFB is triggered automatically."""
    pipe_receiver, pipe_sender = multiprocessing.Pipe(duplex=False)
    emergency_flag = threading.Event()
    stop_event = threading.Event()

    mock_connector = MagicMock()
    mock_connector.enqueue_traffic_frame = AsyncMock()

    worker = TransmitterWorker(
        pipe_receiver=pipe_receiver,
        emergency_flag=emergency_flag,
        stop_event=stop_event,
        connector=mock_connector,
        poll_timeout=0.04,  # Fast timeout for testing
    )

    task = asyncio.create_task(worker.run())

    # Do NOT send anything on pipe -> simulate Core lagging or crashing
    await asyncio.sleep(0.09)

    # Verify that fallback frame was dispatched
    assert mock_connector.enqueue_traffic_frame.called
    sent_payload = mock_connector.enqueue_traffic_frame.call_args[0][0]
    assert sent_payload["is_fallback"] is True
    assert "AFB_TIMEOUT_FALLBACK" in sent_payload["source"]

    stop_event.set()
    await task


@pytest.mark.asyncio
async def test_transmitter_worker_emergency_flag_override():
    """Test that setting emergency flag immediately activates AFB even if pipe has data."""
    pipe_receiver, pipe_sender = multiprocessing.Pipe(duplex=False)
    emergency_flag = threading.Event()
    stop_event = threading.Event()

    mock_connector = MagicMock()
    mock_connector.enqueue_traffic_frame = AsyncMock()

    worker = TransmitterWorker(
        pipe_receiver=pipe_receiver,
        emergency_flag=emergency_flag,
        stop_event=stop_event,
        connector=mock_connector,
        poll_timeout=0.05,
    )

    # Set emergency flag (simulating FÊNIX Hot-Reset)
    emergency_flag.set()

    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.08)

    assert mock_connector.enqueue_traffic_frame.called
    sent_payload = mock_connector.enqueue_traffic_frame.call_args[0][0]
    assert sent_payload["is_fallback"] is True
    assert "AFB_FENIX_HOT_RESET" in sent_payload["source"]

    # Clear emergency flag and send normal frame -> should resume
    emergency_flag.clear()
    normal_frame = {
        "timestamp": time.time(),
        "edges": {"E2": {"speed": 50.0}},
        "source": "synapse_core_recovered"
    }
    pipe_sender.send(normal_frame)
    await asyncio.sleep(0.08)
    calls = [call[0][0] for call in mock_connector.enqueue_traffic_frame.call_args_list]
    recovered_calls = [c for c in calls if c.get("source") == "synapse_core_recovered"]
    assert len(recovered_calls) > 0

    stop_event.set()
    await task


def test_start_transmitter_process_lifecycle():
    """Test spawning dedicated OS process with start_transmitter_process."""
    proc, pipe_sender, emergency_event, stop_event = start_transmitter_process(
        endpoint="localhost:59999",  # dummy test port
        poll_timeout=0.05,
    )

    try:
        assert proc.is_alive()
        assert proc.pid is not None

        # Send test frame through Pipe to child process
        test_frame = {"test": 123}
        pipe_sender.send(test_frame)
        time.sleep(0.08)

        # Trigger emergency flag
        emergency_event.set()
        time.sleep(0.08)
        assert emergency_event.is_set()

        emergency_event.clear()
        assert not emergency_event.is_set()

    finally:
        # Graceful stop
        stop_event.set()
        pipe_sender.send({"command": "STOP"})
        proc.join(timeout=1.5)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1.0)
        assert not proc.is_alive()
