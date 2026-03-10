from dataclasses import dataclass
from typing import List, Tuple, Optional
import random

from src.problem import CVRPProblem
from src.evaluation import EvalMetrics, decode_split_by_capacity_kg, evaluate_routes_vrptw_light


@dataclass
class GAConfig:
    pop_size: int = 80
    generations: int = 250
    crossover_rate: float = 0.9
    mutation_rate: float = 0.25
    tournament_k: int = 3
    elite: int = 2
    seed: Optional[int] = 42


def ox_crossover(p1: List[int], p2: List[int]) -> Tuple[List[int], List[int]]:
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))

    def build(pa, pb):
        child = [None] * n
        child[a:b+1] = pa[a:b+1]
        fill = [x for x in pb if x not in child]
        idx = 0
        for i in range(n):
            if child[i] is None:
                child[i] = fill[idx]
                idx += 1
        return child

    return build(p1, p2), build(p2, p1)


def mutate_inplace(perm: List[int]) -> None:
    n = len(perm)
    move = random.choice(["swap", "invert", "reinsert"])
    i, j = sorted(random.sample(range(n), 2))

    if move == "swap":
        perm[i], perm[j] = perm[j], perm[i]
    elif move == "invert":
        perm[i:j+1] = list(reversed(perm[i:j+1]))
    else:
        x = perm.pop(j)
        perm.insert(i, x)


class GASolver:
    def __init__(self, cfg: GAConfig, late_penalty_per_min: float, cap_penalty_per_kg: float, vehicle_penalty: float):
        self.cfg = cfg
        self.late_penalty_per_min = late_penalty_per_min
        self.cap_penalty_per_kg = cap_penalty_per_kg
        self.vehicle_penalty = vehicle_penalty

        if cfg.seed is not None:
            random.seed(cfg.seed)

    def solve(self, problem: CVRPProblem):
        n_customers = len(problem.nodes) - 1
        base = list(range(1, n_customers + 1))

        population = [random.sample(base, k=len(base)) for _ in range(self.cfg.pop_size)]
        scores = [self._fitness(problem, ind) for ind in population]

        best_idx = min(range(len(population)), key=lambda i: scores[i].objective)
        best_ind = population[best_idx][:]
        best_metrics = scores[best_idx]

        for _ in range(self.cfg.generations):
            new_pop = []

            elite_indices = sorted(range(len(population)), key=lambda i: scores[i].objective)[:self.cfg.elite]
            for ei in elite_indices:
                new_pop.append(population[ei][:])

            while len(new_pop) < self.cfg.pop_size:
                p1 = self._tournament(population, scores)
                p2 = self._tournament(population, scores)

                if random.random() < self.cfg.crossover_rate:
                    c1, c2 = ox_crossover(p1, p2)
                else:
                    c1, c2 = p1[:], p2[:]

                if random.random() < self.cfg.mutation_rate:
                    mutate_inplace(c1)
                if random.random() < self.cfg.mutation_rate:
                    mutate_inplace(c2)

                new_pop.append(c1)
                if len(new_pop) < self.cfg.pop_size:
                    new_pop.append(c2)

            population = new_pop
            scores = [self._fitness(problem, ind) for ind in population]

            gen_best_idx = min(range(len(population)), key=lambda i: scores[i].objective)
            if scores[gen_best_idx].objective < best_metrics.objective:
                best_metrics = scores[gen_best_idx]
                best_ind = population[gen_best_idx][:]

        best_routes = decode_split_by_capacity_kg(problem, best_ind)
        best_metrics = evaluate_routes_vrptw_light(
            problem, best_routes,
            self.late_penalty_per_min, self.cap_penalty_per_kg, self.vehicle_penalty
        )
        return best_routes, best_metrics

    def _fitness(self, problem: CVRPProblem, perm: List[int]) -> EvalMetrics:
        routes = decode_split_by_capacity_kg(problem, perm)
        return evaluate_routes_vrptw_light(
            problem, routes,
            self.late_penalty_per_min, self.cap_penalty_per_kg, self.vehicle_penalty
        )

    def _tournament(self, population, scores):
        cand = random.sample(range(len(population)), k=self.cfg.tournament_k)
        best = min(cand, key=lambda i: scores[i].objective)
        return population[best][:]