# GA-ACO Hybrid for CVRP/VRPTW — Arteaga-Saltillo

Implementación y evaluación comparativa de tres metaheurísticas (GA, ACO e Híbrido GA→ACO)
aplicadas a la distribución de mercancía desde un CEDIS a tiendas OXXO en la zona
Arteaga-Saltillo, Coahuila, México.

> **Tesis de Licenciatura — Ingeniería en Sistemas Computacionales**

---

## Contenido

- [Descripción del problema](#descripción-del-problema)
- [Arquitectura del sistema](#arquitectura-del-sistema)
- [Requisitos e instalación](#requisitos-e-instalación)
- [Uso rápido](#uso-rápido)
- [Dashboard web local](#dashboard-web-local)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Escenarios experimentales](#escenarios-experimentales)
- [Scripts auxiliares](#scripts-auxiliares)
- [Módulos principales](#módulos-principales)
- [Función objetivo](#función-objetivo)
- [Resultados y reproducibilidad](#resultados-y-reproducibilidad)
- [Consideraciones de seguridad](#consideraciones-de-seguridad)
- [Limitaciones](#limitaciones)
- [Troubleshooting](#troubleshooting)
- [Licencia](#licencia)

---

## Descripción del problema

Se resuelve una variante del **CVRP/VRPTW** (Capacitated Vehicle Routing Problem with
Time Windows) sobre una instancia real de 9 nodos (1 CEDIS + 8 tiendas OXXO) en la zona
Arteaga-Saltillo.

| Parámetro             | Valor               |
|-----------------------|---------------------|
| Nodos totales         | 9 (1 CEDIS + 8 tiendas) |
| Peso por bulto        | 7 kg                |
| Capacidad del vehículo| 15 000 kg           |
| Máximo de vehículos   | 1                   |
| Velocidad base        | 35 km/h (respaldo)  |
| Matriz vial           | OpenRouteService (real) |
| Corridas por benchmark| 10 000              |

**Algoritmos evaluados:**

| Algoritmo     | Descripción                                           |
|---------------|-------------------------------------------------------|
| GA            | Algoritmo Genético con OX-crossover y mutaciones mixtas |
| ACO           | Colonia de Hormigas con feromonas y heurística de distancia |
| Híbrido GA→ACO| GA inicializa feromonas; ACO refina la solución        |

---

## Arquitectura del sistema

```text
CSV de nodos (data/)
    ↓
load_problem_from_csv()   ← traffic_factor, service_extra
    ↓
CVRPProblem               ← nodos, matrices, capacidad
    ↓
Solver (GA / ACO / Hybrid)
    ↓
evaluate_routes_vrptw_light()
    ↓
EvalMetrics  →  JSON/CSV de salida (results/)
    ↓
Dashboard Streamlit (dashboard.py) ← solo lectura, solo localhost
```

---

## Requisitos e instalación

### Python

Python 3.11 o superior recomendado (probado en 3.14).

### Dependencias

```powershell
pip install -r requirements.txt
```

El núcleo del solver (`app.py`, `src/`) no requiere dependencias externas.
El dashboard y los scripts de análisis requieren los paquetes listados en `requirements.txt`.

### API key de OpenRouteService (opcional)

Solo necesaria para regenerar `data/matriz_real.json`. La matriz ya está incluida
en el repositorio.

```powershell
$env:ORS_API_KEY = "TU_API_KEY_AQUI"
python build_matrix_ors.py --csv data/dataset_artegasaltillo.csv --out data/matriz_real.json
```

---

## Uso rápido

### Corrida individual

```powershell
python app.py run `
  --data data/dataset_artegasaltillo.csv `
  --matrix-json data/matriz_real.json `
  --solver hybrid `
  --capacity-kg 15000 `
  --max-vehicles 1
```

### Benchmark (múltiples corridas)

```powershell
python app.py benchmark `
  --data data/dataset_artegasaltillo.csv `
  --matrix-json data/matriz_real.json `
  --solver ga `
  --runs 10000 `
  --capacity-kg 15000 `
  --max-vehicles 1 `
  --traffic-factor 1.0 `
  --service-extra 0 `
  --seed 1 `
  --out-dir results/scenario1_base
```

---

## Dashboard web local

El dashboard visualiza todos los resultados de benchmark de forma interactiva.

### Paso 1 — Generar tabla maestra

```powershell
python consolidate_results.py
```

Esto crea `assets/master_benchmarks.csv` con todos los benchmarks consolidados.

### Paso 2 — Iniciar el dashboard

```powershell
streamlit run dashboard.py --server.address=localhost --server.port=8501
```

Abre tu navegador en: [http://localhost:8501](http://localhost:8501)

### Paso 3 (opcional) — Generar figuras estáticas

```powershell
python generate_figures.py
```

Las figuras se guardan en `assets/figures/*.png`.

### Paso 4 (opcional) — Generar rutas óptimas

```powershell
python generate_best_routes.py
```

Las rutas se guardan en `assets/routes/best_route_<escenario>_<solver>.json`
y se visualizan en el tab de Rutas del dashboard.

---

## Estructura del proyecto

```
TESIS/
├── app.py                      # CLI principal: run / benchmark
├── build_matrix_ors.py         # Genera la matriz vial desde ORS
├── consolidate_results.py      # Consolida benchmarks → master_benchmarks.csv
├── dashboard.py                # Dashboard Streamlit (localhost)
├── generate_figures.py         # Genera figuras PNG para defensa/tesis
├── generate_best_routes.py     # Ejecuta solvers y guarda mejores rutas
├── monitor_resources.py        # Registra CPU/RAM durante benchmarks
├── requirements.txt
│
├── data/
│   ├── dataset_artegasaltillo.csv   # Nodos: coordenadas, demanda, TW
│   ├── matriz_real.json             # Matriz vial real (ORS)
│   └── config_cvrp_saltillo.json    # Config de referencia
│
├── results/                         # Benchmarks JSON por escenario
│   ├── *.json                       # Corridas en raíz (escenario base/hora pico)
│   ├── scenario3_congestion/        # Tienda congestionada (ACO)
│   ├── scenario3_congestion_tienda/ # Variante congestión tienda (ACO)
│   └── scenario4_estres/            # Escenario de estrés (GA · ACO · Híbrido)
│
├── src/
│   ├── __init__.py
│   ├── problem.py               # CVRPProblem, Node, matrices
│   ├── evaluation.py            # Función objetivo, EvalMetrics
│   └── solvers/
│       ├── ga.py                # Algoritmo Genético
│       ├── aco.py               # Colonia de Hormigas
│       └── hybrid.py            # Híbrido GA→ACO
│
└── assets/                      # Generado por los scripts auxiliares
    ├── master_benchmarks.csv    # Tabla maestra (consolidate_results.py)
    ├── resource_log.csv         # Bitácora de recursos (monitor_resources.py)
    ├── figures/                 # Figuras PNG (generate_figures.py)
    └── routes/                  # Rutas óptimas JSON (generate_best_routes.py)
```

---

## Escenarios experimentales

| ID | Nombre               | traffic_factor | service_extra | Descripción                       |
|----|----------------------|----------------|---------------|-----------------------------------|
| 1  | Base                 | 1.0            | 0 min         | Condiciones operativas normales   |
| 2  | Hora Pico            | 2.0            | 0 min         | Tiempos de tránsito duplicados    |
| 3  | Tienda Congestionada | 1.0            | 15 min        | +15 min de servicio por tienda    |
| 4  | Estrés               | 4.0            | 0 min         | Tránsito ×4 — alta congestión     |
| 5  | Estrés Total         | 10.0           | 0 min         | Prueba límite — inviable con 1 vehículo |

### Comandos por escenario (los 3 algoritmos)

**Escenario 1 — Base:**

```powershell
foreach ($s in @("ga","aco","hybrid")) {
  python app.py benchmark --data data/dataset_artegasaltillo.csv `
    --matrix-json data/matriz_real.json --solver $s --runs 10000 `
    --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 `
    --service-extra 0 --seed 1 --out-dir results/scenario1_base
}
```

**Escenario 4 — Estrés:**

```powershell
foreach ($s in @("ga","aco","hybrid")) {
  python app.py benchmark --data data/dataset_artegasaltillo.csv `
    --matrix-json data/matriz_real.json --solver $s --runs 10000 `
    --capacity-kg 15000 --max-vehicles 1 --traffic-factor 4.0 `
    --service-extra 0 --seed 1 --out-dir results/scenario4_estres
}
```

---

## Scripts auxiliares

| Script                    | Descripción                                          | Salida                                   |
|---------------------------|------------------------------------------------------|------------------------------------------|
| `consolidate_results.py`  | Consolida todos los JSON en tabla maestra            | `assets/master_benchmarks.csv`           |
| `dashboard.py`            | Dashboard web interactivo                            | `http://localhost:8501`                  |
| `generate_figures.py`     | Genera 12 figuras PNG de alta resolución             | `assets/figures/*.png`                   |
| `generate_best_routes.py` | Ejecuta solvers y guarda mejores rutas               | `assets/routes/*.json`                   |
| `monitor_resources.py`    | Registra CPU/RAM a intervalos regulares              | `assets/resource_log.csv`                |
| `build_matrix_ors.py`     | Genera matriz vial real desde OpenRouteService       | `data/matriz_real.json`                  |

---

## Módulos principales

### `src/problem.py`

- `Node` — nodo de la red (CEDIS o tienda): coordenadas, demanda, TW, tiempo de servicio
- `CVRPProblem` — instancia completa: nodos, matrices, capacidad, velocidad
- `load_problem_from_csv()` — carga datos, aplica `traffic_factor` y `service_extra`

### `src/evaluation.py`

- `EvalMetrics` — métricas de evaluación: objetivo, km, tardanza, espera, tiempo de ruta
- `evaluate_routes_vrptw_light()` — función objetivo con penalizaciones VRPTW

### `src/solvers/ga.py`

- `GASolver` / `GAConfig` — GA con selección por torneo, OX-crossover, mutaciones mixtas
- Mutaciones: `swap`, `invert`, `reinsert`

### `src/solvers/aco.py`

- `ACOSolver` / `ACOConfig` — ACO con feromonas, heurística de distancia, evaporación

### `src/solvers/hybrid.py`

- `HybridGAACOSolver` — GA resuelve primero; su mejor ruta inicializa las feromonas de ACO

---

## Función objetivo

```text
f(x) = total_km
      + 200  × late_minutes          (penalización por tardanza)
      + 0.5  × capacity_violation_kg (penalización por sobrecarga)
      + 5000 × vehicles_extra        (penalización por vehículos extra)
```

En escenarios sin tardanza ni violaciones: `f ≈ distancia total recorrida`.

---

## Resultados y reproducibilidad

Todos los benchmarks incluyen:

- Semilla aleatoria incremental por corrida (`seed = base_seed + run`)
- Estadísticas completas: media, σ, mínimo, máximo por métrica
- Detalle de las 10 000 corridas en `runs_detail`

Para reproducir exactamente los resultados publicados en la tesis:

```powershell
python app.py benchmark `
  --data data/dataset_artegasaltillo.csv `
  --matrix-json data/matriz_real.json `
  --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 `
  --traffic-factor 1.0 --service-extra 0 --seed 1 `
  --out-dir results/scenario1_base
```

Los archivos JSON en `results/` son la fuente primaria de verdad.
`assets/master_benchmarks.csv` es un artefacto derivado regenerable.

---

## Consideraciones de seguridad

Este proyecto fue diseñado para uso local con las siguientes prácticas:

- **Sin credenciales en código.** La API key de ORS se lee exclusivamente de la
  variable de entorno `ORS_API_KEY`. No se almacena en ningún archivo del proyecto.
- **Dashboard solo localhost.** Ejecutar siempre con `--server.address=localhost`
  para evitar exponer el dashboard en la red.
- **Sin ejecución de código arbitrario.** El dashboard solo lee archivos de
  directorios conocidos del proyecto; no evalúa ni ejecuta código de entrada del usuario.
- **Sin path traversal.** Todos los accesos a archivos usan rutas absolutas relativas
  a `Path(__file__).parent` y validan que el archivo esté dentro de `results/`.
- **Manejo seguro de errores.** Las excepciones de lectura de archivos se capturan
  y registran sin exponer trazas completas al usuario del dashboard.
- **Dependencias mínimas.** `requirements.txt` lista solo los paquetes necesarios
  con versiones mínimas verificadas.
- **`.gitignore` incluye `.env`** para evitar que variables de entorno se publiquen
  accidentalmente en el repositorio.

---

## Limitaciones

- La instancia es pequeña (8 tiendas); los resultados son válidos para este caso de estudio.
- Un solo vehículo: en escenarios de estrés extremo (`traffic_factor ≥ 4`), la operación
  se vuelve inviable — el objetivo es dominado por la penalización de tardanza.
- Los benchmarks en `results/` (raíz) no almacenan `traffic_factor` ni `service_extra`;
  el escenario se infiere estadísticamente. Los archivos en subcarpetas nombradas
  (`scenario3_*/`, `scenario4_*/`) sí tienen etiqueta explícita.
- No se modela multiobjetivo explícito (distancia + tiempo como objetivos separados).
- No se incluyen bloqueos probabilísticos tipo Tecnovalores (considerados trabajo futuro).

---

## Troubleshooting

| Problema | Causa probable | Solución |
| --- | --- | --- |
| `ModuleNotFoundError: src` | Ejecutar fuera de `TESIS/` | Ejecutar desde la raíz del proyecto |
| `KeyError: ORS_API_KEY` | Variable de entorno no definida | `$env:ORS_API_KEY = "TU_KEY"` |
| Dashboard sin datos | `master_benchmarks.csv` no existe | `python consolidate_results.py` |
| `streamlit: command not found` | Streamlit no instalado | `pip install streamlit` |
| `psutil` no disponible | Paquete no instalado | `pip install psutil` |
| Gráficas vacías en sensibilidad | Pocos valores de `traffic_factor` | Generar benchmarks para más escenarios |
| Figuras no se generan | `matplotlib`/`seaborn` ausentes | `pip install matplotlib seaborn` |

---

## Licencia

Véase el archivo [LICENSE](LICENSE) incluido en el repositorio.

---

*Proyecto desarrollado para tesis de licenciatura — Ingeniería en Sistemas Computacionales.*
