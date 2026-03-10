# TESIS - Hibridación GA-ACO para ruteo de tiendas OXXO en Saltillo

## Descripción
Este proyecto implementa una propuesta de tesis para resolver una variante simplificada del problema de ruteo de vehículos con capacidad y ventanas de tiempo (**CVRP/VRPTW ligero**) usando tres enfoques metaheurísticos:

- **Algoritmo Genético (GA)**
- **Colonia de Hormigas (ACO)**
- **Híbrido GA → ACO**

El caso de estudio se basa en un conjunto de tiendas OXXO ubicadas en la zona de Arteaga-Saltillo, utilizando:

- demanda en **bultos**
- conversión a **kilogramos**
- ventanas de tiempo
- tiempos de servicio
- matriz vial real obtenida con **openrouteservice**
- escenarios operativos como **hora pico**, **tienda congestionada** y **estrés extremo**

## Objetivo del proyecto
Comparar el desempeño de GA, ACO y un híbrido GA-ACO en términos de:

- distancia total recorrida
- tiempo total de ruta
- minutos de espera
- minutos de retraso
- estabilidad estadística en múltiples corridas

## Estructura del proyecto
```text
TESIS/
├── app.py                     # Punto de entrada CLI para run y benchmark
├── build_matrix_ors.py        # Genera matriz vial real desde openrouteservice
├── data/
│   ├── dataset_artegasaltillo.csv
│   └── matriz_real.json
├── results/                   # Resultados JSON/CSV de corridas y benchmarks
├── src/
│   ├── __init__.py
│   ├── problem.py             # Carga de datos, nodos, matrices, factores de tráfico/servicio
│   ├── evaluation.py          # Función objetivo, métricas y evaluación VRPTW ligera
│   └── solvers/
│       ├── __init__.py
│       ├── ga.py              # Algoritmo Genético
│       ├── aco.py             # Colonia de Hormigas
│       └── hybrid.py          # Híbrido GA→ACO
└── Tesis.docx                 # Documento principal de tesis
```

## Requisitos
- Python 3.11+ recomendado
- Dependencias estándar de Python
- API key de openrouteservice para construir la matriz vial real

## Variables y supuestos principales
- **Peso por bulto:** 7 kg
- **Capacidad del vehículo base:** 15,000 kg
- **Máximo de vehículos:** 1
- **Caso de estudio:** 1 CEDIS + 8 tiendas
- **Velocidad base de respaldo:** 35 km/h

## Escenarios evaluados
1. **Base realista**
   - `traffic_factor=1.0`
   - `service_extra=0`

2. **Hora pico**
   - `traffic_factor=2.0`
   - `service_extra=0`

3. **Tienda congestionada**
   - `traffic_factor=1.0`
   - `service_extra=15`

4. **Estrés**
   - `traffic_factor=4.0`
   - `service_extra=0`

5. **Estrés total**
   - `traffic_factor=10.0`
   - `service_extra=0`

## Cómo generar la matriz vial real
Primero exporta tu API key de ORS en PowerShell:

```powershell
$env:ORS_API_KEY="TU_API_KEY"
```

Luego genera la matriz:

```powershell
python build_matrix_ors.py --csv data/dataset_artegasaltillo.csv --out data/matriz_real.json
```

## Comandos principales
### 1) Ejecutar una corrida individual
```powershell
python app.py run --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --capacity-kg 15000 --max-vehicles 1
```

### 2) Ejecutar benchmark
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 0 --seed 1
```

### 3) Benchmark por escenario
#### Escenario base
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 0 --seed 1 --out-dir results/scenario1_base
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver aco --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 0 --seed 1 --out-dir results/scenario1_base
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver hybrid --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 0 --seed 1 --out-dir results/scenario1_base
```

#### Escenario hora pico
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 2.0 --service-extra 0 --seed 1 --out-dir results/scenario2_hora_pico
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver aco --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 2.0 --service-extra 0 --seed 1 --out-dir results/scenario2_hora_pico
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver hybrid --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 2.0 --service-extra 0 --seed 1 --out-dir results/scenario2_hora_pico
```

#### Escenario tienda congestionada
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 15 --seed 1 --out-dir results/scenario3_congestion
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver aco --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 15 --seed 1 --out-dir results/scenario3_congestion
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver hybrid --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 1.0 --service-extra 15 --seed 1 --out-dir results/scenario3_congestion
```

#### Escenario estrés
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 4.0 --service-extra 0 --seed 1 --out-dir results/scenario4_estres
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver aco --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 4.0 --service-extra 0 --seed 1 --out-dir results/scenario4_estres
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver hybrid --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 4.0 --service-extra 0 --seed 1 --out-dir results/scenario4_estres
```

#### Escenario estrés total
```powershell
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver ga --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 10.0 --service-extra 0 --seed 1 --out-dir results/scenario5_estres_total
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver aco --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 10.0 --service-extra 0 --seed 1 --out-dir results/scenario5_estres_total
python app.py benchmark --data data/dataset_artegasaltillo.csv --matrix-json data/matriz_real.json --solver hybrid --runs 10000 --capacity-kg 15000 --max-vehicles 1 --traffic-factor 10.0 --service-extra 0 --seed 1 --out-dir results/scenario5_estres_total
```

## Interpretación de métricas

- **objective**: valor de la función objetivo
- **total_km**: distancia total recorrida
- **late_minutes**: minutos de retraso por llegar después del cierre de ventana
- **wait_minutes**: minutos esperando por llegar antes de la apertura
- **route_time_minutes**: tiempo total de ruta (viaje + servicio + espera)
- **runtime_seconds**: tiempo de ejecución del algoritmo

## Hallazgos generales del proyecto
- **GA** y **Hybrid** obtienen los mejores resultados promedio en escenarios normales.
- **ACO** encuentra buenas soluciones en algunas corridas, pero con mayor variabilidad.
- En escenarios sin tardanza, el objetivo coincide casi por completo con la distancia.
- En escenarios extremos (`traffic=10.0`), la tardanza domina la función objetivo y el sistema se vuelve operacionalmente inviable con 1 vehículo.

## Estado actual
El proyecto ya cuenta con:
- implementación modular de GA, ACO e híbrido
- carga de datos desde CSV
- integración de matriz vial real ORS
- simulación de tráfico y congestión en tienda
- benchmarks de 10,000 corridas
- tablas comparativas integradas al documento de tesis

## Trabajo futuro
- incluir multiobjetivo (distancia + tiempo)
- considerar escenarios multi-vehículo
- agregar bloqueos temporales tipo Tecnovalores
- escalar a más tiendas y más días de operación

## Autor
Proyecto desarrollado para tesis de licenciatura en Ingeniería en Sistemas Computacionales.
