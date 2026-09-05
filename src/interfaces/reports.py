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
# File: src/interfaces/reports.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Domain Contracts & Protocols for Traffic Engineering Reports (SOLID: DIP & ISP).
"""

from typing import Dict, Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class IReportFormatter(Protocol):
    """
    Contract for serializing and formatting official report domain data into target representation.
    """

    def format(self, report_data: Dict[str, Any]) -> str:
        """Transforms structured report data dictionary into formatted textual representation."""
        ...


@runtime_checkable
class ITrafficReportService(Protocol):
    """
    Contract for synthesizing and orchestrating official municipal traffic reports.
    """

    def build_report(
        self,
        result_id: Optional[str] = None,
        municipal_config: Optional[Dict[str, Any]] = None,
        xai_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesizes structured report data and delegates to injected formatter."""
        ...
