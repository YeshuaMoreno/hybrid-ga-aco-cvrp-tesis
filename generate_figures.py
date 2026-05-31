"""
generate_figures.py
Genera todas las figuras de análisis como archivos PNG de alta resolución.

Uso:
    python generate_figures.py

Salida:
    assets/figures/*.png

Requiere:
    pip install matplotlib seaborn pandas numpy
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sin GUI, seguro en cualquier entorno
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

BASE = Path(__file__).parent
MASTER_CSV = BASE / "assets" / "master_benchmarks.csv"
RESULTS_DIR = BASE / "results"
FIGURES_DIR = BASE / "assets" / "figures"

SOLVER_LABELS = {"ga": "GA", "aco": "ACO", "hybrid": "Híbrido"}
SOLVER_COLORS = {"GA": "#2563EB", "ACO": "#EA580C", "Híbrido": "#16A34A"}
SCENARIO_ORDER = [
    "Base",
    "Hora Pico",
    "Tienda Congestionada",
    "Estrés (sin tardanza)",
    "Estrés",
    "Estrés Total",
]

DPI = 150
STYLE = "seaborn-v0_8-whitegrid"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_master() -> pd.DataFrame | None:
    if not MASTER_CSV.exists():
        print(f"[ERROR] Tabla maestra no encontrada: {MASTER_CSV}")
        print("Ejecuta primero: python consolidate_results.py")
        return None
    df = pd.read_csv(MASTER_CSV)
    df["solver_label"] = df["solver"].map(SOLVER_LABELS).fillna(df["solver"])
    order = SCENARIO_ORDER + [s for s in df["scenario"].unique() if s not in SCENARIO_ORDER]
    df["scenario"] = pd.Categorical(df["scenario"], categories=order, ordered=True)
    return df


def _infer_label(json_path: Path, stats: dict) -> str:
    p = str(json_path).replace("\\", "/").lower()
    rt = stats.get("route_time_mean", 0.0)
    late = stats.get("late_mean", 0.0)
    wait = stats.get("wait_mean", 0.0)
    if "scenario5" in p:
        return "Estrés Total"
    if "scenario4" in p:
        return "Estrés (sin tardanza)" if late <= 50 else "Estrés"
    if "scenario3" in p:
        return "Tienda Congestionada"
    if "scenario2" in p:
        return "Hora Pico"
    if "scenario1" in p:
        return "Base"
    if late > 300:
        return "Estrés Total"
    if late > 50:
        return "Estrés"
    if rt < 492:
        return "Base"
    if rt < 548:
        return "Tienda Congestionada" if wait < 165 else "Hora Pico"
    return "Estrés (sin tardanza)" if rt < 700 else "Estrés"


def _load_runs() -> pd.DataFrame:
    records = []
    for jf in sorted(RESULTS_DIR.rglob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "runs_detail" not in data:
            continue
        solver = data.get("solver", "?")
        label = _infer_label(jf, data.get("stats", {}))
        for run in data["runs_detail"]:
            records.append({
                "solver_label": SOLVER_LABELS.get(solver, solver),
                "scenario": label,
                "objective": run.get("objective"),
                "total_km": run.get("total_km"),
                "late_minutes": run.get("late_minutes"),
                "wait_minutes": run.get("wait_minutes"),
                "route_time_minutes": run.get("route_time_minutes"),
                "runtime_seconds": run.get("runtime_seconds"),
            })
    return pd.DataFrame(records) if records else pd.DataFrame()


def _save(fig: plt.Figure, name: str) -> None:
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {path.name}")


# ── Figuras ───────────────────────────────────────────────────────────────────


def fig_objetivo_por_escenario(df: pd.DataFrame) -> None:
    """Barras agrupadas: objetivo medio por escenario y algoritmo."""
    agg = (
        df.groupby(["scenario", "solver_label"], observed=True)
        .agg(mu=("objective_mean", "mean"), sigma=("objective_stdev", "mean"))
        .reset_index()
    )
    sc = sorted(agg["scenario"].dropna().unique().tolist(),
                key=lambda x: SCENARIO_ORDER.index(x) if x in SCENARIO_ORDER else 99)
    solvers = ["GA", "ACO", "Híbrido"]
    x = np.arange(len(sc))
    width = 0.25

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 5))
        for i, sv in enumerate(solvers):
            vals = []
            errs = []
            for s in sc:
                row = agg[(agg["scenario"] == s) & (agg["solver_label"] == sv)]
                vals.append(float(row["mu"].iloc[0]) if not row.empty else 0.0)
                errs.append(float(row["sigma"].iloc[0]) if not row.empty else 0.0)
            ax.bar(
                x + i * width, vals, width, label=sv,
                color=SOLVER_COLORS.get(sv, "#888"),
                yerr=errs, capsize=4, error_kw={"linewidth": 1},
            )
        ax.set_xticks(x + width)
        ax.set_xticklabels(sc, rotation=15, ha="right")
        ax.set_ylabel("Objetivo medio")
        ax.set_title("Objetivo medio por escenario y algoritmo (±σ)")
        ax.legend(loc="upper left")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "01_objetivo_por_escenario")


def fig_tiempo_ruta_por_escenario(df: pd.DataFrame) -> None:
    """Barras: tiempo total de ruta por escenario."""
    agg = (
        df.groupby(["scenario", "solver_label"], observed=True)["route_time_mean"]
        .mean()
        .reset_index()
    )
    sc = sorted(agg["scenario"].dropna().unique().tolist(),
                key=lambda x: SCENARIO_ORDER.index(x) if x in SCENARIO_ORDER else 99)
    solvers = ["GA", "ACO", "Híbrido"]
    x = np.arange(len(sc))
    width = 0.25

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 5))
        for i, sv in enumerate(solvers):
            vals = []
            for s in sc:
                row = agg[(agg["scenario"] == s) & (agg["solver_label"] == sv)]
                vals.append(float(row["route_time_mean"].iloc[0]) if not row.empty else 0.0)
            ax.bar(x + i * width, vals, width, label=sv, color=SOLVER_COLORS.get(sv, "#888"))
        ax.set_xticks(x + width)
        ax.set_xticklabels(sc, rotation=15, ha="right")
        ax.set_ylabel("Tiempo de ruta (min)")
        ax.set_title("Tiempo total de ruta por escenario y algoritmo")
        ax.legend()
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "02_tiempo_ruta_por_escenario")


def fig_runtime_por_escenario(df: pd.DataFrame) -> None:
    """Barras: runtime por escenario."""
    agg = (
        df.groupby(["scenario", "solver_label"], observed=True)["runtime_mean"]
        .mean()
        .reset_index()
    )
    sc = sorted(agg["scenario"].dropna().unique().tolist(),
                key=lambda x: SCENARIO_ORDER.index(x) if x in SCENARIO_ORDER else 99)
    solvers = ["GA", "ACO", "Híbrido"]
    x = np.arange(len(sc))
    width = 0.25

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 5))
        for i, sv in enumerate(solvers):
            vals = []
            for s in sc:
                row = agg[(agg["scenario"] == s) & (agg["solver_label"] == sv)]
                vals.append(float(row["runtime_mean"].iloc[0]) if not row.empty else 0.0)
            ax.bar(x + i * width, vals, width, label=sv, color=SOLVER_COLORS.get(sv, "#888"))
        ax.set_xticks(x + width)
        ax.set_xticklabels(sc, rotation=15, ha="right")
        ax.set_ylabel("Runtime medio (s)")
        ax.set_title("Runtime promedio por escenario y algoritmo")
        ax.legend()
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "03_runtime_por_escenario")


def fig_boxplot_objetivo(runs: pd.DataFrame) -> None:
    """Boxplot del valor objetivo por algoritmo."""
    if runs.empty:
        print("  [SKIP] Sin datos de runs_detail para boxplot")
        return
    solvers = ["GA", "ACO", "Híbrido"]
    data_by_solver = [
        runs[runs["solver_label"] == sv]["objective"].dropna().values
        for sv in solvers
    ]
    colors = [SOLVER_COLORS.get(sv, "#888") for sv in solvers]

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 6))
        bp = ax.boxplot(
            data_by_solver,
            labels=solvers,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": "white", "linewidth": 2.5},
            whiskerprops={"linewidth": 1.5},
            capprops={"linewidth": 1.5},
        )
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
        ax.set_ylabel("Valor objetivo")
        ax.set_title("Distribución del objetivo por algoritmo (todas las corridas)")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "04_boxplot_objetivo_por_algoritmo")


def fig_violin_objetivo(runs: pd.DataFrame) -> None:
    """Violin plot del valor objetivo por algoritmo."""
    if runs.empty:
        print("  [SKIP] Sin datos de runs_detail para violin")
        return
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 6))
        solvers = ["GA", "ACO", "Híbrido"]
        data_list = [
            runs[runs["solver_label"] == sv]["objective"].dropna().values
            for sv in solvers
        ]
        parts = ax.violinplot(data_list, positions=range(len(solvers)), showmedians=True)
        for i, (pc, sv) in enumerate(zip(parts["bodies"], solvers)):
            pc.set_facecolor(SOLVER_COLORS.get(sv, "#888"))
            pc.set_alpha(0.8)
        parts["cmedians"].set_color("white")
        parts["cmedians"].set_linewidth(2)
        ax.set_xticks(range(len(solvers)))
        ax.set_xticklabels(solvers)
        ax.set_ylabel("Valor objetivo")
        ax.set_title("Densidad del objetivo por algoritmo (violin)")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "05_violin_objetivo_por_algoritmo")


def fig_heatmap_objetivo(df: pd.DataFrame) -> None:
    """Heatmap algoritmo × escenario por objetivo medio."""
    pivot = (
        df.groupby(["solver_label", "scenario"], observed=True)["objective_mean"]
        .mean()
        .unstack("scenario")
    )
    sc_order = [s for s in SCENARIO_ORDER if s in pivot.columns]
    pivot = pivot[sc_order + [c for c in pivot.columns if c not in SCENARIO_ORDER]]

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(len(pivot.columns) * 2.2 + 1, 3.5))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".1f",
            cmap="Blues",
            linewidths=0.5,
            ax=ax,
            cbar_kws={"label": "Objetivo medio"},
        )
        ax.set_title("Heatmap — Objetivo medio por algoritmo y escenario")
        ax.set_xlabel("")
        ax.set_ylabel("")
        plt.xticks(rotation=20, ha="right")
        fig.tight_layout()
    _save(fig, "06_heatmap_objetivo")


def fig_heatmap_tardanza(df: pd.DataFrame) -> None:
    """Heatmap algoritmo × escenario por tardanza media."""
    pivot = (
        df.groupby(["solver_label", "scenario"], observed=True)["late_mean"]
        .mean()
        .unstack("scenario")
    )
    sc_order = [s for s in SCENARIO_ORDER if s in pivot.columns]
    pivot = pivot[sc_order + [c for c in pivot.columns if c not in SCENARIO_ORDER]]

    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(len(pivot.columns) * 2.2 + 1, 3.5))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".1f",
            cmap="Reds",
            linewidths=0.5,
            ax=ax,
            cbar_kws={"label": "Tardanza media (min)"},
        )
        ax.set_title("Heatmap — Tardanza media (min) por algoritmo y escenario")
        ax.set_xlabel("")
        ax.set_ylabel("")
        plt.xticks(rotation=20, ha="right")
        fig.tight_layout()
    _save(fig, "07_heatmap_tardanza")


def fig_sensibilidad(df: pd.DataFrame) -> None:
    """Curvas de sensibilidad: objetivo vs traffic_factor."""
    sens = (
        df[df["service_extra"] == 0]
        .groupby(["solver_label", "traffic_factor"])
        .agg(
            obj=("objective_mean", "mean"),
            late=("late_mean", "mean"),
            rt=("route_time_mean", "mean"),
        )
        .reset_index()
    )
    if sens.empty or sens["traffic_factor"].nunique() < 2:
        print("  [SKIP] Datos insuficientes para sensibilidad")
        return

    solvers = sens["solver_label"].unique()
    with plt.style.context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        metrics = [("obj", "Objetivo medio"), ("late", "Tardanza media (min)"), ("rt", "Tiempo de ruta (min)")]
        for ax, (col, ylabel) in zip(axes, metrics):
            for sv in solvers:
                sub = sens[sens["solver_label"] == sv].sort_values("traffic_factor")
                ax.plot(
                    sub["traffic_factor"], sub[col],
                    marker="o", label=sv,
                    color=SOLVER_COLORS.get(sv, "#888"),
                    linewidth=2.5, markersize=8,
                )
            ax.set_xlabel("Traffic factor")
            ax.set_ylabel(ylabel)
            ax.set_title(ylabel)
            ax.legend(fontsize=8)
            ax.grid(alpha=0.4)
        fig.suptitle("Análisis de sensibilidad — variación con traffic_factor", fontsize=13, fontweight="bold")
        fig.tight_layout()
    _save(fig, "08_sensibilidad_traffic_factor")


def fig_runtime_vs_calidad(df: pd.DataFrame) -> None:
    """Scatter runtime vs objetivo por solver y escenario."""
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 6))
        markers = ["o", "s", "^", "D", "v", "P"]
        sc_list = sorted(df["scenario"].dropna().unique().tolist(),
                         key=lambda x: SCENARIO_ORDER.index(x) if x in SCENARIO_ORDER else 99)
        sc_markers = {sc: markers[i % len(markers)] for i, sc in enumerate(sc_list)}
        for sv in ["GA", "ACO", "Híbrido"]:
            sub = df[df["solver_label"] == sv]
            for sc in sc_list:
                s2 = sub[sub["scenario"] == sc]
                if s2.empty:
                    continue
                ax.scatter(
                    s2["runtime_mean"], s2["objective_mean"],
                    color=SOLVER_COLORS.get(sv, "#888"),
                    marker=sc_markers[sc],
                    s=100, alpha=0.8,
                    label=f"{sv} – {sc}" if True else "",
                )
        # Leyenda simplificada: colores por solver, marcadores por escenario
        solver_patches = [
            mpatches.Patch(color=SOLVER_COLORS.get(sv, "#888"), label=sv)
            for sv in ["GA", "ACO", "Híbrido"]
        ]
        ax.legend(handles=solver_patches, title="Algoritmo", loc="upper right")
        ax.set_xlabel("Runtime medio (s)")
        ax.set_ylabel("Objetivo medio")
        ax.set_title("Tradeoff Runtime vs. Calidad")
        ax.grid(alpha=0.4)
        fig.tight_layout()
    _save(fig, "09_runtime_vs_calidad")


def fig_histograma_objetivo(runs: pd.DataFrame) -> None:
    """Histograma del objetivo por algoritmo."""
    if runs.empty:
        return
    solvers = ["GA", "ACO", "Híbrido"]
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        for sv in solvers:
            data = runs[runs["solver_label"] == sv]["objective"].dropna()
            if data.empty:
                continue
            ax.hist(
                data, bins=60, alpha=0.55,
                color=SOLVER_COLORS.get(sv, "#888"),
                label=sv, edgecolor="white", linewidth=0.3,
            )
        ax.set_xlabel("Valor objetivo")
        ax.set_ylabel("Frecuencia")
        ax.set_title("Histograma de objetivo por algoritmo (todas las corridas)")
        ax.legend()
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "10_histograma_objetivo")


def fig_histograma_km(runs: pd.DataFrame) -> None:
    """Histograma de distancia (km) por algoritmo."""
    if runs.empty:
        return
    solvers = ["GA", "ACO", "Híbrido"]
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        for sv in solvers:
            data = runs[runs["solver_label"] == sv]["total_km"].dropna()
            if data.empty:
                continue
            ax.hist(
                data, bins=60, alpha=0.55,
                color=SOLVER_COLORS.get(sv, "#888"),
                label=sv, edgecolor="white", linewidth=0.3,
            )
        ax.set_xlabel("Distancia (km)")
        ax.set_ylabel("Frecuencia")
        ax.set_title("Histograma de distancia recorrida por algoritmo")
        ax.legend()
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "11_histograma_km")


def fig_variabilidad_objetivo(df: pd.DataFrame) -> None:
    """Barras de σ (desviación estándar) del objetivo por solver."""
    stab = (
        df.groupby("solver_label", observed=True)["objective_stdev"]
        .mean()
        .reset_index()
        .sort_values("objective_stdev")
    )
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(
            stab["solver_label"], stab["objective_stdev"],
            color=[SOLVER_COLORS.get(sv, "#888") for sv in stab["solver_label"]],
        )
        for bar, val in zip(bars, stab["objective_stdev"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                f"{val:.4f}",
                ha="center", va="bottom", fontsize=10,
            )
        ax.set_ylabel("Desviación estándar del objetivo (σ)")
        ax.set_title("Variabilidad del objetivo — menor σ indica mayor estabilidad")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
    _save(fig, "12_variabilidad_objetivo")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = _load_master()
    if df is None:
        sys.exit(1)

    print("\nGenerando figuras estáticas…")

    # Figuras que solo necesitan la tabla maestra
    fig_objetivo_por_escenario(df)
    fig_tiempo_ruta_por_escenario(df)
    fig_runtime_por_escenario(df)
    fig_heatmap_objetivo(df)
    fig_heatmap_tardanza(df)
    fig_sensibilidad(df)
    fig_runtime_vs_calidad(df)
    fig_variabilidad_objetivo(df)

    # Figuras que necesitan runs_detail (10 000 corridas)
    print("\nCargando runs_detail (puede tomar unos segundos)…")
    runs = _load_runs()
    if not runs.empty:
        fig_boxplot_objetivo(runs)
        fig_violin_objetivo(runs)
        fig_histograma_objetivo(runs)
        fig_histograma_km(runs)
    else:
        print("  [AVISO] No se encontraron datos de runs_detail.")

    print(f"\nFiguras guardadas en: {FIGURES_DIR}")
    print(f"Total: {len(list(FIGURES_DIR.glob('*.png')))} archivos PNG")


if __name__ == "__main__":
    main()
