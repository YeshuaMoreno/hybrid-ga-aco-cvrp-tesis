from dataclasses import dataclass
from typing import List
from src.problem import CVRPProblem


@dataclass
class EvalMetrics:
    objective: float
    total_km: float
    late_minutes: float
    wait_minutes: float
    route_time_minutes: float
    vehicles_used: int
    capacity_violation_kg: float
    vehicles_extra: int


def decode_split_by_capacity_kg(problem: CVRPProblem, perm: List[int]) -> List[List[int]]:
    routes: List[List[int]] = []
    current: List[int] = []
    load = 0.0

    for c in perm:
        dem = problem.nodes[c].demand_kg
        if current and load + dem > problem.capacity_kg:
            routes.append(current)
            current = [c]
            load = dem
        else:
            current.append(c)
            load += dem

    if current:
        routes.append(current)

    return routes


def evaluate_routes_vrptw_light(
    problem: CVRPProblem,
    routes: List[List[int]],
    late_penalty_per_min: float,
    cap_penalty_per_kg: float,
    vehicle_penalty: float
) -> EvalMetrics:
    depot = problem.nodes[0]

    total_km = 0.0
    late = 0.0
    wait = 0.0
    total_time = 0.0
    cap_violation = 0.0

    vehicles_used = len(routes)
    vehicles_extra = 0

    if problem.max_vehicles is not None and vehicles_used > problem.max_vehicles:
        vehicles_extra = vehicles_used - problem.max_vehicles

    for r in routes:
        # capacidad
        load_kg = sum(problem.nodes[c].demand_kg for c in r)
        if load_kg > problem.capacity_kg:
            cap_violation += (load_kg - problem.capacity_kg)

        # salida inteligente: salir para llegar a la 1ra parada cerca de su tw_start
        smart_depart = float(depot.tw_start)
        if r:
            first = r[0]
            eta_depart = problem.nodes[first].tw_start - problem.travel_minutes(0, first)
            if eta_depart > smart_depart:
                smart_depart = float(eta_depart)

        t = smart_depart
        prev = 0

        for c in r:
            t += problem.travel_minutes(prev, c)
            node = problem.nodes[c]

            # 1) si llegas antes, esperas a que abra ventana
            if t < node.tw_start:
                wait += (node.tw_start - t)
                t = float(node.tw_start)

            # 2) bloqueo tipo Tecnovalores (si aplica)
            block_start = getattr(node, "block_start", None)
            block_end = getattr(node, "block_end", None)
            if block_start is not None and block_end is not None:
                if block_start <= t < block_end:
                    wait += (block_end - t)
                    t = float(block_end)

            # 3) ya con todo lo anterior aplicado, revisas tardanza
            if t > node.tw_end:
                late += (t - node.tw_end)

            # 4) servicio
            t += float(node.service_time)

            # 5) distancia y avance
            total_km += problem.dist_km[prev][c]
            prev = c
            
            # bloqueo por Tecnovalores y otros no se puede atender a nadie
            block_start = getattr(node, "block_start", None)
            block_end = getattr(node, "block_end", None)
            if block_start is not None and block_end is not None:
                if block_start <= t < block_end:
                    wait += (block_end - t)
                    t = float(block_end)

        # regreso a depot
        t += problem.travel_minutes(prev, 0)
        total_km += problem.dist_km[prev][0]

        if t > depot.tw_end:
            late += (t - depot.tw_end)

        total_time += (t - smart_depart)

    objective = (
        total_km
        + late_penalty_per_min * late
        + cap_penalty_per_kg * cap_violation
        + vehicle_penalty * vehicles_extra
    )

    return EvalMetrics(
        objective=objective,
        total_km=total_km,
        late_minutes=late,
        wait_minutes=wait,
        route_time_minutes=total_time,
        vehicles_used=vehicles_used,
        capacity_violation_kg=cap_violation,
        vehicles_extra=vehicles_extra
    )