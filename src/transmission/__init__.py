# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""
Transmission Subsystem — Process-isolated HFT communication gateway with CARINA.
"""

from src.transmission.transmitter_process import (
    run_transmitter_worker,
    start_transmitter_process,
)

__all__ = ["run_transmitter_worker", "start_transmitter_process"]
