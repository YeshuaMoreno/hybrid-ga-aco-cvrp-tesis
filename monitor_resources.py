"""
monitor_resources.py
Registra uso de CPU y RAM a intervalos regulares durante la ejecución de benchmarks.

Uso:
    python monitor_resources.py --interval 2 --output assets/resource_log.csv

Ctrl+C detiene el registro.

Requiere:
    pip install psutil
"""

import argparse
import csv
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    print(
        "[ERROR] psutil no está instalado.\n"
        "Ejecuta: pip install psutil"
    )
    sys.exit(1)


BASE = Path(__file__).parent
DEFAULT_OUTPUT = BASE / "assets" / "resource_log.csv"

FIELDNAMES = [
    "timestamp",
    "elapsed_s",
    "cpu_percent",
    "ram_used_gb",
    "ram_total_gb",
    "ram_percent",
    "ram_available_gb",
]

_running = True


def _handle_signal(signum, frame):
    global _running
    _running = False


def monitor(interval: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output.exists()

    with output.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        t_start = time.perf_counter()
        print(f"Monitoreando CPU/RAM → {output}")
        print("Presiona Ctrl+C para detener.\n")

        while _running:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            elapsed = time.perf_counter() - t_start
            row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_s": round(elapsed, 2),
                "cpu_percent": round(cpu, 2),
                "ram_used_gb": round(mem.used / 1e9, 3),
                "ram_total_gb": round(mem.total / 1e9, 3),
                "ram_percent": round(mem.percent, 2),
                "ram_available_gb": round(mem.available / 1e9, 3),
            }
            writer.writerow(row)
            f.flush()
            print(
                f"[{row['timestamp']}] CPU={row['cpu_percent']:5.1f}%  "
                f"RAM={row['ram_percent']:5.1f}%  "
                f"({row['ram_used_gb']:.2f}/{row['ram_total_gb']:.2f} GB)",
                end="\r",
            )
            time.sleep(interval)

    print(f"\n\nMonitoreo finalizado. Log guardado en: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitorea CPU y RAM durante benchmarks.")
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="Segundos entre mediciones (default: 2)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Ruta del CSV de salida (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    if args.interval < 0.5:
        print("[AVISO] Intervalo mínimo recomendado: 0.5 s")
        args.interval = 0.5

    # Manejo de señales para terminar limpiamente
    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    monitor(args.interval, args.output)


if __name__ == "__main__":
    main()
