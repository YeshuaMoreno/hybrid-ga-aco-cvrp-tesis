from dataclasses import dataclass, field
from typing import List

from src.solvers.ga import GASolver, GAConfig
from src.solvers.aco import ACOSolver, ACOConfig


@dataclass
class HybridConfig:
    ga: GAConfig = field(default_factory=lambda: GAConfig(generations=150))
    aco: ACOConfig = field(default_factory=lambda: ACOConfig(iterations=150))
    pheromone_boost: float = 0.2


class HybridGAACOSolver:
    def __init__(self, cfg: HybridConfig, late_penalty_per_min: float, cap_penalty_per_kg: float, vehicle_penalty: float):
        self.cfg = cfg
        self.late_penalty_per_min = late_penalty_per_min
        self.cap_penalty_per_kg = cap_penalty_per_kg
        self.vehicle_penalty = vehicle_penalty

    def solve(self, problem):
        ga = GASolver(self.cfg.ga, self.late_penalty_per_min, self.cap_penalty_per_kg, self.vehicle_penalty)
        ga_routes, ga_metrics = ga.solve(problem)

        n = len(problem.nodes)
        tau0 = self.cfg.aco.tau0
        tau = [[tau0] * n for _ in range(n)]
        self._seed_pheromone(tau, ga_routes, self.cfg.pheromone_boost)

        aco = ACOSolver(
            self.cfg.aco,
            self.late_penalty_per_min,
            self.cap_penalty_per_kg,
            self.vehicle_penalty,
            initial_pheromone=tau
        )
        aco_routes, aco_metrics = aco.solve(problem)

        if ga_metrics.objective <= aco_metrics.objective:
            return ga_routes, ga_metrics
        return aco_routes, aco_metrics

    def _seed_pheromone(self, tau: List[List[float]], routes: List[List[int]], boost: float):
        for r in routes:
            prev = 0
            for c in r:
                tau[prev][c] += boost
                tau[c][prev] += boost
                prev = c
            tau[prev][0] += boost
            tau[0][prev] += boost