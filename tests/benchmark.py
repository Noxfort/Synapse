import os
import sys
import time
import platform
import subprocess

try:
    import psutil
except ImportError:
    print("Instalando a biblioteca 'psutil'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_gpu_info():
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            encoding='utf-8'
        )
        lines = result.strip().split('\n')
        vram_used = sum(int(line.split(',')[0].strip()) for line in lines)
        vram_total = sum(int(line.split(',')[1].strip()) for line in lines)
        return {"vram_used_mb": vram_used, "vram_total_mb": vram_total, "has_gpu": True}
    except Exception:
        return {"vram_used_mb": 0, "vram_total_mb": 0, "has_gpu": False}

def run_benchmark(num_sensors, duration=60):
    print("\n==================================================")
    print("       INICIANDO BENCHMARK SYNAPSE CORE")
    print(f"       Stress Test: {num_sensors} Sensores | Tempo: {duration}s")
    print("==================================================")
    
    os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
    
    core_script = os.path.join(os.path.dirname(__file__), "mock_sensors.py")
    if not os.path.exists(core_script):
        print(f"Erro: '{core_script}' não encontrado. Ele é necessário para executar o teste de carga no ecossistema inteiro.")
        sys.exit(1)
        
    print(f"-> Passo 1/1: Iniciando o Gateway (SYNAPSE CORE) em modo Headless Stress Test com {num_sensors} sensores...")
    
    env = os.environ.copy()
    env["SYNAPSE_TEST_MODE"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen" # Tenta rodar em background sem abrir UI física
    
    # O mock_sensors.py agora inicializa todo o MainController e chama start_online_operation()
    core_process = subprocess.Popen([sys.executable, core_script, str(num_sensors)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    peak_cpu_percent = 0.0
    peak_ram_mb = 0.0
    peak_vram_mb = 0.0
    
    start_time = time.time()
    
    try:
        core_ps = psutil.Process(core_process.pid)
        print("\nMonitorando recursos do Gateway (Ingestores, Otimizadores, Interface)...\n")
        
        while time.time() - start_time < duration:
            if core_process.poll() is not None:
                print("\nO processo do SYNAPSE_CORE terminou prematuramente.")
                break
                
            total_cpu = 0.0
            total_ram = 0
            
            children = core_ps.children(recursive=True)
            for p in [core_ps] + children:
                try:
                    total_cpu += p.cpu_percent(interval=None)
                    total_ram += p.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            
            if total_cpu > peak_cpu_percent:
                peak_cpu_percent = total_cpu
                
            ram_mb = total_ram / (1024 * 1024)
            if ram_mb > peak_ram_mb:
                peak_ram_mb = ram_mb
                
            gpu_info = get_gpu_info()
            if gpu_info["has_gpu"] and gpu_info["vram_used_mb"] > peak_vram_mb:
                peak_vram_mb = gpu_info["vram_used_mb"]
                
            time.sleep(1)
            sys.stdout.write(f"\rRestante: {int(duration - (time.time() - start_time))}s | CPU Pico: {peak_cpu_percent:.1f}% | RAM Pico: {peak_ram_mb:.0f} MB")
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\nBenchmark interrompido pelo usuário.")
    finally:
        print("\n\nEncerrando SYNAPSE CORE, Interfaces e Threads (Hardkill)...")
        processes_to_kill = [core_process]
            
        for proc in processes_to_kill:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
            except psutil.NoSuchProcess:
                pass
            proc.kill()

    folder_size_mb = get_folder_size(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) / (1024 * 1024)
    cores_utilizados = max(1, int(peak_cpu_percent / 100) + 1)
    
    gerar_relatorio(os_info, cores_utilizados, peak_ram_mb, peak_vram_mb, folder_size_mb, peak_cpu_percent, num_sensors)

def format_gb(mb):
    if mb < 1024:
        return f"{mb:.0f} MB"
    return f"{mb / 1024:.2f} GB"

def get_next_tier(value, tiers):
    for t in tiers:
        if value <= t:
            return t
    return int(value) + (1 if value % 1 > 0 else 0)

def gerar_relatorio(os_info, base_cores, base_ram_mb, base_vram_mb, folder_size_mb, peak_cpu_percent, num_sensors):
    os_ram_reserve_mb = 2048 
    
    # Fatores de stress para o gateway de percepção
    stress_ram_factor = 1.8
    stress_cpu_factor = 1.5
    stress_vram_factor = 1.2
    
    ram_raw_gb = max(2048, (base_ram_mb * stress_ram_factor) + os_ram_reserve_mb + (num_sensors * 5)) / 1024.0
    cpu_cores_raw = int(base_cores * stress_cpu_factor) + 2
    disk_raw_gb = (folder_size_mb + (5.0 * num_sensors) + 2048) / 1024.0
    
    ram_recomendada = get_next_tier(ram_raw_gb, [4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 256])
    cpu_cores_recomendado = get_next_tier(cpu_cores_raw, [2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 64])
    disk_recomendado = get_next_tier(disk_raw_gb, [16, 32, 64, 128, 256, 512, 1024, 2048])
    
    if base_vram_mb > 0:
        vram_raw_gb = (base_vram_mb * stress_vram_factor) / 1024.0
        vram_recomendada = get_next_tier(vram_raw_gb, [2, 4, 6, 8, 10, 12, 16, 24, 32])
    else:
        vram_recomendada = 0

    if vram_recomendada == 0:
        if num_sensors <= 100:
            vram_text = "Integrada (Onboard) é suficiente"
        elif num_sensors <= 500:
            vram_text = "Placa de vídeo dedicada (Mínimo 2 GB VRAM) recomendada"
        else:
            vram_text = "Placa de vídeo dedicada com aceleração essencial para alta escala"
    else:
        vram_text = f"Dedicada com {vram_recomendada} GB VRAM"

    if num_sensors <= 200:
        disk_text = f"(HDD Suportado, SSD Recomendado)"
    else:
        disk_text = f"(SSD Obrigatório para fluxo contínuo de sensores)"

    if num_sensors <= 50:
        porte = "Porte: Pequeno (Rede de Sensores Básica)"
    elif num_sensors <= 200:
        porte = "Porte: Médio (Rede Intermediária)"
    elif num_sensors <= 1000:
        porte = "Porte: Grande (Múltiplas Rotas)"
    else:
        porte = "Porte: Massivo (Escala Metropolitana)"

    report = f"""==================================================
RELATÓRIO DE REQUISITOS DE HARDWARE - SYNAPSE CORE
==================================================

1. INFORMAÇÕES TÉCNICAS GERAIS
--------------------------------------------------
Sistema Operacional : Suporta {os_info} ou superior.
Arquitetura         : Exige 64-bit obrigatoriamente.
Conexão c/ Internet : Requer banda larga (Estimativa: {max(1, num_sensors // 50)} Mbps).
Dependências        : Python 3.8+, bibliotecas do requirements.txt.

2. MÉTRICAS BRUTAS OBTIDAS (TESTE COM {num_sensors} SENSORES MOCK)
--------------------------------------------------
- RAM Utilizada (S/ SO): {base_ram_mb:.1f} MB
- VRAM (GPU) Utilizada: {base_vram_mb:.1f} MB
- Uso Máximo de CPU (Threads): {peak_cpu_percent:.1f}%

3. REQUISITOS DE HARDWARE RECOMENDADOS ({porte})
--------------------------------------------------
Processador (CPU)   : {cpu_cores_recomendado} Núcleos reais (ou threads lógicas)
Memória (RAM)       : {ram_recomendada} GB (Já inclui folga e uso do sistema operacional)
Armazenamento       : {disk_recomendado} GB {disk_text}
Placa de Vídeo (GPU): {vram_text}

==================================================
"""

    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark.txt"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nRelatório focado gerado com sucesso em: {report_path}")

if __name__ == "__main__":
    print("==================================================")
    print("       SYNAPSE - CONFIGURAÇÃO DE BENCHMARK        ")
    print("==================================================")
    
    try:
        user_input = input("Quantos sensores deseja simular no teste base? [Padrão: 50]: ").strip()
        num_sensors = int(user_input) if user_input else 50
        
        duracao_teste = 60 # Tempo tabelado fixado
    except ValueError:
        print("Entrada inválida. Usando valores padrão (50 sensores, 60 segundos).")
        num_sensors = 50
        duracao_teste = 60
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(0)

    run_benchmark(num_sensors, duracao_teste)
