from dataclasses import dataclass
from typing import List, Optional, Tuple
import csv
import json
import math

BULTO_KG = 7.0
DEFAULT_SPEED_KMH = 35.0


@dataclass(frozen=True)
class Node:
    id: int
    name: str
    lat: float
    lon: float
    demand_bultos: int
    tw_start: int
    tw_end: int
    service_time: int
    node_type: str  # depot/store

    @property
    def demand_kg(self) -> float:
        return self.demand_bultos * BULTO_KG


@dataclass
class CVRPProblem:
    nodes: List[Node]
    capacity_kg: float
    max_vehicles: Optional[int]
    speed_kmh: float = DEFAULT_SPEED_KMH
    dist_km: Optional[List[List[float]]] = None
    dur_min: Optional[List[List[float]]] = None

    def __post_init__(self):
        n = len(self.nodes)

        if self.dist_km is None and self.dur_min is None:
            self.dist_km = build_haversine_distance_matrix(self.nodes)
            self.dur_min = build_duration_matrix_from_distance(self.dist_km, self.speed_kmh)
        elif self.dist_km is not None and self.dur_min is None:
            validate_square_matrix(self.dist_km, n, "dist_km")
            self.dur_min = build_duration_matrix_from_distance(self.dist_km, self.speed_kmh)
        elif self.dist_km is None and self.dur_min is not None:
            raise ValueError("Se proporcionó 'duration_matrix_min' pero no 'distance_matrix_km'.")
        else:
            validate_square_matrix(self.dist_km, n, "dist_km")
            validate_square_matrix(self.dur_min, n, "dur_min")

    def travel_minutes(self, i: int, j: int) -> float:
        return self.dur_min[i][j]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def build_haversine_distance_matrix(nodes: List[Node]) -> List[List[float]]:
    n = len(nodes)
    d = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            dij = haversine_km(nodes[i].lat, nodes[i].lon, nodes[j].lat, nodes[j].lon)
            d[i][j] = dij
            d[j][i] = dij

    return d


def build_duration_matrix_from_distance(dist_km: List[List[float]], speed_kmh: float) -> List[List[float]]:
    n = len(dist_km)
    dur = [[0.0] * n for _ in range(n)]
    if speed_kmh <= 0:
        raise ValueError("speed_kmh debe ser mayor que 0.")
    for i in range(n):
        for j in range(n):
            dur[i][j] = (dist_km[i][j] / speed_kmh) * 60.0
    return dur


def validate_square_matrix(matrix: List[List[float]], n: int, name: str) -> None:
    if len(matrix) != n:
        raise ValueError(f"La matriz '{name}' debe tener {n} filas.")
    for idx, row in enumerate(matrix):
        if len(row) != n:
            raise ValueError(f"La fila {idx} de la matriz '{name}' debe tener {n} columnas.")


def load_matrices_from_json(matrix_json_path: str) -> Tuple[List[List[float]], List[List[float]]]:
    with open(matrix_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "distance_matrix_km" not in data:
        raise ValueError("El JSON no contiene 'distance_matrix_km'.")
    if "duration_matrix_min" not in data:
        raise ValueError("El JSON no contiene 'duration_matrix_min'.")

    return data["distance_matrix_km"], data["duration_matrix_min"]


def load_problem_from_csv(
    csv_path: str,
    capacity_kg: float,
    max_vehicles: Optional[int],
    speed_kmh: float,
    matrix_json_path: Optional[str] = None,
    traffic_factor: float = 1.0,
    service_factor: float = 1.0,
    service_extra: int = 0
) -> CVRPProblem:
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    rows.sort(key=lambda x: int(x["id"]))

    nodes: List[Node] = []
    for r in rows:
        base_service = int(r["service_time"])
        is_store = str(r["node_type"]).lower() == "store"

        if is_store:
            if service_factor <= 0:
                raise ValueError("service_factor debe ser > 0.")
            service_eff = int(round(base_service * float(service_factor) + int(service_extra)))
        else:
            service_eff = base_service  # depot no se altera

        nodes.append(Node(
            id=int(r["id"]),
            name=str(r["name"]),
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            demand_bultos=int(r["demand"]),
            tw_start=int(r["tw_start"]),
            tw_end=int(r["tw_end"]),
            service_time=service_eff,   # <- IMPORTANTE: aquí va service_eff
            node_type=str(r["node_type"]),
        ))

    if not nodes or nodes[0].id != 0:
        raise ValueError("El CSV debe incluir el depot con id=0.")

    dist_km = None
    dur_min = None

    if matrix_json_path is not None:
        dist_km, dur_min = load_matrices_from_json(matrix_json_path)

        if traffic_factor <= 0:
            raise ValueError("traffic_factor debe ser mayor que 0.")

        dur_min = [[v * traffic_factor for v in row] for row in dur_min]

    return CVRPProblem(
        nodes=nodes,
        capacity_kg=capacity_kg,
        max_vehicles=max_vehicles,
        speed_kmh=speed_kmh,
        dist_km=dist_km,
        dur_min=dur_min
    )