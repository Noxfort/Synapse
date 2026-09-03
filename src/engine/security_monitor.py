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
# File: src/engine/security_monitor.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import time
from typing import Dict, Any, Optional
from src.utils.logging_setup import logger

class SecurityMonitor:
    """
    Analyzes the outputs of the Auditor Autoencoder.
    Adheres to the Single Responsibility Principle (SRP) by keeping thresholding
    and alert payload generation away from the cycle math logic.
    """
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        
    def evaluate(self, security_score: float, threshold: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluates the Security Score against defined thresholds and returns an alert payload if triggered.
        """
        active_threshold = threshold if threshold is not None else self.threshold
        if security_score > active_threshold:
            logger.warning(
                f"[Auditor] 🛡️ Security Violation / Anomaly Detected! "
                f"Score: {security_score:.4f} (Threshold: {active_threshold:.4f})"
            )
            
            return {
                "title": "Integrity Violation",
                "payload": {
                    "loss": security_score,
                    "threshold": active_threshold,
                    "status": "ATTACK",
                    "timestamp": time.time()
                }
            }
            
        return None
