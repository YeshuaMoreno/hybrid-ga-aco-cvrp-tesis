# Documentación técnica - Proyecto TESIS GA-ACO

## 1. Resumen técnico
El sistema resuelve un problema de ruteo de vehículos con capacidad y ventanas de tiempo mediante tres metaheurísticas:

- Algoritmo Genético
- Colonia de Hormigas
- Híbrido GA→ACO

Trabaja sobre un conjunto de nodos cargado desde CSV y una matriz de distancias/tiempos cargada desde JSON.

---

## 2. Flujo general del sistema
```text
CSV de nodos
   ↓
load_problem_from_csv()
   ↓
CVRPProblem(nodes, capacity, matrices, factores)
   ↓
Solver (GA / ACO / Hybrid)
   ↓
evaluate_routes_vrptw_light()
   ↓
Métricas + JSON/CSV de salida
```

---

## 3. Módulos

### 3.1 `app.py`
Punto de entrada del sistema.

Funciones principales:
- `cmd_run(args)` → ejecuta una corrida individual
- `cmd_benchmark(args)` → ejecuta múltiples corridas y resume estadísticas
- `build_parser()` → define la CLI
- `build_solver(name, args)` → construye GA, ACO o Hybrid según argumentos

### 3.2 `src/problem.py`
Modela los datos del problema.

Clases:
- `Node`
- `CVRPProblem`

Responsabilidades:
- leer CSV de nodos
- leer matriz JSON
- aplicar `traffic_factor`
- aplicar `service_factor` y `service_extra`
- construir problema listo para evaluación

### 3.3 `src/evaluation.py`
Evalúa una solución.

Componentes:
- `EvalMetrics`
- `decode_split_by_capacity_kg()`
- `evaluate_routes_vrptw_light()`

Responsabilidades:
- dividir la permutación en rutas por capacidad
- calcular distancia, espera, retraso y tiempo total
- calcular la función objetivo

### 3.4 `src/solvers/ga.py`
Implementa el Algoritmo Genético.

Incluye:
- población inicial aleatoria
- selección por torneo
- crossover OX
- mutación (`swap`, `invert`, `reinsert`)
- elitismo

### 3.5 `src/solvers/aco.py`
Implementa Colonia de Hormigas.

Incluye:
- feromonas
- heurística basada en distancia
- construcción probabilística
- evaporación y depósito

### 3.6 `src/solvers/hybrid.py`
Implementa el híbrido GA→ACO.

Flujo:
1. resolver con GA
2. usar la mejor ruta como refuerzo inicial de feromonas
3. ejecutar ACO
4. devolver la mejor solución entre ambas fases

### 3.7 `build_matrix_ors.py`
Genera `matriz_real.json` desde openrouteservice.

Entrada:
- CSV con lat/lon de nodos
- ORS API key

Salida:
- `distance_matrix_km`
- `duration_matrix_min`

---

## 4. Modelo de datos

### 4.1 CSV de nodos
Campos esperados:
- `id`
- `name`
- `lat`
- `lon`
- `demand`
- `tw_start`
- `tw_end`
- `service_time`
- `node_type`

### 4.2 JSON de matriz
Campos esperados:
- `distance_matrix_km`
- `duration_matrix_min`

Ambas matrices deben ser NxN.

---

## 5. Función objetivo
La evaluación usa:

```text
objective = total_km
          + late_penalty_per_min * late_minutes
          + cap_penalty_per_kg * capacity_violation_kg
          + vehicle_penalty * vehicles_extra
```

Interpretación:
- si no hay tardanza ni exceso de capacidad, el objetivo ≈ distancia
- si hay tardanza, el objetivo crece fuertemente

---

## 6. Escenarios operativos

### Escenario base
- `traffic_factor=1.0`
- `service_extra=0`

### Hora pico
- `traffic_factor=2.0`
- `service_extra=0`

### Tienda congestionada
- `traffic_factor=1.0`
- `service_extra=15`

### Estrés
- `traffic_factor=4.0`
- `service_extra=0`

### Estrés total
- `traffic_factor=10.0`
- `service_extra=0`

---

## 7. Comandos útiles
### Corrida individual
```powershell
python app.py run --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --capacity-kg 15000 --max-vehicles 1
```

### Benchmark
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 0 --seed 1
```

---

## 8. Resultados esperados por tipo de escenario
- **Base:** menor tiempo total, mayor espera, sin tardanza
- **Hora pico:** menor espera, mayor tiempo total, todavía sin tardanza
- **Tienda congestionada:** menor espera, mayor tiempo por servicio
- **Estrés:** espera casi nula, tiempo alto
- **Estrés total:** tardanza elevada y objetivo dominado por penalización

---

## 9. Limitaciones actuales
- objetivo dominado por distancia mientras `late=0`
- no hay multiobjetivo explícito distancia + tiempo
- no se modelan aún bloqueos probabilísticos tipo Tecnovalores
- el caso de estudio todavía es pequeño (8 tiendas)

---

## 10. Recomendaciones de mantenimiento
- guardar siempre benchmarks por escenario en carpetas separadas
- no sobrescribir `matriz_real.json` sin respaldo
- documentar en el JSON de benchmark los factores de tráfico y servicio
- congelar una versión del código antes de generar tablas finales de tesis
