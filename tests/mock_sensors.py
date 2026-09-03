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
# File: tests/mock_sensors.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import sys
import os
import time

# Permite importar do diretório raiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.factories.controller_factory import ControllerFactory

def run_stress_test(num_sensors):
    app = QApplication(sys.argv)
    app.setApplicationName("SYNAPSE_STRESS")
    
    print(f"\n[Stress Test] Inicializando MainController via ControllerFactory...")
    controller = ControllerFactory.create_main_controller()
    
    print(f"[Stress Test] Registrando {num_sensors} sensores mock na pipeline (SourceType: API)...")
    for i in range(num_sensors):
        # Registra sensores mock para que a engine, ingestores e otimizadores atuem sobre eles
        controller.project.add_data_source(f"Sensor_Mock_{i}", "API", f"mock://sensor_{i}")
        
    print("[Stress Test] Disparando start_online_operation()...")
    # Isso inicia todas as funções: Ingestores, Motores de Inferência e Threads
    controller.system.start_online_operation()
    
    print("[Stress Test] Pipeline completamente engajada. Event loop ativo.")
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        num_sensors = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    except ValueError:
        num_sensors = 10
        
    run_stress_test(num_sensors)
