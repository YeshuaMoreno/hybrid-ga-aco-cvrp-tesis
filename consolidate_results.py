"""
consolidate_results.py
Consolida todos los archivos JSON de benchmark en assets/master_benchmarks.csv.

Prioridad de etiquetado de escenario:
  1. Campos explícitos en el JSON (scenario_name + traffic_factor + service_extra)
     → label_source = "explicit"
  2. Nombre de subcarpeta reconocida (scenario1_base, scenario2_hora_pico, etc.)
     → label_source = "folder"
  3. Inferencia estadística desde route_time_mean, late_mean, wait_mean
     → label_source = "inferred"

Los benchmarks generados con app.py ≥ parche-2026 incluyen campos explícitos.
Los benchmarks anteriores usan carpeta o inferencia.

Uso:
    python consolidate_results.py
"""

import csv
import json
from collections import Counter
from pathlib import Path

BASE        = Path(__file__).parent
RESULTS_DIR = BASE / "results"
ASSETS_DIR  = BASE / "assets"
OUTPUT_CSV  = ASSETS_DIR / "master_benchmarks.csv"

# Mapa de nombres normalizados de escenario
SCENARIO_ALIASES: dict[str, str] = {
    "base":                  "Base",
    "Base":                  "Base",
    "hora pico":             "Hora Pico",
    "Hora Pico":             "Hora Pico",
    "tienda congestionada":  "Tienda Congestionada",
    "Tienda Congestionada":  "Tienda Congestionada",
    "congestion tienda":     "Tienda Congestionada",
    "estres":                "Estrés",
    "Estres":                "Estrés",
    "estrés":                "Estrés",
    "Estrés":                "Estrés",
    "estres total":          "Estrés Total",
    "Estres Total":          "Estrés Total",
    "estrés total":          "Estrés Total",
    "Estrés Total":          "Estrés Total",
    "estres sin tardanza":   "Estrés (sin tardanza)",
    "Estrés (sin tardanza)": "Estrés (sin tardanza)",
}

FIELDNAMES = [
    "file",
    "scenario",
    "traffic_factor",
    "service_extra",
    "label_source",       # explicit | folder | inferred
    "solver",
    "runs",
    "seed_base",
    "capacity_kg",
    "max_vehicles",
    "speed_kmh",
    "matrix_json",
    "objective_mean",
    "objective_stdev",
    "objective_best",
    "objective_worst",
    "km_mean",
    "km_stdev",
    "late_mean",
    "late_stdev",
    "wait_mean",
    "wait_stdev",
    "route_time_mean",
    "route_time_stdev",
    "runtime_mean",
    "runtime_stdev",
    "runtime_best",
    "runtime_worst",
]


def _normalize_scenario(raw: str) -> str:
    key = raw.strip()
    return SCENARIO_ALIASES.get(key, key)


def _label_from_explicit(data: dict) -> tuple[str, float, int, str] | None:
    """
    Devuelve (scenario, tf, se, 'explicit') si el JSON tiene los tres campos
    explícitos y el scenario_name no está vacío.
    Retorna None si faltan campos.
    """
    sc_name = data.get("scenario_name", "")
    tf      = data.get("traffic_factor")
    se      = data.get("service_extra")

    if not sc_name or tf is None or se is None:
        return None

    scenario = _normalize_scenario(sc_name)
    return scenario, float(tf), int(se), "explicit"


def _label_from_folder(json_path: Path) -> tuple[str, float, int, str] | None:
    """
    Devuelve (scenario, tf, se, 'folder') si la ruta contiene un nombre
    de subcarpeta reconocido.
    """
    p = str(json_path).replace("\\", "/").lower()

    if "scenario5" in p or "estres_total" in p:
        return "Estrés Total", 10.0, 0, "folder"
    if "scenario4" in p or "scenario4_estres" in p:
        return None   # necesita stats para distinguir con/sin tardanza
    if "scenario3_congestion_tienda" in p:
        return "Tienda Congestionada", 1.0, 15, "folder"
    if "scenario3_congestion" in p:
        return "Tienda Congestionada", 1.0, 15, "folder"
    if "scenario3" in p:
        return "Tienda Congestionada", 1.0, 15, "folder"
    if "scenario2_hora_pico" in p or "scenario2" in p:
        return "Hora Pico", 2.0, 0, "folder"
    if "scenario1_base" in p or "scenario1" in p:
        return "Base", 1.0, 0, "folder"

    return None


def _label_from_stats(json_path: Path, stats: dict) -> tuple[str, float, int, str]:
    """
    Inferencia estadística como último recurso.
    """
    p     = str(json_path).replace("\\", "/").lower()
    rt    = stats.get("route_time_mean", 0.0)
    late  = stats.get("late_mean", 0.0)
    wait  = stats.get("wait_mean", 0.0)

    # scenario4 necesita stats para distinguir con/sin tardanza
    if "scenario4" in p:
        if late > 50.0:
            return "Estrés", 4.0, 0, "folder"
        return "Estrés (sin tardanza)", 4.0, 0, "folder"

    # Archivos en raíz → inferencia estadística
    if late > 300.0:
        return "Estrés Total", 10.0, 0, "inferred"
    if late > 50.0:
        return "Estrés", 4.0, 0, "inferred"

    # Discriminar Base vs Hora Pico vs Tienda Congestionada
    if rt < 492.0:
        return "Base", 1.0, 0, "inferred"
    if rt < 548.0:
        # wait bajo + ruta más larga → servicio extra (tienda congestionada)
        # wait más alto → viaje más rápido llegado tarde → hora pico (tf=2)
        if wait < 165.0:
            return "Tienda Congestionada", 1.0, 15, "inferred"
        return "Hora Pico", 2.0, 0, "inferred"
    if rt < 700.0:
        return "Estrés (sin tardanza)", 4.0, 0, "inferred"
    return "Estrés", 4.0, 0, "inferred"


def _resolve_label(
    json_path: Path,
    data: dict,
    stats: dict,
) -> tuple[str, float, int, str]:
    # Prioridad 1: campos explícitos en el JSON
    explicit = _label_from_explicit(data)
    if explicit is not None:
        return explicit

    # Prioridad 2: nombre de subcarpeta reconocida
    folder = _label_from_folder(json_path)
    if folder is not None:
        return folder

    # Prioridad 3: inferencia estadística
    return _label_from_stats(json_path, stats)


def _safe(value, decimals: int = 4) -> float:
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return 0.0


def consolidate() -> list[dict]:
    rows = []
    json_files = sorted(RESULTS_DIR.rglob("*.json"))

    if not json_files:
        print(f"[AVISO] No se encontraron archivos JSON en: {RESULTS_DIR}")
        return rows

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[SKIP] {jf.name}: {exc}")
            continue

        if "stats" not in data or "solver" not in data:
            continue

        stats = data["stats"]
        scenario, tf, se, source = _resolve_label(jf, data, stats)

        rows.append({
            "file":             str(jf.relative_to(BASE)).replace("\\", "/"),
            "scenario":         scenario,
            "traffic_factor":   tf,
            "service_extra":    se,
            "label_source":     source,
            "solver":           data.get("solver", ""),
            "runs":             int(data.get("runs", 0)),
            "seed_base":        int(data.get("seed_base", 0)),
            "capacity_kg":      _safe(data.get("capacity_kg", 0), 1),
            "max_vehicles":     data.get("max_vehicles", 0),
            "speed_kmh":        _safe(data.get("speed_kmh", 0), 1),
            "matrix_json":      data.get("matrix_json", ""),
            "objective_mean":   _safe(stats.get("objective_mean", 0)),
            "objective_stdev":  _safe(stats.get("objective_stdev", 0)),
            "objective_best":   _safe(stats.get("objective_best", 0)),
            "objective_worst":  _safe(stats.get("objective_worst", 0)),
            "km_mean":          _safe(stats.get("km_mean", 0)),
            "km_stdev":         _safe(stats.get("km_stdev", 0)),
            "late_mean":        _safe(stats.get("late_mean", 0)),
            "late_stdev":       _safe(stats.get("late_stdev", 0)),
            "wait_mean":        _safe(stats.get("wait_mean", 0)),
            "wait_stdev":       _safe(stats.get("wait_stdev", 0)),
            "route_time_mean":  _safe(stats.get("route_time_mean", 0)),
            "route_time_stdev": _safe(stats.get("route_time_stdev", 0)),
            "runtime_mean":     _safe(stats.get("runtime_mean", 0), 6),
            "runtime_stdev":    _safe(stats.get("runtime_stdev", 0), 6),
            "runtime_best":     _safe(stats.get("runtime_best", 0), 6),
            "runtime_worst":    _safe(stats.get("runtime_worst", 0), 6),
        })

    return rows


def _coverage_report(rows: list[dict]) -> None:
    """Imprime qué combinaciones escenario × algoritmo están presentes."""
    EXPECTED_SCENARIOS = [
        "Base", "Hora Pico", "Tienda Congestionada", "Estrés", "Estrés Total",
    ]
    EXPECTED_SOLVERS = ["ga", "aco", "hybrid"]

    print("\n══════════════════════════════════════════════════════")
    print(" COBERTURA DE BENCHMARKS")
    print("══════════════════════════════════════════════════════")
    print(f" {'Escenario':<28} {'GA':^12} {'ACO':^12} {'Hybrid':^12}")
    print(" " + "─" * 66)

    for sc in EXPECTED_SCENARIOS:
        row_data = {sv: [] for sv in EXPECTED_SOLVERS}
        for r in rows:
            if r["scenario"] == sc:
                row_data[r["solver"]].append(r["label_source"])

        def _cell(sv):
            if not row_data[sv]:
                return "FALTA"
            sources = set(row_data[sv])
            tag = "ok" if sources == {"explicit"} else ("folder" if "inferred" not in sources else "infer")
            return tag

        print(f" {sc:<28} {_cell('ga'):^12} {_cell('aco'):^12} {_cell('hybrid'):^12}")

    print(" " + "─" * 66)
    print(" Leyenda: ok=explícito · folder=por carpeta · infer=inferido · FALTA=sin datos")
    print("══════════════════════════════════════════════════════\n")

    # Combinaciones faltantes
    missing = []
    present = {(r["scenario"], r["solver"]) for r in rows}
    for sc in EXPECTED_SCENARIOS:
        for sv in EXPECTED_SOLVERS:
            if (sc, sv) not in present:
                missing.append((sc, sv))

    if missing:
        print(" COMBINACIONES FALTANTES (sin ningún benchmark):")
        for sc, sv in missing:
            print(f"   · {sc} × {sv.upper()}")
    else:
        print(" Cobertura completa: todas las combinaciones tienen al menos un benchmark.")
    print()

    # Combinaciones solo inferidas
    inferred_only = []
    for sc in EXPECTED_SCENARIOS:
        for sv in EXPECTED_SOLVERS:
            entries = [r for r in rows if r["scenario"] == sc and r["solver"] == sv]
            if entries and all(r["label_source"] == "inferred" for r in entries):
                inferred_only.append((sc, sv))

    if inferred_only:
        print(" COMBINACIONES SOLO INFERIDAS (sin metadata explícita):")
        for sc, sv in inferred_only:
            print(f"   · {sc} × {sv.upper()}")
        print()


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    rows = consolidate()

    if not rows:
        print("Sin datos para consolidar.")
        return

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    sources = Counter(r["label_source"] for r in rows)
    print(f"\n Tabla maestra: {OUTPUT_CSV}")
    print(f" Total entradas : {len(rows)}")
    print(f" Fuentes        : {dict(sources)}")

    _coverage_report(rows)


if __name__ == "__main__":
    main()
