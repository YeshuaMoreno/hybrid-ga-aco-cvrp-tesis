"""
stat_validation.py  —  Validacion estadistica formal para defensa de tesis
===========================================================================
Lee los 15 benchmarks formales (5 escenarios x 3 algoritmos, 10 000 corridas
cada uno) directamente del campo ``runs_detail`` de cada JSON.

Genera:
    assets/stats/                          carpeta con todas las figuras
        hist_{escenario}_{metrica}.png     histogramas de frecuencia
        box_{escenario}_{metrica}.png      boxplots comparativos
    assets/stats/wilcoxon_results.csv      tabla de p-valores y descriptivos
    assets/stats/metodologia.md            texto metodologico listo para tesis

Uso:
    pip install scipy matplotlib seaborn pandas numpy
    python stat_validation.py

No modifica la tesis final.  No modifica app.py.
Todos los datos salen de los JSON ya existentes en results/.
"""

from __future__ import annotations

import json
import warnings
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats as sp_stats

# ── Configuracion ────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent
RESULTS    = BASE / "results"
OUT_DIR    = BASE / "assets" / "stats"
ALPHA      = 0.05
N_RUNS     = 10_000

SOLVER_LABELS = {"ga": "GA", "aco": "ACO", "hybrid": "Hibrido GA-ACO"}
SOLVER_ORDER  = ["GA", "ACO", "Hibrido GA-ACO"]
SCENARIO_ORDER = [
    "Base", "Hora Pico", "Tienda Congestionada",
    "Estres", "Estres Total",
]
METRICS = [
    ("objective",        "Funcion objetivo"),
    ("total_km",         "Distancia total (km)"),
    ("runtime_seconds",  "Tiempo de ejecucion (s)"),
]
COMPARISON_METRICS = [
    ("objective",        "Funcion objetivo"),
    ("runtime_seconds",  "Tiempo de ejecucion (s)"),
]

COLORS = {"GA": "#1D4ED8", "ACO": "#B45309", "Hibrido GA-ACO": "#15803D"}

# ── Carga de datos ───────────────────────────────────────────────────────────

def _load_formal_benchmarks() -> pd.DataFrame:
    """
    Carga los 15 benchmarks formales (mayo-junio 2026) y devuelve un
    DataFrame con 150 000 filas (15 x 10 000).
    """
    rows: list[dict] = []
    json_files = sorted(RESULTS.rglob("*.json"))

    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        sc_name = data.get("scenario_name", "")
        solver  = data.get("solver", "")
        if not sc_name or not solver:
            continue
        rd = data.get("runs_detail")
        if not rd or len(rd) < N_RUNS:
            continue

        solver_label = SOLVER_LABELS.get(solver, solver)
        for r in rd:
            row = {
                "scenario":     sc_name,
                "solver":       solver_label,
                "run":          r["run"],
                "seed":         r["seed"],
                "objective":    r["objective"],
                "total_km":     r["total_km"],
                "late_minutes": r["late_minutes"],
                "vehicles_used":        r["vehicles_used"],
                "capacity_violation_kg": r["capacity_violation_kg"],
                "wait_minutes":         r["wait_minutes"],
                "route_time_minutes":   r["route_time_minutes"],
                "runtime_seconds":      r["runtime_seconds"],
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    df["scenario"] = pd.Categorical(
        df["scenario"], categories=SCENARIO_ORDER, ordered=True,
    )
    df["solver"] = pd.Categorical(
        df["solver"], categories=SOLVER_ORDER, ordered=True,
    )
    return df.sort_values(["scenario", "solver", "run"]).reset_index(drop=True)


# ── Histogramas ──────────────────────────────────────────────────────────────

def _plot_histograms(df: pd.DataFrame) -> None:
    """Un histograma por escenario por metrica, 3 algoritmos superpuestos."""
    for metric_col, metric_label in METRICS:
        for sc in SCENARIO_ORDER:
            dfs = df[df["scenario"] == sc]
            if dfs.empty:
                continue

            fig, ax = plt.subplots(figsize=(8, 4.5))

            for sv in SOLVER_ORDER:
                vals = dfs.loc[dfs["solver"] == sv, metric_col].values
                if len(vals) == 0:
                    continue
                ax.hist(
                    vals, bins=80, alpha=0.55, label=sv,
                    color=COLORS[sv], edgecolor="white", linewidth=0.3,
                )

            ax.set_xlabel(metric_label, fontsize=11)
            ax.set_ylabel("Frecuencia", fontsize=11)
            ax.set_title(
                f"{metric_label} — {sc}  (n = {N_RUNS:,} por algoritmo)",
                fontsize=12, fontweight="bold",
            )
            ax.legend(frameon=True, fontsize=10)
            ax.grid(axis="y", alpha=0.3)
            sns.despine(ax=ax)

            sc_key = (
                sc.lower()
                .replace(" ", "_")
                .replace("á", "a")
                .replace("é", "e")
            )
            met_key = metric_col
            fname = OUT_DIR / f"hist_{sc_key}_{met_key}.png"
            fig.tight_layout()
            fig.savefig(fname, dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"  [hist] {fname.name}")


# ── Boxplots ─────────────────────────────────────────────────────────────────

def _plot_boxplots(df: pd.DataFrame) -> None:
    """Un boxplot por escenario por metrica, 3 algoritmos lado a lado."""
    for metric_col, metric_label in METRICS:
        for sc in SCENARIO_ORDER:
            dfs = df[df["scenario"] == sc]
            if dfs.empty:
                continue

            fig, ax = plt.subplots(figsize=(6, 4.5))

            box_data = []
            box_labels = []
            box_colors = []
            for sv in SOLVER_ORDER:
                vals = dfs.loc[dfs["solver"] == sv, metric_col].values
                if len(vals) == 0:
                    continue
                box_data.append(vals)
                box_labels.append(sv)
                box_colors.append(COLORS[sv])

            bp = ax.boxplot(
                box_data,
                tick_labels=box_labels,
                patch_artist=True,
                widths=0.5,
                showfliers=False,
                medianprops=dict(color="black", linewidth=1.5),
            )
            for patch, color in zip(bp["boxes"], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)

            ax.set_ylabel(metric_label, fontsize=11)
            ax.set_title(
                f"{metric_label} — {sc}",
                fontsize=12, fontweight="bold",
            )
            ax.grid(axis="y", alpha=0.3)
            sns.despine(ax=ax)

            sc_key = (
                sc.lower()
                .replace(" ", "_")
                .replace("á", "a")
                .replace("é", "e")
            )
            fname = OUT_DIR / f"box_{sc_key}_{metric_col}.png"
            fig.tight_layout()
            fig.savefig(fname, dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"  [box]  {fname.name}")


# ── Prueba de Wilcoxon (rank-sum / Mann-Whitney U) ──────────────────────────

def _wilcoxon_tests(df: pd.DataFrame) -> pd.DataFrame:
    """
    Comparaciones por pares (GA vs ACO, GA vs Hibrido, ACO vs Hibrido)
    dentro de cada escenario, para objective y runtime_seconds.

    Usa Mann-Whitney U (Wilcoxon rank-sum) porque:
    - No asume normalidad (distribuciones sesgadas, multimodales)
    - Muestras independientes (cada corrida usa seed distinta)
    - Gran tamano muestral (n=10 000) → p-valores muy pequenos
    """
    pairs = list(combinations(SOLVER_ORDER, 2))
    results: list[dict] = []

    for sc in SCENARIO_ORDER:
        dfs = df[df["scenario"] == sc]
        if dfs.empty:
            continue

        for metric_col, metric_label in COMPARISON_METRICS:
            for alg1, alg2 in pairs:
                v1 = dfs.loc[dfs["solver"] == alg1, metric_col].values
                v2 = dfs.loc[dfs["solver"] == alg2, metric_col].values

                if len(v1) == 0 or len(v2) == 0:
                    continue

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stat_u, p_val = sp_stats.mannwhitneyu(
                        v1, v2, alternative="two-sided",
                    )

                mean1, mean2     = float(np.mean(v1)), float(np.mean(v2))
                median1, median2 = float(np.median(v1)), float(np.median(v2))
                std1, std2       = float(np.std(v1, ddof=1)), float(np.std(v2, ddof=1))

                if p_val < ALPHA:
                    if median1 < median2:
                        winner = alg1
                    elif median2 < median1:
                        winner = alg2
                    elif mean1 <= mean2:
                        winner = alg1
                    else:
                        winner = alg2
                    interp = (
                        f"Diferencia significativa (p < {ALPHA}). "
                        f"{winner} obtiene valores significativamente menores."
                    )
                else:
                    interp = (
                        f"Sin diferencia significativa (p >= {ALPHA}). "
                        "No se puede rechazar la hipotesis nula."
                    )

                # Effect size: rank-biserial correlation r = 1 - 2U/(n1*n2)
                n1, n2 = len(v1), len(v2)
                r_effect = 1.0 - (2.0 * stat_u) / (n1 * n2)

                results.append({
                    "escenario":     sc,
                    "metrica":       metric_label,
                    "comparacion":   f"{alg1} vs {alg2}",
                    "n_alg1":        n1,
                    "n_alg2":        n2,
                    "media_alg1":    round(mean1, 6),
                    "media_alg2":    round(mean2, 6),
                    "std_alg1":      round(std1, 6),
                    "std_alg2":      round(std2, 6),
                    "mediana_alg1":  round(median1, 6),
                    "mediana_alg2":  round(median2, 6),
                    "U_statistic":   stat_u,
                    "p_value":       p_val,
                    "effect_size_r": round(r_effect, 6),
                    "significativo": "Si" if p_val < ALPHA else "No",
                    "interpretacion": interp,
                })

    return pd.DataFrame(results)


# ── Prueba de normalidad (Shapiro-Wilk sobre submuestra) ────────────────────

def _normality_tests(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shapiro-Wilk sobre una submuestra de 5 000 observaciones (limite de scipy).
    Documenta por que NO se asume normalidad.
    """
    results: list[dict] = []
    for sc in SCENARIO_ORDER:
        dfs = df[df["scenario"] == sc]
        for sv in SOLVER_ORDER:
            vals = dfs.loc[dfs["solver"] == sv, "objective"].values
            if len(vals) == 0:
                continue
            sample = np.random.default_rng(42).choice(vals, size=min(5000, len(vals)), replace=False)
            stat_w, p_val = sp_stats.shapiro(sample)
            results.append({
                "escenario": sc,
                "algoritmo": sv,
                "metrica":   "objective",
                "n_sample":  len(sample),
                "W_stat":    round(stat_w, 6),
                "p_value":   p_val,
                "normal":    "Si" if p_val >= ALPHA else "No",
            })
    return pd.DataFrame(results)


# ── Texto metodologico ──────────────────────────────────────────────────────

def _write_methodology(
    df_wilcox: pd.DataFrame,
    df_normal: pd.DataFrame,
) -> None:
    """Genera assets/stats/metodologia.md con texto listo para tesis."""

    n_normal = (df_normal["normal"] == "Si").sum()
    n_total  = len(df_normal)

    lines = []
    lines.append("# Validacion estadistica de resultados experimentales")
    lines.append("")
    lines.append("## Justificacion de la prueba no parametrica")
    lines.append("")
    lines.append(
        "Para determinar si las diferencias observadas entre los algoritmos "
        "(GA, ACO e Hibrido GA-ACO) son estadisticamente significativas, se "
        "empleo la prueba de **Mann-Whitney U** (tambien conocida como prueba "
        "de rango de Wilcoxon para muestras independientes)."
    )
    lines.append("")
    lines.append("### Por que no se asume normalidad")
    lines.append("")
    lines.append(
        "La prueba de Shapiro-Wilk aplicada a submuestras de 5,000 observaciones "
        f"rechazo la hipotesis de normalidad en {n_total - n_normal} de {n_total} "
        "combinaciones escenario-algoritmo (p < 0.05). Esto indica que las "
        "distribuciones de la funcion objetivo **no siguen una distribucion normal**, "
        "lo cual invalida el uso de pruebas parametricas como la prueba t de Student "
        "o ANOVA."
    )
    lines.append("")
    lines.append(
        "Las razones de la no-normalidad incluyen:"
    )
    lines.append("")
    lines.append("- Distribuciones multimodales o asimetricas en la funcion objetivo.")
    lines.append(
        "- Presencia de valores extremos generados por soluciones suboptimas "
        "en corridas con semillas desfavorables."
    )
    lines.append(
        "- La naturaleza estocastica de las metaheuristicas produce distribuciones "
        "que no se ajustan al modelo gaussiano."
    )
    lines.append("")
    lines.append("### Configuracion de la prueba")
    lines.append("")
    lines.append(
        f"- **Tamano de muestra**: n = {N_RUNS:,} corridas independientes por "
        "algoritmo por escenario."
    )
    lines.append(f"- **Nivel de significancia**: alpha = {ALPHA}")
    lines.append("- **Hipotesis nula (H0)**: Las distribuciones de ambos algoritmos son identicas.")
    lines.append(
        "- **Hipotesis alternativa (H1)**: Las distribuciones difieren significativamente "
        "(prueba bilateral)."
    )
    lines.append(
        "- **Tamano del efecto**: Se reporta la correlacion de rango biserial "
        "(r = 1 - 2U / n1*n2), donde |r| < 0.1 es efecto negligible, "
        "0.1-0.3 pequeno, 0.3-0.5 mediano y > 0.5 grande."
    )
    lines.append("")
    lines.append("### Comparaciones realizadas")
    lines.append("")
    lines.append(
        "Se realizaron comparaciones por pares dentro de cada escenario "
        "(GA vs ACO, GA vs Hibrido GA-ACO, ACO vs Hibrido GA-ACO) para "
        "dos metricas: funcion objetivo y tiempo de ejecucion."
    )
    lines.append("")

    lines.append("## Resultados de la prueba de Mann-Whitney U")
    lines.append("")

    for sc in SCENARIO_ORDER:
        dfw = df_wilcox[
            (df_wilcox["escenario"] == sc) &
            (df_wilcox["metrica"] == "Funcion objetivo")
        ]
        if dfw.empty:
            continue

        lines.append(f"### {sc}")
        lines.append("")
        lines.append("| Comparacion | Media A | Media B | Mediana A | Mediana B | p-valor | Efecto (r) | Significativo |")
        lines.append("|---|---|---|---|---|---|---|---|")

        for _, row in dfw.iterrows():
            p_str = f"{row['p_value']:.2e}" if row["p_value"] < 0.001 else f"{row['p_value']:.4f}"
            lines.append(
                f"| {row['comparacion']} "
                f"| {row['media_alg1']:.4f} "
                f"| {row['media_alg2']:.4f} "
                f"| {row['mediana_alg1']:.4f} "
                f"| {row['mediana_alg2']:.4f} "
                f"| {p_str} "
                f"| {row['effect_size_r']:.4f} "
                f"| {row['significativo']} |"
            )
        lines.append("")

    lines.append("## Interpretacion general")
    lines.append("")

    n_sig = (df_wilcox[df_wilcox["metrica"] == "Funcion objetivo"]["significativo"] == "Si").sum()
    n_comp = len(df_wilcox[df_wilcox["metrica"] == "Funcion objetivo"])
    lines.append(
        f"De las {n_comp} comparaciones por pares realizadas sobre la funcion objetivo, "
        f"{n_sig} resultaron estadisticamente significativas (p < {ALPHA}). "
    )
    lines.append("")

    sig_obj = df_wilcox[
        (df_wilcox["metrica"] == "Funcion objetivo") &
        (df_wilcox["significativo"] == "Si")
    ]
    for _, row in sig_obj.iterrows():
        # Determine winner
        algs = row["comparacion"].split(" vs ")
        if row["mediana_alg1"] < row["mediana_alg2"]:
            winner = algs[0]
        elif row["mediana_alg2"] < row["mediana_alg1"]:
            winner = algs[1]
        elif row["media_alg1"] <= row["media_alg2"]:
            winner = algs[0]
        else:
            winner = algs[1]

        r_abs = abs(row["effect_size_r"])
        if r_abs < 0.1:
            effect_word = "negligible"
        elif r_abs < 0.3:
            effect_word = "pequeno"
        elif r_abs < 0.5:
            effect_word = "mediano"
        else:
            effect_word = "grande"

        lines.append(
            f"- **{row['escenario']}** — {row['comparacion']}: "
            f"Con un nivel de significancia de {ALPHA}, la diferencia observada "
            f"no se atribuye al azar (p = {row['p_value']:.2e}). "
            f"{winner} obtiene valores menores de funcion objetivo. "
            f"Tamano del efecto: {effect_word} (r = {row['effect_size_r']:.4f})."
        )

    not_sig = df_wilcox[
        (df_wilcox["metrica"] == "Funcion objetivo") &
        (df_wilcox["significativo"] == "No")
    ]
    if not not_sig.empty:
        lines.append("")
        for _, row in not_sig.iterrows():
            lines.append(
                f"- **{row['escenario']}** — {row['comparacion']}: "
                f"No se encontro diferencia significativa (p = {row['p_value']:.4f}). "
                "Los algoritmos son estadisticamente equivalentes en este escenario."
            )

    lines.append("")
    lines.append("## Texto sugerido para la seccion de resultados")
    lines.append("")
    lines.append(
        "Para evaluar si las diferencias de desempeno entre los tres algoritmos "
        "son estadisticamente significativas, se aplico la prueba de Mann-Whitney U "
        "(Wilcoxon rank-sum) a las 10,000 corridas independientes de cada combinacion "
        "escenario-algoritmo. Se opto por esta prueba no parametrica porque la prueba "
        "de Shapiro-Wilk rechazo la hipotesis de normalidad en la mayoria de las "
        "distribuciones observadas (p < 0.05), invalidando el uso de pruebas "
        "parametricas como la t de Student."
    )
    lines.append("")
    lines.append(
        "Se utilizo un nivel de significancia alpha = 0.05 y se reporta la "
        "correlacion de rango biserial como medida del tamano del efecto. "
        f"Los resultados muestran que {n_sig} de {n_comp} comparaciones por pares "
        "en la funcion objetivo presentan diferencias estadisticamente significativas, "
        "lo que permite concluir que las diferencias observadas entre los algoritmos "
        "no se atribuyen al azar, sino a diferencias reales en el desempeno "
        "de cada metaheuristica."
    )
    lines.append("")

    fp = OUT_DIR / "metodologia.md"
    fp.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [md]   {fp.name}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" VALIDACION ESTADISTICA — TESIS GA-ACO CVRP")
    print("=" * 60)

    # 1. Cargar datos
    print("\n[1/6] Cargando runs_detail de los 15 benchmarks formales...")
    df = _load_formal_benchmarks()
    combos = df.groupby(["scenario", "solver"], observed=True).size()
    print(f"  Total filas: {len(df):,}")
    print(f"  Combinaciones escenario x algoritmo: {len(combos)}")
    for (sc, sv), n in combos.items():
        print(f"    {sc:25s}  {sv:18s}  n = {n:,}")

    # 2. Exportar CSV maestro por corrida
    print("\n[2/6] Exportando CSV maestro por corrida...")
    csv_all = OUT_DIR / "all_runs.csv"
    df.to_csv(csv_all, index=False, encoding="utf-8")
    print(f"  {csv_all.name} ({len(df):,} filas)")

    # 3. Histogramas
    print("\n[3/6] Generando histogramas...")
    _plot_histograms(df)

    # 4. Boxplots
    print("\n[4/6] Generando boxplots...")
    _plot_boxplots(df)

    # 5. Pruebas estadisticas
    print("\n[5/6] Ejecutando pruebas de normalidad (Shapiro-Wilk)...")
    df_normal = _normality_tests(df)
    normal_csv = OUT_DIR / "shapiro_wilk_results.csv"
    df_normal.to_csv(normal_csv, index=False, encoding="utf-8")
    print(f"  {normal_csv.name}")
    for _, r in df_normal.iterrows():
        tag = "NORMAL" if r["normal"] == "Si" else "NO NORMAL"
        print(f"    {r['escenario']:25s} {r['algoritmo']:18s} W={r['W_stat']:.6f}  p={r['p_value']:.2e}  {tag}")

    print("\n[6/6] Ejecutando pruebas de Mann-Whitney U (Wilcoxon rank-sum)...")
    df_wilcox = _wilcoxon_tests(df)
    wilcox_csv = OUT_DIR / "wilcoxon_results.csv"
    df_wilcox.to_csv(wilcox_csv, index=False, encoding="utf-8")
    print(f"  {wilcox_csv.name}")
    for _, r in df_wilcox.iterrows():
        tag = "***" if r["significativo"] == "Si" else "   "
        p_str = f"{r['p_value']:.2e}" if r['p_value'] < 0.001 else f"{r['p_value']:.4f}"
        print(
            f"  {tag} {r['escenario']:25s} {r['metrica']:25s} "
            f"{r['comparacion']:30s} p={p_str}"
        )

    # 7. Texto metodologico
    print("\nGenerando texto metodologico...")
    _write_methodology(df_wilcox, df_normal)

    # Resumen final
    print("\n" + "=" * 60)
    print(" ENTREGABLES GENERADOS")
    print("=" * 60)
    all_files = sorted(OUT_DIR.iterdir())
    for f in all_files:
        size = f.stat().st_size
        if size > 1024 * 1024:
            sz = f"{size / 1024 / 1024:.1f} MB"
        elif size > 1024:
            sz = f"{size / 1024:.0f} KB"
        else:
            sz = f"{size} B"
        print(f"  {f.name:45s} {sz:>8s}")
    print("=" * 60)
    print(" Listo. Revisa assets/stats/")
    print("=" * 60)


if __name__ == "__main__":
    main()
