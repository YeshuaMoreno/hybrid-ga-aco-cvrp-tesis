import argparse
import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List, Tuple
from dataclasses import dataclass, field

from src.problem import load_problem_from_csv, CVRPProblem, BULTO_KG, DEFAULT_SPEED_KMH
from src.evaluation import EvalMetrics
from src.solvers.ga import GASolver, GAConfig
from src.solvers.aco import ACOSolver, ACOConfig
from src.solvers.hybrid import HybridGAACOSolver, HybridConfig


DEFAULT_LATE_PENALTY_PER_MIN = 200.0
DEFAULT_CAP_PENALTY_PER_KG = 0.5
DEFAULT_VEHICLE_PENALTY = 5000.0


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def save_run_results(
    out_dir: Path,
    tag: str,
    solver_name: str,
    csv_path: str,
    runtime_seconds: float,
    problem: CVRPProblem,
    routes: List[List[int]],
    metrics: EvalMetrics
) -> Tuple[Path, Path]:
    ensure_dir(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{stamp}_{solver_name}_{tag}".replace(" ", "_")

    summary_path = out_dir / f"{base}_summary.json"
    summary = {
        "timestamp": stamp,
        "solver": solver_name,
        "data": csv_path,
        "capacity_kg": problem.capacity_kg,
        "capacity_bultos_equiv": problem.capacity_kg / BULTO_KG,
        "max_vehicles": problem.max_vehicles,
        "speed_kmh": problem.speed_kmh,
        "metrics": {
            "objective": metrics.objective,
            "total_km": metrics.total_km,
            "late_minutes": metrics.late_minutes,
            "wait_minutes": metrics.wait_minutes,
            "route_time_minutes": metrics.route_time_minutes,
            "vehicles_used": metrics.vehicles_used,
            "vehicles_extra": metrics.vehicles_extra,
            "capacity_violation_kg": metrics.capacity_violation_kg,
            "runtime_seconds": runtime_seconds,
        },
        "routes": [
            {
                "vehicle": i + 1,
                "stops": [0] + r + [0],
                "stop_names": [problem.nodes[s].name for s in ([0] + r + [0])],
                "load_bultos": sum(problem.nodes[s].demand_bultos for s in r),
                "load_kg": sum(problem.nodes[s].demand_kg for s in r)
            }
            for i, r in enumerate(routes)
        ]
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    routes_path = out_dir / f"{base}_routes.csv"
    with open(routes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vehicle", "sequence_ids", "sequence_names", "load_bultos", "load_kg"])
        for i, r in enumerate(routes):
            seq = [0] + r + [0]
            w.writerow([
                i + 1,
                "->".join(map(str, seq)),
                "->".join(problem.nodes[s].name for s in seq),
                sum(problem.nodes[s].demand_bultos for s in r),
                round(sum(problem.nodes[s].demand_kg for s in r), 2)
            ])

    return summary_path, routes_path


def print_solution(problem: CVRPProblem, routes: List[List[int]], metrics: EvalMetrics) -> None:
    print("\n=== RESULTADO ===")
    print(f"Objetivo: {metrics.objective:.3f}")
    print(f"Distancia total: {metrics.total_km:.3f} km")
    print(f"Tarde total: {metrics.late_minutes:.1f} min | Espera total: {metrics.wait_minutes:.1f} min")
    print(f"Vehículos usados: {metrics.vehicles_used} (extra: {metrics.vehicles_extra})")
    print(f"Violación de capacidad: {metrics.capacity_violation_kg:.1f} kg")
    print(f"Tiempo total (suma rutas): {metrics.route_time_minutes:.1f} min")

    for i, r in enumerate(routes, start=1):
        load_b = sum(problem.nodes[c].demand_bultos for c in r)
        load_kg = sum(problem.nodes[c].demand_kg for c in r)
        names = [problem.nodes[x].name for x in r]
        print(f"\nVehículo {i}: carga {load_b} bultos ({load_kg:.1f} kg)")
        print("  Ruta:", "CEDIS -> " + " -> ".join(names) + " -> CEDIS")


def build_solver(name: str, args) -> Any:
    if name == "ga":
        cfg = GAConfig(
            pop_size=args.ga_pop,
            generations=args.ga_gen,
            crossover_rate=args.ga_cx,
            mutation_rate=args.ga_mut,
            tournament_k=args.ga_k,
            elite=args.ga_elite,
            seed=args.seed
        )
        return GASolver(cfg, args.late_penalty, args.cap_penalty, args.vehicle_penalty)

    if name == "aco":
        cfg = ACOConfig(
            n_ants=args.aco_ants,
            iterations=args.aco_it,
            alpha=args.aco_alpha,
            beta=args.aco_beta,
            rho=args.aco_rho,
            Q=args.aco_Q,
            tau0=args.aco_tau0,
            seed=args.seed
        )
        return ACOSolver(cfg, args.late_penalty, args.cap_penalty, args.vehicle_penalty)

    if name == "hybrid":
        ga_cfg = GAConfig(
            pop_size=args.ga_pop,
            generations=args.ga_gen_hybrid,
            crossover_rate=args.ga_cx,
            mutation_rate=args.ga_mut,
            tournament_k=args.ga_k,
            elite=args.ga_elite,
            seed=args.seed
        )
        aco_cfg = ACOConfig(
            n_ants=args.aco_ants,
            iterations=args.aco_it_hybrid,
            alpha=args.aco_alpha,
            beta=args.aco_beta,
            rho=args.aco_rho,
            Q=args.aco_Q,
            tau0=args.aco_tau0,
            seed=args.seed
        )
        cfg = HybridConfig(ga=ga_cfg, aco=aco_cfg, pheromone_boost=args.hy_boost)
        return HybridGAACOSolver(cfg, args.late_penalty, args.cap_penalty, args.vehicle_penalty)

    raise ValueError(f"Solver desconocido: {name}")


def cmd_run(args) -> int:
    if args.capacity_kg is not None:
        capacity_kg = float(args.capacity_kg)
    elif args.capacity_bultos is not None:
        capacity_kg = float(args.capacity_bultos) * BULTO_KG
    else:
        raise ValueError("Debes pasar --capacity-kg o --capacity-bultos.")

    problem = load_problem_from_csv(
        csv_path=args.data,
        capacity_kg=capacity_kg,
        max_vehicles=args.max_vehicles,
        speed_kmh=args.speed_kmh,
        matrix_json_path=args.matrix_json,
        traffic_factor=args.traffic_factor,
        service_factor=args.service_factor,
        service_extra=args.service_extra
    )

    solver = build_solver(args.solver, args)

    t0 = time.perf_counter()
    routes, metrics = solver.solve(problem)
    t1 = time.perf_counter()
    runtime_seconds = t1 - t0

    print_solution(problem, routes, metrics)

    out_dir = Path(args.out_dir)
    summary_path, routes_path = save_run_results(
        out_dir=out_dir,
        tag=args.tag or "run",
        solver_name=args.solver,
        csv_path=args.data,
        runtime_seconds=runtime_seconds,
        problem=problem,
        routes=routes,
        metrics=metrics
    )

    print(f"\nGuardado:\n- {summary_path}\n- {routes_path}")
    return 0


def cmd_benchmark(args) -> int:
    if args.capacity_kg is not None:
        capacity_kg = float(args.capacity_kg)
    elif args.capacity_bultos is not None:
        capacity_kg = float(args.capacity_bultos) * BULTO_KG
    else:
        raise ValueError("Debes pasar --capacity-kg o --capacity-bultos.")

    problem = load_problem_from_csv(
        csv_path=args.data,
        capacity_kg=capacity_kg,
        max_vehicles=args.max_vehicles,
        speed_kmh=args.speed_kmh,
        matrix_json_path=args.matrix_json,
        traffic_factor=args.traffic_factor,
        service_factor=args.service_factor,
        service_extra=args.service_extra
    )

    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    results = []
    for r in range(args.runs):
        seed = (args.seed or 0) + r
        args_local = argparse.Namespace(**vars(args))
        args_local.seed = seed

        solver = build_solver(args.solver, args_local)

        t0 = time.perf_counter()
        routes, metrics = solver.solve(problem)
        t1 = time.perf_counter()
        runtime_seconds = t1 - t0

        results.append({
            "run": r + 1,
            "seed": seed,
            "objective": metrics.objective,
            "total_km": metrics.total_km,
            "late_minutes": metrics.late_minutes,
            "vehicles_used": metrics.vehicles_used,
            "capacity_violation_kg": metrics.capacity_violation_kg,
            "wait_minutes": metrics.wait_minutes,
            "route_time_minutes": metrics.route_time_minutes,
            "runtime_seconds": runtime_seconds
        })

        print(
            f"Run {r+1}/{args.runs} seed={seed} "
            f"obj={metrics.objective:.3f} km={metrics.total_km:.3f} late={metrics.late_minutes:.1f}"
        )

    objectives = [x["objective"] for x in results]
    kms = [x["total_km"] for x in results]
    late = [x["late_minutes"] for x in results]
    wait = [x["wait_minutes"] for x in results]
    route_time = [x["route_time_minutes"] for x in results]
    runtimes = [x["runtime_seconds"] for x in results]

    def mean(xs): return sum(xs) / max(len(xs), 1)

    def stdev(xs):
        m = mean(xs)
        return math.sqrt(sum((v - m) ** 2 for v in xs) / max(len(xs) - 1, 1))

    bench = {
        "solver": args.solver,
        "runs": args.runs,
        "scenario_name": getattr(args, "scenario_name", "") or "",
        "traffic_factor": args.traffic_factor,
        "service_extra": args.service_extra,
        "service_factor": args.service_factor,
        "seed_base": args.seed if args.seed is not None else 0,
        "data": args.data,
        "matrix_json": args.matrix_json or "",
        "capacity_kg": problem.capacity_kg,
        "max_vehicles": problem.max_vehicles,
        "speed_kmh": problem.speed_kmh,
        "penalties": {
            "late_penalty_per_min": args.late_penalty,
            "cap_penalty_per_kg": args.cap_penalty,
            "vehicle_penalty": args.vehicle_penalty
        },
        "stats": {
            "objective_mean": mean(objectives),
            "objective_stdev": stdev(objectives),
            "km_mean": mean(kms),
            "km_stdev": stdev(kms),
            "late_mean": mean(late),
            "late_stdev": stdev(late),
            "wait_mean": mean(wait),
            "wait_stdev": stdev(wait),
            "route_time_mean": mean(route_time),
            "route_time_stdev": stdev(route_time),
            "runtime_mean": mean(runtimes),
            "runtime_stdev": stdev(runtimes),
            "objective_best": min(objectives),
            "objective_worst": max(objectives),
            "runtime_best": min(runtimes),
            "runtime_worst": max(runtimes)
        },
        "runs_detail": results
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{stamp}_{args.solver}_benchmark_{args.runs}runs.json"
    out_path.write_text(json.dumps(bench, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nBenchmark guardado en: {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser):
        sp.add_argument("--data", required=True, help="Ruta al CSV de nodos")
        sp.add_argument("--matrix-json", default=None, help="Ruta al JSON con distance_matrix_km y duration_matrix_min")
        sp.add_argument("--solver", choices=["ga", "aco", "hybrid"], default="hybrid")
        sp.add_argument("--capacity-bultos", type=float, default=None)
        sp.add_argument("--capacity-kg", type=float, default=None)
        sp.add_argument("--max-vehicles", type=int, default=None)
        sp.add_argument("--speed-kmh", type=float, default=DEFAULT_SPEED_KMH)
        sp.add_argument("--seed", type=int, default=42)
        sp.add_argument("--out-dir", default="results")
        sp.add_argument("--tag", default="")
        sp.add_argument("--scenario-name", default="", help="Nombre del escenario: 'Base', 'Hora Pico', 'Tienda Congestionada', 'Estres', 'Estres Total'")
        sp.add_argument("--traffic-factor", type=float, default=1.0, help="Multiplicador de tiempo vial para simular tráfico: 1.4")
        sp.add_argument("--service-factor", type=float, default=1.0, help="Multiplicador del tiempo de servicio en tiendas: 1.5")
        sp.add_argument("--service-extra", type=int, default=0, help="Minutos extra fijos de servicio por tienda: 15")

        sp.add_argument("--late-penalty", type=float, default=DEFAULT_LATE_PENALTY_PER_MIN)
        sp.add_argument("--cap-penalty", type=float, default=DEFAULT_CAP_PENALTY_PER_KG)
        sp.add_argument("--vehicle-penalty", type=float, default=DEFAULT_VEHICLE_PENALTY)

        sp.add_argument("--ga-pop", type=int, default=80)
        sp.add_argument("--ga-gen", type=int, default=250)
        sp.add_argument("--ga-gen-hybrid", type=int, default=150)
        sp.add_argument("--ga-cx", type=float, default=0.9)
        sp.add_argument("--ga-mut", type=float, default=0.25)
        sp.add_argument("--ga-k", type=int, default=3)
        sp.add_argument("--ga-elite", type=int, default=2)

        sp.add_argument("--aco-ants", type=int, default=40)
        sp.add_argument("--aco-it", type=int, default=200)
        sp.add_argument("--aco-it-hybrid", type=int, default=150)
        sp.add_argument("--aco-alpha", type=float, default=1.0)
        sp.add_argument("--aco-beta", type=float, default=3.0)
        sp.add_argument("--aco-rho", type=float, default=0.2)
        sp.add_argument("--aco-Q", type=float, default=100.0)
        sp.add_argument("--aco-tau0", type=float, default=0.01)

        sp.add_argument("--hy-boost", type=float, default=0.2)

    run_p = sub.add_parser("run", help="Ejecuta una corrida")
    add_common(run_p)
    run_p.set_defaults(func=cmd_run)

    bench_p = sub.add_parser("benchmark", help="Ejecuta múltiples corridas")
    add_common(bench_p)
    bench_p.add_argument("--runs", type=int, default=20)
    bench_p.set_defaults(func=cmd_benchmark)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())