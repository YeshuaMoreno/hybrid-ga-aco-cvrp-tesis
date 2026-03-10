import argparse
import csv
import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"


def read_nodes(csv_path: str):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    rows.sort(key=lambda x: int(x["id"]))

    nodes = []
    for r in rows:
        nodes.append({
            "id": int(r["id"]),
            "name": str(r["name"]),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "node_type": str(r["node_type"]),
        })
    return nodes


def build_request_body(nodes):
    # ORS usa [lon, lat]
    locations = [[n["lon"], n["lat"]] for n in nodes]

    return {
        "locations": locations,
        "metrics": ["distance", "duration"],
        "units": "km",
        # opcional, pero limpio:
        "resolve_locations": False,
    }


def request_matrix_ors(api_key: str, body: dict):
    payload = json.dumps(body).encode("utf-8")

    req = Request(
        ORS_MATRIX_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} al consultar ORS Matrix API:\n{detail}") from e
    except URLError as e:
        raise RuntimeError(f"Error de red al consultar ORS Matrix API: {e}") from e


def validate_and_extract_matrices(nodes, response_json):
    n = len(nodes)

    if "distances" not in response_json:
        raise RuntimeError(
            "La respuesta no contiene 'distances'. Respuesta:\n"
            + json.dumps(response_json, ensure_ascii=False, indent=2)[:2000]
        )
    if "durations" not in response_json:
        raise RuntimeError(
            "La respuesta no contiene 'durations'. Respuesta:\n"
            + json.dumps(response_json, ensure_ascii=False, indent=2)[:2000]
        )

    dist_km = response_json["distances"]
    dur_sec = response_json["durations"]

    if len(dist_km) != n or any(len(row) != n for row in dist_km):
        raise RuntimeError("La matriz de distancias no tiene tamaño NxN correcto.")
    if len(dur_sec) != n or any(len(row) != n for row in dur_sec):
        raise RuntimeError("La matriz de duraciones no tiene tamaño NxN correcto.")

    # ORS devuelve duration en segundos; la pasamos a minutos
    dur_min = []
    for row in dur_sec:
        dur_min.append([float(v) / 60.0 if v is not None else None for v in row])

    # Distancias ya van en km porque mandamos units=km
    dist_km = [
        [float(v) if v is not None else None for v in row]
        for row in dist_km
    ]

    # Validar que no haya celdas nulas
    bad = []
    for i in range(n):
        for j in range(n):
            if dist_km[i][j] is None or dur_min[i][j] is None:
                bad.append((i, j))

    if bad:
        raise RuntimeError(
            f"La matriz tiene valores nulos en {len(bad)} posiciones. "
            f"Ejemplos: {bad[:10]}"
        )

    return dist_km, dur_min


def save_matrix_json(out_path: str, nodes, distance_matrix_km, duration_matrix_min):
    data = {
        "meta": {
            "provider": "openrouteservice",
            "endpoint": "/v2/matrix/driving-car",
            "units": "km",
            "duration_units": "min",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "node_order": [
            {
                "index": i,
                "id": n["id"],
                "name": n["name"],
                "lat": n["lat"],
                "lon": n["lon"],
                "node_type": n["node_type"],
            }
            for i, n in enumerate(nodes)
        ],
        "distance_matrix_km": distance_matrix_km,
        "duration_matrix_min": duration_matrix_min,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Genera matriz vial real usando openrouteservice Matrix V2.")
    parser.add_argument("--csv", required=True, help="CSV de nodos (depot + tiendas).")
    parser.add_argument("--out", default="data/matriz_real.json", help="Ruta de salida del JSON.")
    args = parser.parse_args()

    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No encontré ORS_API_KEY en variables de entorno.\n"
            "En PowerShell usa:\n"
            "$env:ORS_API_KEY='TU_API_KEY'"
        )

    nodes = read_nodes(args.csv)
    body = build_request_body(nodes)

    print(f"Leyendo nodos desde: {args.csv}")
    print(f"Nodos detectados: {len(nodes)}")
    print("Consultando openrouteservice Matrix API...")

    response_json = request_matrix_ors(api_key, body)
    dist_km, dur_min = validate_and_extract_matrices(nodes, response_json)
    save_matrix_json(args.out, nodes, dist_km, dur_min)

    print(f"Matriz guardada en: {args.out}")
    print("Listo. Ya puedes correr app.py con --matrix-json.")


if __name__ == "__main__":
    main()