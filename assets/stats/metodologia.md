# Validacion estadistica de resultados experimentales

## Justificacion de la prueba no parametrica

Para determinar si las diferencias observadas entre los algoritmos (GA, ACO e Hibrido GA-ACO) son estadisticamente significativas, se empleo la prueba de **Mann-Whitney U** (tambien conocida como prueba de rango de Wilcoxon para muestras independientes).

### Por que no se asume normalidad

La prueba de Shapiro-Wilk aplicada a submuestras de 5,000 observaciones rechazo la hipotesis de normalidad en 11 de 15 combinaciones escenario-algoritmo (p < 0.05). Esto indica que las distribuciones de la funcion objetivo **no siguen una distribucion normal**, lo cual invalida el uso de pruebas parametricas como la prueba t de Student o ANOVA.

Las razones de la no-normalidad incluyen:

- Distribuciones multimodales o asimetricas en la funcion objetivo.
- Presencia de valores extremos generados por soluciones suboptimas en corridas con semillas desfavorables.
- La naturaleza estocastica de las metaheuristicas produce distribuciones que no se ajustan al modelo gaussiano.

### Configuracion de la prueba

- **Tamano de muestra**: n = 10,000 corridas independientes por algoritmo por escenario.
- **Nivel de significancia**: alpha = 0.05
- **Hipotesis nula (H0)**: Las distribuciones de ambos algoritmos son identicas.
- **Hipotesis alternativa (H1)**: Las distribuciones difieren significativamente (prueba bilateral).
- **Tamano del efecto**: Se reporta la correlacion de rango biserial (r = 1 - 2U / n1*n2), donde |r| < 0.1 es efecto negligible, 0.1-0.3 pequeno, 0.3-0.5 mediano y > 0.5 grande.

### Comparaciones realizadas

Se realizaron comparaciones por pares dentro de cada escenario (GA vs ACO, GA vs Hibrido GA-ACO, ACO vs Hibrido GA-ACO) para dos metricas: funcion objetivo y tiempo de ejecucion.

## Resultados de la prueba de Mann-Whitney U

### Base

| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |
|---|---|---|---|---|---|---|---|
| GA vs ACO | 63.4314 | 68.0298 | 63.4300 | 66.1800 | 0.00e+00 | 0.9993 | Si |
| GA vs Hibrido GA-ACO | 63.4314 | 63.4324 | 63.4300 | 63.4300 | 7.27e-08 | 0.0110 | Si |
| ACO vs Hibrido GA-ACO | 68.0298 | 63.4324 | 66.1800 | 63.4300 | 0.00e+00 | -0.9990 | Si |

### Hora Pico

| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |
|---|---|---|---|---|---|---|---|
| GA vs ACO | 63.4342 | 69.4273 | 63.4300 | 70.3300 | 0.00e+00 | 0.9985 | Si |
| GA vs Hibrido GA-ACO | 63.4342 | 63.4354 | 63.4300 | 63.4300 | 4.83e-05 | 0.0129 | Si |
| ACO vs Hibrido GA-ACO | 69.4273 | 63.4354 | 70.3300 | 63.4300 | 0.00e+00 | -0.9981 | Si |

### Tienda Congestionada

| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |
|---|---|---|---|---|---|---|---|
| GA vs ACO | 63.4366 | 69.4084 | 63.4300 | 70.4300 | 0.00e+00 | 0.9977 | Si |
| GA vs Hibrido GA-ACO | 63.4366 | 63.4373 | 63.4300 | 63.4300 | 0.0230 | 0.0086 | Si |
| ACO vs Hibrido GA-ACO | 69.4084 | 63.4373 | 70.4300 | 63.4300 | 0.00e+00 | -0.9975 | Si |

### Estres

| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |
|---|---|---|---|---|---|---|---|
| GA vs ACO | 63.5200 | 70.0889 | 63.5200 | 69.4500 | 0.00e+00 | 0.9770 | Si |
| GA vs Hibrido GA-ACO | 63.5200 | 63.5200 | 63.5200 | 63.5200 | 1.0000 | 0.0000 | No |
| ACO vs Hibrido GA-ACO | 70.0889 | 63.5200 | 69.4500 | 63.5200 | 0.00e+00 | -0.9770 | Si |

### Estres Total

| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |
|---|---|---|---|---|---|---|---|
| GA vs ACO | 71559.2900 | 73584.6217 | 71559.2900 | 71559.2900 | 0.00e+00 | 0.4762 | Si |
| GA vs Hibrido GA-ACO | 71559.2900 | 71559.2900 | 71559.2900 | 71559.2900 | 1.0000 | 0.0000 | No |
| ACO vs Hibrido GA-ACO | 73584.6217 | 71559.2900 | 71559.2900 | 71559.2900 | 0.00e+00 | -0.4762 | Si |

## Interpretacion general

De las 15 comparaciones por pares realizadas sobre la funcion objetivo, 13 resultaron estadisticamente significativas (p < 0.05). 

- **Base** — GA vs ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). GA obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = 0.9993).
- **Base** — GA vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 7.27e-08). GA obtiene valores menores de funcion objetivo. Tamano del efecto: negligible (r = 0.0110).
- **Base** — ACO vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). Hibrido GA-ACO obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = -0.9990).
- **Hora Pico** — GA vs ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). GA obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = 0.9985).
- **Hora Pico** — GA vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 4.83e-05). GA obtiene valores menores de funcion objetivo. Tamano del efecto: negligible (r = 0.0129).
- **Hora Pico** — ACO vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). Hibrido GA-ACO obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = -0.9981).
- **Tienda Congestionada** — GA vs ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). GA obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = 0.9977).
- **Tienda Congestionada** — GA vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 2.30e-02). GA obtiene valores menores de funcion objetivo. Tamano del efecto: negligible (r = 0.0086).
- **Tienda Congestionada** — ACO vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). Hibrido GA-ACO obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = -0.9975).
- **Estres** — GA vs ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). GA obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = 0.9770).
- **Estres** — ACO vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). Hibrido GA-ACO obtiene valores menores de funcion objetivo. Tamano del efecto: grande (r = -0.9770).
- **Estres Total** — GA vs ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). GA obtiene valores menores de funcion objetivo. Tamano del efecto: mediano (r = 0.4762).
- **Estres Total** — ACO vs Hibrido GA-ACO: Con un nivel de significancia de 0.05, la diferencia observada no se atribuye al azar (p = 0.00e+00). Hibrido GA-ACO obtiene valores menores de funcion objetivo. Tamano del efecto: mediano (r = -0.4762).

- **Estres** — GA vs Hibrido GA-ACO: No se encontro diferencia significativa (p = 1.0000). Los algoritmos son estadisticamente equivalentes en este escenario.
- **Estres Total** — GA vs Hibrido GA-ACO: No se encontro diferencia significativa (p = 1.0000). Los algoritmos son estadisticamente equivalentes en este escenario.

## Texto sugerido para la seccion de resultados

Para evaluar si las diferencias de desempeno entre los tres algoritmos son estadisticamente significativas, se aplico la prueba de Mann-Whitney U (Wilcoxon rank-sum) a las 10,000 corridas independientes de cada combinacion escenario-algoritmo. Se opto por esta prueba no parametrica porque la prueba de Shapiro-Wilk rechazo la hipotesis de normalidad en la mayoria de las distribuciones observadas (p < 0.05), invalidando el uso de pruebas parametricas como la t de Student.

Se utilizo un nivel de significancia alpha = 0.05 y se reporta la correlacion de rango biserial como medida del tamano del efecto. Los resultados muestran que 13 de 15 comparaciones por pares en la funcion objetivo presentan diferencias estadisticamente significativas, lo que permite concluir que las diferencias observadas entre los algoritmos no se atribuyen al azar, sino a diferencias reales en el desempeno de cada metaheuristica.
