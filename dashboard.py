"""
dashboard.py  —  GA-ACO CVRP · Dashboard de Defensa
=====================================================
Ejecutar (solo localhost):
    streamlit run dashboard.py --server.address=localhost --server.port=8501

Requiere:
    pip install -r requirements.txt

Genera la tabla maestra primero:
    python consolidate_results.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Rutas base ────────────────────────────────────────────────────────────────

BASE        = Path(__file__).parent
RESULTS_DIR = BASE / "results"
DATA_CSV    = BASE / "data" / "dataset_artegasaltillo.csv"
MASTER_CSV  = BASE / "assets" / "master_benchmarks.csv"
ROUTES_DIR  = BASE / "assets" / "routes"

SOLVER_LABELS = {"ga": "GA", "aco": "ACO", "hybrid": "Híbrido GA-ACO"}
SOLVER_COLORS = {"GA": "#1D4ED8", "ACO": "#B45309", "Híbrido GA-ACO": "#15803D"}

SCENARIO_ORDER = [
    "Base",
    "Hora Pico",
    "Tienda Congestionada",
    "Estrés",
    "Estrés Total",
]

# ── Configuración de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="GA-ACO CVRP — Defensa de Tesis",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Fondo sidebar oscuro profesional */
    section[data-testid="stSidebar"] { background: #1E293B; }
    section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    section[data-testid="stSidebar"] h2 { color: #F8FAFC !important; font-size: 1.1rem; }
    /* Ajuste de métricas */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    /* Tabla más compacta */
    .dataframe td { font-size: 0.87rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Carga de datos ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _load_master() -> pd.DataFrame | None:
    if not MASTER_CSV.exists():
        return None
    df = pd.read_csv(MASTER_CSV)
    df["solver_label"] = df["solver"].map(SOLVER_LABELS).fillna(df["solver"])
    order = SCENARIO_ORDER + [s for s in df["scenario"].unique() if s not in SCENARIO_ORDER]
    df["scenario"] = pd.Categorical(df["scenario"], categories=order, ordered=True)
    return df


@st.cache_data(show_spinner=False)
def _load_nodes() -> pd.DataFrame | None:
    if not DATA_CSV.exists():
        return None
    df = pd.read_csv(DATA_CSV)
    df["tw_start_h"] = df["tw_start"] / 60          # minutos → horas decimales
    df["tw_end_h"]   = df["tw_end"]   / 60
    df["tw_start_fmt"] = df["tw_start"].apply(_fmt_hhmm)
    df["tw_end_fmt"]   = df["tw_end"].apply(_fmt_hhmm)
    df["demand_kg"]    = df["demand"] * 7.0
    return df


def _fmt_hhmm(minutes: int) -> str:
    """Convierte minutos desde medianoche a 'HH:MM'."""
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"


@st.cache_data(show_spinner=False)
def _load_routes() -> list[dict]:
    if not ROUTES_DIR.exists():
        return []
    out = []
    for f in sorted(ROUTES_DIR.glob("best_route_*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def _sorted_scenarios(df: pd.DataFrame) -> list[str]:
    present = df["scenario"].dropna().unique().tolist()
    return [s for s in SCENARIO_ORDER if s in present] + [
        s for s in present if s not in SCENARIO_ORDER
    ]


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## GA-ACO CVRP")
    st.caption("Dashboard · Defensa de Tesis")
    st.divider()
    st.markdown(
        """
**Problema:** Ruteo de vehículos con ventanas de tiempo (CVRP/VRPTW)
**Zona:** Arteaga-Saltillo, Coahuila
**Instancia:** 1 CEDIS + 8 tiendas OXXO
**Capacidad:** 15 000 kg · 1 vehículo
**Corridas por benchmark:** 10 000

---
**Algoritmos:**
· GA — Algoritmo Genético
· ACO — Colonia de Hormigas
· Híbrido — GA inicializa ACO
"""
    )
    st.divider()
    master = _load_master()
    if master is not None:
        n_sc   = master["scenario"].nunique()
        n_solv = master["solver"].nunique()
        n_rows = len(master)
        st.success(f"{n_rows} benchmarks · {n_sc} escenarios · {n_solv} algoritmos")
    st.divider()
    st.caption("Solo localhost · Sin acceso externo")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_resumen, tab_instancia, tab_comparativo, tab_rutas = st.tabs(
    ["Resumen", "Instancia", "Comparativo", "Rutas"]
)


# ══════════════════════════════════════════════════════════════════════════════
#  RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
with tab_resumen:
    st.header("Resumen del Proyecto")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodos", "9", "1 CEDIS + 8 tiendas")
    c2.metric("Algoritmos", "3", "GA · ACO · Híbrido")
    c3.metric("Escenarios", "5", "Base → Estrés Total")
    c4.metric("Corridas por benchmark", "10 000")

    st.divider()

    col_desc, col_params = st.columns([3, 2])

    with col_desc:
        st.subheader("Descripción del problema")
        st.markdown(
            """
El proyecto resuelve una variante del **CVRP/VRPTW** para la distribución de
mercancía desde un Centro de Distribución (CEDIS) a 8 tiendas OXXO en la zona
Arteaga-Saltillo, usando una matriz de tiempos y distancias obtenida de la red
vial real mediante OpenRouteService.

**Función objetivo:**

$$f = d_{km} \\;+\\; 200 \\cdot T_{tarde} \\;+\\; 0.5 \\cdot V_{cap} \\;+\\; 5000 \\cdot V_{veh}$$

En escenarios sin tardanza: $f \\approx$ distancia total recorrida.
En escenarios extremos: la tardanza domina la función y la operación se vuelve
inviable con un único vehículo.
"""
        )

    with col_params:
        st.subheader("Parámetros")
        params = [
            ("Peso por bulto",              "7 kg"),
            ("Capacidad del vehículo",      "15 000 kg"),
            ("Máx. vehículos",              "1"),
            ("Velocidad base (respaldo)",   "35 km/h"),
            ("Penalización tardanza",       "200 $/min"),
            ("Penalización capacidad extra","0.5 $/kg"),
            ("Penalización vehículo extra", "5 000 $"),
            ("Corridas / benchmark",        "10 000"),
        ]
        for k, v in params:
            ka, va = st.columns([3, 2])
            ka.write(f"**{k}**")
            va.write(v)

    st.divider()
    st.subheader("Escenarios experimentales")
    sc_df = pd.DataFrame(
        {
            "ID": [1, 2, 3, 4, 5],
            "Escenario": ["Base", "Hora Pico", "Tienda Congestionada", "Estrés", "Estrés Total"],
            "traffic_factor": ["1.0 ×", "2.0 ×", "1.0 ×", "4.0 ×", "10.0 ×"],
            "service_extra": ["—", "—", "+15 min/tienda", "—", "—"],
            "Descripción": [
                "Condiciones operativas normales",
                "Tiempos de tránsito duplicados",
                "+15 min de atención por tienda",
                "Tránsito cuadruplicado — alta congestión",
                "Tránsito ×10 — prueba de límite operacional",
            ],
        }
    )
    st.dataframe(sc_df, use_container_width=True, hide_index=True)

    if master is not None:
        st.divider()
        st.subheader("Objetivo medio por escenario y algoritmo")
        agg = (
            master.groupby(["scenario", "solver_label"], observed=True)
            .agg(mu=("objective_mean", "mean"), sigma=("objective_stdev", "mean"))
            .reset_index()
        )
        fig_res = px.bar(
            agg.sort_values("scenario"),
            x="scenario",
            y="mu",
            color="solver_label",
            barmode="group",
            error_y="sigma",
            color_discrete_map=SOLVER_COLORS,
            labels={"mu": "Objetivo promedio", "scenario": "", "solver_label": "Algoritmo"},
            height=420,
        )
        fig_res.update_xaxes(tickangle=12)
        fig_res.update_layout(
            legend=dict(orientation="h", y=1.08),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_res, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  INSTANCIA
# ══════════════════════════════════════════════════════════════════════════════
with tab_instancia:
    st.header("Instancia del Problema")
    nodes = _load_nodes()

    if nodes is None:
        st.error("No se encontró data/dataset_artegasaltillo.csv")
    else:
        stores  = nodes[nodes["node_type"] == "store"].sort_values("id").reset_index(drop=True)
        depot   = nodes[nodes["node_type"] == "depot"].iloc[0]

        col_tabla, col_mapa = st.columns([2, 3])

        with col_tabla:
            st.subheader("Nodos de la instancia")
            disp = stores[[
                "id", "name", "demand", "demand_kg",
                "tw_start_fmt", "tw_end_fmt", "service_time",
            ]].rename(columns={
                "id":           "ID",
                "name":         "Tienda",
                "demand":       "Bultos",
                "demand_kg":    "kg",
                "tw_start_fmt": "Apertura",
                "tw_end_fmt":   "Cierre",
                "service_time": "T. Serv. (min)",
            })
            st.dataframe(disp, use_container_width=True, hide_index=True)

            total_b  = int(stores["demand"].sum())
            total_kg = stores["demand_kg"].sum()
            cap      = 15_000.0

            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("Demanda total", f"{total_b} bultos", f"{total_kg:.0f} kg")
            m2.metric("Utilización", f"{total_kg / cap * 100:.1f}%", f"{total_kg:.0f} / {cap:.0f} kg")

            st.caption(
                "CEDIS Saltillo: depot (nodo 0) · "
                "Velocidad base: 35 km/h · "
                "Capacidad: 15 000 kg · "
                "Peso/bulto: 7 kg"
            )

        with col_mapa:
            st.subheader("Ubicación geográfica")
            all_nodes = nodes.copy()
            all_nodes["tipo"] = all_nodes["node_type"].map({"depot": "CEDIS", "store": "Tienda OXXO"})
            all_nodes["tamaño"] = all_nodes["node_type"].map({"depot": 22, "store": 14})
            fig_map = px.scatter_mapbox(
                all_nodes,
                lat="lat", lon="lon",
                hover_name="name",
                hover_data={
                    "demand": True,
                    "demand_kg": True,
                    "tw_start_fmt": True,
                    "tw_end_fmt": True,
                    "lat": False,
                    "lon": False,
                    "tipo": False,
                    "tamaño": False,
                },
                color="tipo",
                color_discrete_map={"CEDIS": "#DC2626", "Tienda OXXO": "#1D4ED8"},
                size="tamaño",
                zoom=11,
                mapbox_style="open-street-map",
                height=460,
                labels={"tipo": ""},
            )
            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                legend=dict(orientation="h", y=1.02),
            )
            st.plotly_chart(fig_map, use_container_width=True)

        st.divider()
        st.subheader("Ventanas de tiempo por tienda (formato 24 h)")
        st.caption(
            "Cada barra representa la ventana de atención. "
            "El vehículo debe llegar dentro de este rango; "
            "si llega antes espera, si llega después incurre en tardanza penalizada."
        )

        # Ventanas de tiempo — un registro por tienda, barras horizontales
        tw_data = []
        for _, row in stores.iterrows():
            tw_data.append({
                "Tienda":    row["name"].replace("OXXO ", ""),
                "Apertura":  row["tw_start_h"],
                "Cierre":    row["tw_end_h"],
                "Duración":  row["tw_end_h"] - row["tw_start_h"],
                "Etiqueta":  f"{row['tw_start_fmt']} – {row['tw_end_fmt']}  ({row['service_time']} min serv.)",
            })
        tw_df = pd.DataFrame(tw_data)

        fig_tw = go.Figure()
        # Barra invisible de base (desde 0 hasta apertura) para posicionar la real
        fig_tw.add_trace(
            go.Bar(
                name="",
                y=tw_df["Tienda"],
                x=tw_df["Apertura"],
                orientation="h",
                marker_color="rgba(0,0,0,0)",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Barra visible: duración de la ventana
        fig_tw.add_trace(
            go.Bar(
                name="Ventana de tiempo",
                y=tw_df["Tienda"],
                x=tw_df["Duración"],
                orientation="h",
                marker_color="#1D4ED8",
                opacity=0.75,
                text=tw_df["Etiqueta"],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate="%{y}<br>%{text}<extra></extra>",
            )
        )
        fig_tw.update_layout(
            barmode="stack",
            xaxis=dict(
                title="Hora del día",
                range=[0, 24],
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
            ),
            yaxis=dict(title=""),
            height=380,
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            margin={"l": 120, "r": 20, "t": 20, "b": 40},
        )
        st.plotly_chart(fig_tw, use_container_width=True)

        # Tabla de verificación de ventanas
        st.subheader("Verificación de ventanas de tiempo")
        ver_df = stores[[
            "name", "tw_start_fmt", "tw_end_fmt", "service_time", "demand", "demand_kg"
        ]].rename(columns={
            "name":         "Tienda",
            "tw_start_fmt": "Apertura",
            "tw_end_fmt":   "Cierre",
            "service_time": "Serv. (min)",
            "demand":       "Bultos",
            "demand_kg":    "kg",
        })
        st.dataframe(ver_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COMPARATIVO
# ══════════════════════════════════════════════════════════════════════════════
with tab_comparativo:
    st.header("Resultados Comparativos")

    if master is None:
        st.error(
            "No se encontró la tabla de resultados. "
            "Ejecuta `python consolidate_results.py` antes de abrir el dashboard."
        )
    else:
        sc_opts = _sorted_scenarios(master)
        sel_sc  = st.selectbox(
            "Filtrar por escenario:",
            ["Todos"] + sc_opts,
            key="comp_sc",
        )
        df_c = master if sel_sc == "Todos" else master[master["scenario"] == sel_sc]

        # Tabla estadística principal
        st.subheader("Estadísticas por escenario y algoritmo")
        tbl = df_c[[
            "scenario", "solver_label",
            "objective_mean", "objective_stdev",
            "objective_best", "objective_worst",
            "km_mean", "late_mean",
            "wait_mean", "route_time_mean",
            "runtime_mean",
        ]].rename(columns={
            "scenario":        "Escenario",
            "solver_label":    "Algoritmo",
            "objective_mean":  "Obj. μ",
            "objective_stdev": "Obj. σ",
            "objective_best":  "Obj. mín.",
            "objective_worst": "Obj. máx.",
            "km_mean":         "km μ",
            "late_mean":       "Tarde μ (min)",
            "wait_mean":       "Espera μ (min)",
            "route_time_mean": "T. Ruta μ (min)",
            "runtime_mean":    "Runtime μ (s)",
        })
        st.dataframe(
            tbl.sort_values(["Escenario", "Obj. μ"]).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        def _bar(df, y, title, ytitle):
            agg = (
                df.groupby(["scenario", "solver_label"], observed=True)[y]
                .mean()
                .reset_index()
                .rename(columns={y: ytitle})
            )
            fig = px.bar(
                agg.sort_values("scenario"),
                x="scenario",
                y=ytitle,
                color="solver_label",
                barmode="group",
                color_discrete_map=SOLVER_COLORS,
                labels={"solver_label": "Algoritmo", "scenario": ""},
                title=title,
                height=360,
            )
            fig.update_xaxes(tickangle=12)
            fig.update_layout(
                legend=dict(orientation="h", y=1.1),
                plot_bgcolor="white",
                paper_bgcolor="white",
            )
            return fig

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(_bar(df_c, "objective_mean", "Objetivo medio", "Objetivo μ"), use_container_width=True)
        with c2:
            st.plotly_chart(_bar(df_c, "route_time_mean", "Tiempo de ruta (min)", "T. Ruta μ"), use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(_bar(df_c, "late_mean", "Tardanza media (min)", "Tardanza μ"), use_container_width=True)
        with c4:
            st.plotly_chart(_bar(df_c, "km_mean", "Distancia media (km)", "km μ"), use_container_width=True)

        c5, c6 = st.columns(2)
        with c5:
            st.plotly_chart(_bar(df_c, "wait_mean", "Espera media (min)", "Espera μ"), use_container_width=True)
        with c6:
            st.plotly_chart(_bar(df_c, "runtime_mean", "Runtime medio (s)", "Runtime μ"), use_container_width=True)

        # Heatmap objetivo (siempre visible, no opcional)
        st.divider()
        st.subheader("Heatmap — Objetivo medio por algoritmo y escenario")
        pivot_obj = (
            master.groupby(["solver_label", "scenario"], observed=True)["objective_mean"]
            .mean()
            .unstack("scenario")
        )
        sc_ord = [s for s in SCENARIO_ORDER if s in pivot_obj.columns] + [
            c for c in pivot_obj.columns if c not in SCENARIO_ORDER
        ]
        pivot_obj = pivot_obj[sc_ord]

        fig_hm = px.imshow(
            pivot_obj.values,
            x=list(pivot_obj.columns),
            y=list(pivot_obj.index),
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Blues",
            labels={"x": "Escenario", "y": "Algoritmo", "color": "Objetivo μ"},
            height=280,
        )
        fig_hm.update_xaxes(tickangle=15)
        fig_hm.update_layout(margin={"t": 20, "b": 10})
        st.plotly_chart(fig_hm, use_container_width=True)

        # Heatmap tardanza
        st.subheader("Heatmap — Tardanza media (min) por algoritmo y escenario")
        pivot_late = (
            master.groupby(["solver_label", "scenario"], observed=True)["late_mean"]
            .mean()
            .unstack("scenario")
        )
        sc_ord2 = [s for s in SCENARIO_ORDER if s in pivot_late.columns] + [
            c for c in pivot_late.columns if c not in SCENARIO_ORDER
        ]
        pivot_late = pivot_late[sc_ord2]

        fig_hm2 = px.imshow(
            pivot_late.values,
            x=list(pivot_late.columns),
            y=list(pivot_late.index),
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="Reds",
            labels={"x": "Escenario", "y": "Algoritmo", "color": "Tardanza μ (min)"},
            height=280,
        )
        fig_hm2.update_xaxes(tickangle=15)
        fig_hm2.update_layout(margin={"t": 20, "b": 10})
        st.plotly_chart(fig_hm2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_rutas:
    st.header("Red de Distribución y Rutas")

    nodes_r = _load_nodes()
    if nodes_r is None:
        st.error("No se encontró data/dataset_artegasaltillo.csv")
    else:
        depot_r  = nodes_r[nodes_r["node_type"] == "depot"].iloc[0]
        stores_r = nodes_r[nodes_r["node_type"] == "store"].sort_values("id").reset_index(drop=True)

        routes = _load_routes()

        if routes:
            # Si hay rutas generadas, ofrecer selector
            sc_names = [r.get("scenario", f"Ruta {i+1}") for i, r in enumerate(routes)]
            alg_names = [r.get("solver", "?").upper() for r in routes]
            labels = [f"{sc} — {alg}" for sc, alg in zip(sc_names, alg_names)]

            sel_route_idx = st.selectbox(
                "Seleccionar ruta para visualizar:",
                options=range(len(routes)),
                format_func=lambda i: labels[i],
                key="route_sel",
            )
            route_data = routes[sel_route_idx]

            # Métricas de la ruta seleccionada
            m = route_data.get("metrics", {})
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Objetivo", f"{m.get('objective', 0):.2f}")
            c2.metric("Distancia", f"{m.get('total_km', 0):.2f} km")
            c3.metric("Tardanza", f"{m.get('late_minutes', 0):.1f} min")
            c4.metric("Espera", f"{m.get('wait_minutes', 0):.1f} min")
            c5.metric("T. Ruta", f"{m.get('route_time_minutes', 0):.1f} min")

            st.divider()

            # Construir mapa con la ruta real
            fig_r = go.Figure()
            node_coords = {nc["id"]: nc for nc in route_data.get("node_coords", [])}

            for veh in route_data.get("routes", []):
                stops = veh.get("stops", [])
                lats = [node_coords[s]["lat"] for s in stops if s in node_coords]
                lons = [node_coords[s]["lon"] for s in stops if s in node_coords]
                names = [node_coords[s]["name"] for s in stops if s in node_coords]
                if lats:
                    fig_r.add_trace(
                        go.Scattermapbox(
                            lat=lats,
                            lon=lons,
                            mode="lines+markers",
                            line=dict(width=3, color="#1D4ED8"),
                            marker=dict(size=10, color="#1D4ED8"),
                            name=f"Vehículo {veh.get('vehicle', 1)}",
                            hovertext=names,
                            hoverinfo="text",
                        )
                    )

        else:
            # Sin rutas generadas: mostrar solo nodos y conectividad
            fig_r = go.Figure()

        # Aristas CEDIS → tienda (siempre)
        for _, s in stores_r.iterrows():
            fig_r.add_trace(
                go.Scattermapbox(
                    lat=[depot_r["lat"], s["lat"]],
                    lon=[depot_r["lon"], s["lon"]],
                    mode="lines",
                    line=dict(width=1, color="#94A3B8"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # Tiendas
        fig_r.add_trace(
            go.Scattermapbox(
                lat=stores_r["lat"],
                lon=stores_r["lon"],
                mode="markers+text",
                marker=dict(size=16, color="#1D4ED8"),
                text=stores_r["name"].str.replace("OXXO ", "", regex=False),
                textposition="top center",
                name="Tiendas OXXO",
                hovertext=[
                    f"<b>{r['name']}</b><br>"
                    f"Demanda: {r['demand']} bultos · {r['demand_kg']:.0f} kg<br>"
                    f"Ventana: {r['tw_start_fmt']} – {r['tw_end_fmt']}<br>"
                    f"T. servicio: {r['service_time']} min"
                    for _, r in stores_r.iterrows()
                ],
                hoverinfo="text",
            )
        )

        # CEDIS
        fig_r.add_trace(
            go.Scattermapbox(
                lat=[depot_r["lat"]],
                lon=[depot_r["lon"]],
                mode="markers+text",
                marker=dict(size=24, color="#DC2626"),
                text=["CEDIS"],
                textposition="top right",
                name="CEDIS Saltillo",
                hovertext="CEDIS Saltillo",
                hoverinfo="text",
            )
        )

        fig_r.update_layout(
            mapbox_style="open-street-map",
            mapbox_zoom=11,
            mapbox_center={
                "lat": nodes_r["lat"].mean(),
                "lon": nodes_r["lon"].mean(),
            },
            height=540,
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend=dict(orientation="h", y=1.02),
        )
        st.plotly_chart(fig_r, use_container_width=True)

        # Tabla de ruta detallada (si hay ruta seleccionada)
        if routes:
            st.subheader("Detalle de la ruta")
            for veh in route_data.get("routes", []):
                st.write(
                    f"**Vehículo {veh.get('vehicle', 1)}** — "
                    f"{veh.get('load_bultos', 0)} bultos · "
                    f"{veh.get('load_kg', 0):.0f} kg"
                )
                st.write(" → ".join(veh.get("stop_names", [])))
        else:
            st.caption(
                "Para visualizar rutas concretas, ejecuta: "
                "`python generate_best_routes.py`"
            )

        # Estadísticas de la instancia
        st.divider()
        st.subheader("Estadísticas de la instancia")
        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Nodos totales", len(nodes_r))
        ic2.metric("Demanda total", f"{int(stores_r['demand'].sum())} bultos")
        ic3.metric("Carga total", f"{stores_r['demand_kg'].sum():.0f} kg")
        ic4.metric("Utilización del vehículo", f"{stores_r['demand_kg'].sum() / 15000 * 100:.1f}%")
