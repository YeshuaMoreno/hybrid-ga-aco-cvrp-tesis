"""
generate_best_routes.py
Ejecuta una corrida individual por cada escenario y algoritmo para obtener
la mejor ruta y guardarla en assets/routes/.

Uso:
    python generate_best_routes.py

Salida:
    assets/routes/best_route_<escenario>_<solver>.json

Nota:
    Usa la semilla óptima encontrada en los benchmarks (seed=42 por defecto).
    Los resultados se guardan para que el dashboard los pueda visualizar.
"""

import json
import time
from pathlib import Path

BASE = Path(__file__).parent
ROUTES_DIR = BASE / "assets" / "routes"

SCENARIOS = [
    {
        "name": "base",
        "label": "Base",
        "traffic_factor": 1.0,
        "service_extra": 0,
        "service_factor": 1.0,
    },
    {
        "name": "hora_pico",
        "label": "Hora Pico",
        "traffic_factor": 2.0,
        "service_extra": 0,
        "service_factor": 1.0,
    },
    {
        "name": "congestion_tienda",
        "label": "Tienda Congestionada",
        "traffic_factor": 1.0,
        "service_extra": 15,
        "service_factor": 1.0,
    },
    {
        "name": "estres",
        "label": "Estrés",
        "traffic_factor": 4.0,
        "service_extra": 0,
        "service_factor": 1.0,
    },
    {
        "name": "estres_total",
        "label": "Estrés Total",
        "traffic_factor": 10.0,
        "service_extra": 0,
        "service_factor": 1.0,
    },
]

SOLVERS = ["ga", "aco", "hybrid"]
DATA_CSV = str(BASE / "data" / "dataset_artegasaltillo.csv")
MATRIX_JSON = str(BASE / "data" / "matriz_real.json")
CAPACITY_KG = 15000.0
MAX_VEHICLES = 1
SEED = 42


def _build_problem(scenario: dict):
    from src.problem import load_problem_from_csv

    return load_problem_from_csv(
        csv_path=DATA_CSV,
        capacity_kg=CAPACITY_KG,
        max_vehicles=MAX_VEHICLES,
        speed_kmh=35.0,
        matrix_json_path=MATRIX_JSON if Path(MATRIX_JSON).exists() else None,
        traffic_factor=scenario["traffic_factor"],
        service_factor=scenario["service_factor"],
        service_extra=scenario["service_extra"],
    )


def _build_solver(solver_name: str):
    from src.solvers.ga import GASolver, GAConfig
    from src.solvers.aco import ACOSolver, ACOConfig
    from src.solvers.hybrid import HybridGAACOSolver, HybridConfig

    late_p, cap_p, veh_p = 200.0, 0.5, 5000.0

    if solver_name == "ga":
        cfg = GAConfig(pop_size=80, generations=250, seed=SEED)
        return GASolver(cfg, late_p, cap_p, veh_p)
    if solver_name == "aco":
        cfg = ACOConfig(n_ants=40, iterations=200, seed=SEED)
        return ACOSolver(cfg, late_p, cap_p, veh_p)
    if solver_name == "hybrid":
        ga_cfg = GAConfig(pop_size=80, generations=150, seed=SEED)
        aco_cfg = ACOConfig(n_ants=40, iterations=150, seed=SEED)
        cfg = HybridConfig(ga=ga_cfg, aco=aco_cfg)
        return HybridGAACOSolver(cfg, late_p, cap_p, veh_p)
    raise ValueError(f"Solver desconocido: {solver_name}")


def main() -> None:
    ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    print("Generando mejores rutas por escenario y algoritmo…\n")

    for sc in SCENARIOS:
        try:
            problem = _build_problem(sc)
        except Exception as exc:
            print(f"  [ERROR] No se pudo construir el problema para '{sc['label']}': {exc}")
            continue

        for solver_name in SOLVERS:
            out_file = ROUTES_DIR / f"best_route_{sc['name']}_{solver_name}.json"
            print(f"  {sc['label']} × {solver_name.upper()}…", end=" ", flush=True)

            try:
                solver = _build_solver(solver_name)
                t0 = time.perf_counter()
                routes, metrics = solver.solve(problem)
                runtime = time.perf_counter() - t0

                route_data = {
                    "scenario": sc["label"],
                    "solver": solver_name,
                    "traffic_factor": sc["traffic_factor"],
                    "service_extra": sc["service_extra"],
                    "seed": SEED,
                    "runtime_seconds": round(runtime, 4),
                    "metrics": {
                        "objective": round(metrics.objective, 4),
                        "total_km": round(metrics.total_km, 4),
                        "late_minutes": round(metrics.late_minutes, 2),
                        "wait_minutes": round(metrics.wait_minutes, 2),
                        "route_time_minutes": round(metrics.route_time_minutes, 2),
                        "vehicles_used": metrics.vehicles_used,
                        "capacity_violation_kg": round(metrics.capacity_violation_kg, 2),
                    },
                    "routes": [
                        {
                            "vehicle": i + 1,
                            "stops": [0] + r + [0],
                            "stop_names": [problem.nodes[s].name for s in ([0] + r + [0])],
                            "load_bultos": sum(problem.nodes[c].demand_bultos for c in r),
                            "load_kg": round(sum(problem.nodes[c].demand_kg for c in r), 2),
                        }
                        for i, r in enumerate(routes)
                    ],
                    "node_coords": [
                        {
                            "id": n.id,
                            "name": n.name,
                            "lat": n.lat,
                            "lon": n.lon,
                            "node_type": n.node_type,
                        }
                        for n in problem.nodes
                    ],
                }
                out_file.write_text(json.dumps(route_data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"obj={metrics.objective:.3f}  km={metrics.total_km:.3f}  ✓")

            except Exception as exc:
                print(f"ERROR: {exc}")

    print(f"\nRutas guardadas en: {ROUTES_DIR}")


if __name__ == "__main__":
    main()
