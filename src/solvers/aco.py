from dataclasses import dataclass
from typing import List, Optional
import random

from src.problem import CVRPProblem
from src.evaluation import EvalMetrics, evaluate_routes_vrptw_light


@dataclass
class ACOConfig:
    n_ants: int = 40
    iterations: int = 200
    alpha: float = 1.0
    beta: float = 3.0
    rho: float = 0.2
    Q: float = 100.0
    tau0: float = 0.01
    seed: Optional[int] = 123


def roulette_choice(items: List[int], weights: List[float]) -> int:
    s = sum(weights)
    if s <= 0:
        return random.choice(items)

    r = random.random() * s
    acc = 0.0
    for it, w in zip(items, weights):
        acc += w
        if acc >= r:
            return it
    return items[-1]


class ACOSolver:
    def __init__(
        self,
        cfg: ACOConfig,
        late_penalty_per_min: float,
        cap_penalty_per_kg: float,
        vehicle_penalty: float,
        initial_pheromone: Optional[List[List[float]]] = None
    ):
        self.cfg = cfg
        self.late_penalty_per_min = late_penalty_per_min
        self.cap_penalty_per_kg = cap_penalty_per_kg
        self.vehicle_penalty = vehicle_penalty
        self.initial_pheromone = initial_pheromone

        if cfg.seed is not None:
            random.seed(cfg.seed)

    def solve(self, problem: CVRPProblem):
        n = len(problem.nodes)

        tau = self._init_pheromone(n)
        eta = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j:
                    eta[i][j] = 1.0 / (problem.dist_km[i][j] + 1e-9)

        best_routes = None
        best_metrics = EvalMetrics(
            objective=float("inf"),
            total_km=0.0,
            late_minutes=0.0,
            wait_minutes=0.0,
            route_time_minutes=0.0,
            vehicles_used=0,
            capacity_violation_kg=0.0,
            vehicles_extra=0
        )

        for _ in range(self.cfg.iterations):
            it_best_routes = None
            it_best_metrics = None

            for _ in range(self.cfg.n_ants):
                routes = self._construct_solution(problem, tau, eta)
                metrics = evaluate_routes_vrptw_light(
                    problem, routes,
                    self.late_penalty_per_min, self.cap_penalty_per_kg, self.vehicle_penalty
                )

                if it_best_metrics is None or metrics.objective < it_best_metrics.objective:
                    it_best_metrics = metrics
                    it_best_routes = routes

            if it_best_metrics and it_best_metrics.objective < best_metrics.objective:
                best_metrics = it_best_metrics
                best_routes = it_best_routes

            for i in range(n):
                for j in range(n):
                    tau[i][j] *= (1.0 - self.cfg.rho)

            if best_routes is not None:
                self._deposit(problem, tau, best_routes, best_metrics)

        return best_routes if best_routes is not None else [], best_metrics

    def _init_pheromone(self, n: int) -> List[List[float]]:
        if self.initial_pheromone is not None:
            return [row[:] for row in self.initial_pheromone]
        return [[self.cfg.tau0] * n for _ in range(n)]

    def _deposit(self, problem: CVRPProblem, tau: List[List[float]], routes: List[List[int]], metrics: EvalMetrics):
        delta = self.cfg.Q / (metrics.objective + 1e-9)

        for r in routes:
            prev = 0
            for c in r:
                tau[prev][c] += delta
                tau[c][prev] += delta
                prev = c
            tau[prev][0] += delta
            tau[0][prev] += delta

    def _construct_solution(self, problem: CVRPProblem, tau, eta):
        unvisited = set(range(1, len(problem.nodes)))
        routes = []

        while unvisited:
            route = []
            load = 0.0
            current = 0

            while True:
                feasible = [c for c in unvisited if load + problem.nodes[c].demand_kg <= problem.capacity_kg]
                if not feasible:
                    break

                weights = []
                for c in feasible:
                    w = (tau[current][c] ** self.cfg.alpha) * (eta[current][c] ** self.cfg.beta)
                    weights.append(w)

                nxt = roulette_choice(feasible, weights)
                route.append(nxt)
                unvisited.remove(nxt)
                load += problem.nodes[nxt].demand_kg
                current = nxt

                if not unvisited:
                    break

            routes.append(route)

        return routes