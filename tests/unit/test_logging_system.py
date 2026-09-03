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
# File: tests/unit/test_logging_system.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import os
import sys
import logging
import pytest
from pathlib import Path
import tempfile

# Test backward compatibility imports from src.utils.logging_setup
from src.utils.logging_setup import (
    setup_logger,
    get_logger as get_logger_legacy,
    set_global_level as set_global_level_legacy,
    get_log_dir as get_log_dir_legacy,
    get_session_log_path as get_session_log_path_legacy,
    DetailedColoredFormatter as DetailedColoredFormatterLegacy,
    DetailedFileFormatter as DetailedFileFormatterLegacy,
    StreamToLogger as StreamToLoggerLegacy,
    logger as legacy_logger,
)

# Test modular package imports from src.logging submódulos
from src.logging.facade import (
    setup_logging,
    get_logger,
    set_global_level,
    get_log_dir,
    get_session_log_path,
)
from src.logging.config import LogConfig
from src.logging.formatters import DetailedColoredFormatter, DetailedFileFormatter
from src.logging.interceptors import StreamToLogger
from src.logging.handlers import create_console_handler, create_rotating_file_handler


def test_get_logger_hierarchy():
    """Verifies that get_logger standardizes names under Synapse."""
    log_root = get_logger()
    assert log_root.name == "Synapse"

    log_custom = get_logger("Coordinator")
    assert log_custom.name == "Synapse.Coordinator"

    log_prefixed = get_logger("Synapse.AFB")
    assert log_prefixed.name == "Synapse.AFB"

    log_src = get_logger("src.pipeline.imputer_pipeline")
    assert log_src.name == "Synapse.pipeline.imputer_pipeline"


def test_detailed_colored_formatter():
    """Verifies that DetailedColoredFormatter outputs expected components."""
    formatter = DetailedColoredFormatter(use_colors=False)
    record = logging.LogRecord(
        name="Synapse.Engine",
        level=logging.DEBUG,
        pathname="/path/to/inference_engine.py",
        lineno=123,
        msg="Inference cycle completed successfully",
        args=(),
        exc_info=None,
        func="process_cycle"
    )
    formatted = formatter.format(record)
    
    assert "DEBUG" in formatted
    assert "[Engine]" in formatted
    assert "inference_engine.py:123" in formatted
    assert "(process_cycle)" in formatted
    assert "Inference cycle completed successfully" in formatted


def test_detailed_colored_formatter_with_colors():
    """Verifies ANSI escape codes when use_colors=True."""
    formatter = DetailedColoredFormatter(use_colors=True)
    formatter.use_colors = True
    record = logging.LogRecord(
        name="Synapse.Auditor",
        level=logging.ERROR,
        pathname="auditor_agent.py",
        lineno=45,
        msg="Physics veto triggered",
        args=(),
        exc_info=None,
        func="audit_state"
    )
    formatted = formatter.format(record)
    assert "\033[" in formatted  # Contains ANSI codes
    assert "Physics veto triggered" in formatted


def test_detailed_file_formatter():
    """Verifies DetailedFileFormatter structure."""
    formatter = DetailedFileFormatter()
    record = logging.LogRecord(
        name="Synapse.AFB",
        level=logging.INFO,
        pathname="afb_engine.py",
        lineno=77,
        msg="AFB baseline updated",
        args=(),
        exc_info=None,
        func="update_baseline"
    )
    formatted = formatter.format(record)
    
    assert "INFO" in formatted
    assert "Synapse.AFB" in formatted
    assert "afb_engine.py:77" in formatted
    assert "(update_baseline)" in formatted
    assert "AFB baseline updated" in formatted


def test_set_global_level():
    """Verifies dynamic log level switching."""
    test_log = get_logger("TestModule")
    
    set_global_level("DEBUG")
    assert test_log.getEffectiveLevel() == logging.DEBUG

    set_global_level("WARNING")
    assert test_log.getEffectiveLevel() == logging.WARNING

    # Reset back to DEBUG for tests
    set_global_level("DEBUG")


def test_stream_to_logger_safe_redirection():
    """Verifies that StreamToLogger writes without recursion or crashing."""
    test_log = get_logger("StreamTest")
    stream = StreamToLogger(test_log, logging.INFO, stream_name="stdout")
    
    # Should handle single line and multiline
    stream.write("Hello from standard output\n")
    stream.write("Line 1\nLine 2\n")
    stream.flush()
    assert stream.isatty() is False


def test_session_log_file_created():
    """Verifies that session log file path is valid and exists or is createable."""
    log_dir = get_log_dir()
    assert log_dir.exists()
    
    session_file = get_session_log_path()
    if session_file:
        assert session_file.parent.exists()


def test_log_config_and_handlers_factory():
    """Verifies LogConfig customization and handler factories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "test_session.log"
        cfg = LogConfig(
            logger_name="CustomSynapse",
            console_level=logging.INFO,
            file_level=logging.WARNING,
            redirect_streams=False,
            enable_excepthook=False,
            log_dir=Path(tmpdir)
        )
        assert cfg.logger_name == "CustomSynapse"
        assert cfg.console_level == logging.INFO
        assert cfg.file_level == logging.WARNING
        assert cfg.redirect_streams is False

        console_h = create_console_handler(level=cfg.console_level)
        assert console_h.level == logging.INFO

        file_h = create_rotating_file_handler(
            file_path=temp_path,
            level=cfg.file_level
        )
        assert file_h is not None
        assert file_h.level == logging.WARNING
        file_h.close()


def test_backward_compatibility_facade():
    """Verifies that src.utils.logging_setup transparently exports all expected symbols."""
    assert DetailedColoredFormatterLegacy is DetailedColoredFormatter
    assert DetailedFileFormatterLegacy is DetailedFileFormatter
    assert StreamToLoggerLegacy is StreamToLogger
    assert legacy_logger is not None
    assert callable(setup_logger)
    assert callable(get_logger_legacy)
    assert callable(set_global_level_legacy)
    assert callable(get_log_dir_legacy)
    assert callable(get_session_log_path_legacy)
