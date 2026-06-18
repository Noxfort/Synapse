import sys
import os
import time

# Permite importar do diretório raiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.main_controller import MainController

def run_stress_test(num_sensors):
    app = QApplication(sys.argv)
    app.setApplicationName("SYNAPSE_STRESS")
    
    print(f"\n[Stress Test] Inicializando MainController...")
    controller = MainController()
    
    print(f"[Stress Test] Registrando {num_sensors} sensores mock na pipeline (SourceType: API)...")
    for i in range(num_sensors):
        # Registra sensores mock para que a engine, ingestores e otimizadores atuem sobre eles
        controller.project_ctrl.add_data_source(f"Sensor_Mock_{i}", "API", f"mock://sensor_{i}")
        
    print("[Stress Test] Disparando start_online_operation()...")
    # Isso inicia todas as funções: Ingestores, Motores de Inferência e Threads
    controller.start_online_operation()
    
    print("[Stress Test] Pipeline completamente engajada. Event loop ativo.")
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        num_sensors = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    except ValueError:
        num_sensors = 10
        
    run_stress_test(num_sensors)
