"""
dashboard.py — GA-ACO CVRP · Dashboard de Defensa de Tesis
===========================================================
Ejecutar (solo localhost):
    streamlit run dashboard.py --server.address=localhost --server.port=8501

Requiere:
    pip install -r requirements.txt

Preparar antes de ejecutar:
    python consolidate_results.py
    python generate_best_routes.py

Notas técnicas:
    - DEFENSE_MODE = True  →  solo usa los 15 benchmarks con metadata explícita
    - Mapas migrados a go.Scattermap / px.scatter_map (plotly >= 5.18, sin token Mapbox)
      Layout: map=dict(style="open-street-map", zoom=..., center=...)
      vs. API anterior: mapbox_style=... / mapbox_zoom=... / mapbox_center=...
    - use_container_width=True  sigue siendo la API recomendada en Streamlit <= 1.40
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Modo defensa ──────────────────────────────────────────────────────────────
# True  → solo muestra las 15 entradas con label_source == "explicit"
# False → muestra todos los benchmarks (incluyendo inferidos y por carpeta)
DEFENSE_MODE: bool = True

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent
DATA_CSV    = BASE / "data" / "dataset_artegasaltillo.csv"
MASTER_CSV  = BASE / "assets" / "master_benchmarks.csv"
ROUTES_DIR  = BASE / "assets" / "routes"

# Mapeo nombre de escenario → parte del nombre de archivo de ruta
_SC_TO_FILE: dict[str, str] = {
    "Base":                  "base",
    "Hora Pico":             "hora_pico",
    "Tienda Congestionada":  "congestion_tienda",
    "Estrés":                "estres",
    "Estrés Total":          "estres_total",
}
_ALG_TO_FILE: dict[str, str] = {
    "GA":             "ga",
    "ACO":            "aco",
    "Híbrido GA-ACO": "hybrid",
}

SOLVER_LABELS: dict[str, str] = {"ga": "GA", "aco": "ACO", "hybrid": "Híbrido GA-ACO"}
SOLVER_COLORS: dict[str, str] = {
    "GA":             "#1D4ED8",
    "ACO":            "#B45309",
    "Híbrido GA-ACO": "#15803D",
}
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
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] { background: #1E293B; }
    section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] strong { color: #F8FAFC !important; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 600; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 500; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helpers de formato ────────────────────────────────────────────────────────
def _hhmm(minutes: int | float) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"


# ── Carga de datos con caché ──────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load_master() -> pd.DataFrame | None:
    if not MASTER_CSV.exists():
        return None
    df = pd.read_csv(MASTER_CSV)
    if DEFENSE_MODE:
        df = df[df["label_source"] == "explicit"].copy()
    df["solver_label"] = df["solver"].map(SOLVER_LABELS).fillna(df["solver"])
    order = SCENARIO_ORDER + [s for s in df["scenario"].unique() if s not in SCENARIO_ORDER]
    df["scenario"] = pd.Categorical(df["scenario"], categories=order, ordered=True)
    return df if not df.empty else None


@st.cache_data(show_spinner=False)
def _load_nodes() -> pd.DataFrame | None:
    if not DATA_CSV.exists():
        return None
    df = pd.read_csv(DATA_CSV)
    df["tw_start_fmt"] = df["tw_start"].apply(_hhmm)
    df["tw_end_fmt"]   = df["tw_end"].apply(_hhmm)
    df["tw_start_h"]   = df["tw_start"] / 60.0
    df["tw_end_h"]     = df["tw_end"]   / 60.0
    df["demand_kg"]    = df["demand"] * 7.0
    return df


@st.cache_data(show_spinner=False)
def _load_route(scenario_label: str, alg_label: str) -> dict | None:
    sc_key  = _SC_TO_FILE.get(scenario_label, "")
    alg_key = _ALG_TO_FILE.get(alg_label, "")
    if not sc_key or not alg_key:
        return None
    fp = ROUTES_DIR / f"best_route_{sc_key}_{alg_key}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sorted_scenarios(df: pd.DataFrame) -> list[str]:
    present = df["scenario"].dropna().unique().tolist()
    return [s for s in SCENARIO_ORDER if s in present]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## GA-ACO CVRP")
    st.caption("Dashboard · Defensa de Tesis")
    st.divider()
    st.markdown(
        """
**Problema**
Ruteo de vehículos con capacidad y ventanas de tiempo (CVRP/VRPTW)

**Instancia**
1 CEDIS + 8 tiendas OXXO
Zona Arteaga-Saltillo, Coahuila

**Configuración**
· Capacidad: 15 000 kg
· Vehículos: 1
· Corridas por benchmark: 10 000

**Algoritmos**
· GA — Algoritmo Genético
· ACO — Colonia de Hormigas
· Híbrido — GA inicializa ACO
"""
    )
    st.divider()
    _m = _load_master()
    if _m is not None:
        st.success(
            f"{len(_m)} benchmarks · "
            f"{_m['scenario'].nunique()} escenarios · "
            f"{_m['solver'].nunique()} algoritmos"
        )
    st.divider()
    st.caption("Solo localhost · Sin acceso externo")


# ── Pestañas ──────────────────────────────────────────────────────────────────
tab_resumen, tab_instancia, tab_comparativo, tab_rutas = st.tabs(
    ["Resumen", "Instancia", "Comparativo", "Rutas"]
)


# ══════════════════════════════════════════════════════════════════════════════
#  RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
with tab_resumen:
    st.header("Resumen del Proyecto")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nodos",              "9",       "1 CEDIS + 8 tiendas")
    c2.metric("Algoritmos",         "3",       "GA · ACO · Híbrido")
    c3.metric("Escenarios",         "5",       "Base → Estrés Total")
    c4.metric("Corridas/benchmark", "10 000",  "seed incremental")

    st.divider()

    col_desc, col_params = st.columns([3, 2])
    with col_desc:
        st.subheader("Descripción del problema")
        st.markdown(
            """
Se resuelve una variante del **CVRP/VRPTW** (Capacitated Vehicle Routing Problem
with Time Windows) para la distribución de mercancía desde un Centro de Distribución
a 8 tiendas OXXO en la zona Arteaga-Saltillo, usando datos de la red vial real
obtenidos mediante **OpenRouteService**.

**Función objetivo:**

$$f = d_{km} \\;+\\; 200 \\cdot T_{tarde} \\;+\\; 0.5 \\cdot V_{cap} \\;+\\; 5000 \\cdot V_{veh}$$

En escenarios sin tardanza: $f \\approx$ distancia total recorrida.
En escenarios extremos (Estrés Total): la tardanza domina completamente la función.
"""
        )

    with col_params:
        st.subheader("Parámetros del experimento")
        rows_p = [
            ("Peso por bulto",               "7 kg"),
            ("Capacidad del vehículo",       "15 000 kg"),
            ("Máximo de vehículos",          "1"),
            ("Velocidad base",               "35 km/h"),
            ("Penalización tardanza",        "200 $/min"),
            ("Penalización capacidad extra", "0.5 $/kg"),
            ("Penalización vehículo extra",  "5 000 $"),
            ("Corridas por benchmark",       "10 000"),
        ]
        for k, v in rows_p:
            ka, va = st.columns([3, 2])
            ka.write(f"**{k}**")
            va.write(v)

    st.divider()
    st.subheader("Escenarios evaluados")
    sc_tbl = pd.DataFrame({
        "ID":              [1, 2, 3, 4, 5],
        "Escenario":       ["Base", "Hora Pico", "Tienda Congestionada", "Estrés", "Estrés Total"],
        "traffic_factor":  ["1.0 ×", "2.0 ×", "1.0 ×", "4.0 ×", "10.0 ×"],
        "service_extra":   ["—", "—", "+15 min/tienda", "—", "—"],
        "Descripción":     [
            "Condiciones operativas normales",
            "Tiempos de tránsito duplicados",
            "+15 min de atención por tienda",
            "Tránsito ×4 — alta congestión",
            "Tránsito ×10 — prueba de límite operacional",
        ],
    })
    st.dataframe(sc_tbl, use_container_width=True, hide_index=True)

    master = _load_master()
    if master is not None:
        st.divider()
        st.subheader("Objetivo medio por escenario y algoritmo")
        agg_res = (
            master.groupby(["scenario", "solver_label"], observed=True)
            .agg(mu=("objective_mean", "mean"), sigma=("objective_stdev", "mean"))
            .reset_index()
        )
        fig_res = px.bar(
            agg_res.sort_values("scenario"),
            x="scenario", y="mu", color="solver_label",
            barmode="group", error_y="sigma",
            color_discrete_map=SOLVER_COLORS,
            labels={"mu": "Objetivo promedio", "scenario": "Escenario", "solver_label": "Algoritmo"},
            height=420,
        )
        fig_res.update_xaxes(tickangle=12)
        fig_res.update_layout(
            legend=dict(orientation="h", y=1.10, title_text=""),
            plot_bgcolor="white",
            paper_bgcolor="white",
            yaxis=dict(gridcolor="#E5E7EB"),
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
        stores = nodes[nodes["node_type"] == "store"].sort_values("id").reset_index(drop=True)
        depot  = nodes[nodes["node_type"] == "depot"].iloc[0]

        col_tbl, col_map = st.columns([2, 3])

        with col_tbl:
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
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("Demanda total",  f"{total_b} bultos", f"{total_kg:.0f} kg")
            m2.metric("Utilización",    f"{total_kg / 15000 * 100:.1f}%",
                                        f"{total_kg:.0f} / 15 000 kg")

        with col_map:
            st.subheader("Ubicación geográfica — Arteaga-Saltillo")
            all_nd = nodes.copy()
            all_nd["Tipo"]  = all_nd["node_type"].str.strip().map(
                {"depot": "CEDIS", "store": "Tienda OXXO"}
            )
            all_nd["_sz"]   = all_nd["node_type"].str.strip().map({"depot": 22, "store": 14})
            # Migrado: scatter_map (plotly >= 5.18, sin token Mapbox)
            fig_map = px.scatter_map(
                all_nd,
                lat="lat", lon="lon",
                hover_name="name",
                hover_data={
                    "demand":       True,
                    "demand_kg":    True,
                    "tw_start_fmt": True,
                    "tw_end_fmt":   True,
                    "lat": False, "lon": False,
                    "Tipo": False, "_sz": False,
                },
                color="Tipo",
                color_discrete_map={"CEDIS": "#DC2626", "Tienda OXXO": "#1D4ED8"},
                size="_sz",
                zoom=11,
                height=460,
                labels={"Tipo": ""},
            )
            fig_map.update_layout(
                map=dict(style="open-street-map", zoom=11,
                         center=dict(lat=all_nd["lat"].mean(), lon=all_nd["lon"].mean())),
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                legend=dict(orientation="h", y=1.03),
            )
            st.plotly_chart(fig_map, use_container_width=True)

        st.divider()
        st.subheader("Ventanas de tiempo por tienda (escala 24 h)")

        # Barras horizontales: base invisible + barra de duración visible
        fig_tw = go.Figure()
        fig_tw.add_trace(go.Bar(
            y=stores["name"].str.replace("OXXO ", "", regex=False),
            x=stores["tw_start_h"],
            orientation="h",
            marker_color="rgba(0,0,0,0)",
            showlegend=False,
            hoverinfo="skip",
        ))
        fig_tw.add_trace(go.Bar(
            y=stores["name"].str.replace("OXXO ", "", regex=False),
            x=stores["tw_end_h"] - stores["tw_start_h"],
            orientation="h",
            marker_color="#1D4ED8",
            opacity=0.70,
            text=[
                f"{r['tw_start_fmt']} – {r['tw_end_fmt']}  ·  serv. {r['service_time']} min"
                for _, r in stores.iterrows()
            ],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="%{y}<br>%{text}<extra></extra>",
            showlegend=False,
        ))
        fig_tw.update_layout(
            barmode="stack",
            xaxis=dict(
                title="Hora del día",
                range=[0, 24],
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
                gridcolor="#E5E7EB",
            ),
            yaxis=dict(title="", autorange="reversed"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=360,
            margin={"l": 130, "r": 20, "t": 10, "b": 50},
        )
        st.plotly_chart(fig_tw, use_container_width=True)

        st.subheader("Tabla de verificación de ventanas")
        vtbl = stores[[
            "name", "tw_start_fmt", "tw_end_fmt", "service_time", "demand", "demand_kg"
        ]].rename(columns={
            "name":         "Tienda",
            "tw_start_fmt": "Apertura",
            "tw_end_fmt":   "Cierre",
            "service_time": "Serv. (min)",
            "demand":       "Bultos",
            "demand_kg":    "kg",
        })
        st.dataframe(vtbl, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COMPARATIVO
# ══════════════════════════════════════════════════════════════════════════════
with tab_comparativo:
    st.header("Resultados Comparativos")

    master = _load_master()
    if master is None:
        st.error(
            "No se encontró la tabla de resultados. "
            "Ejecuta primero: python consolidate_results.py"
        )
    else:
        sc_opts = _sorted_scenarios(master)
        sel_sc  = st.selectbox("Filtrar por escenario:", ["Todos"] + sc_opts, key="cmp_sc")
        df_c    = master if sel_sc == "Todos" else master[master["scenario"] == sel_sc]

        # ── Tabla estadística ──────────────────────────────────────────────
        st.subheader("Estadísticas por escenario y algoritmo")
        tbl_df = df_c[[
            "scenario", "solver_label",
            "objective_mean", "objective_stdev",
            "objective_best", "objective_worst",
            "km_mean", "late_mean", "wait_mean",
            "route_time_mean", "runtime_mean",
        ]].rename(columns={
            "scenario":        "Escenario",
            "solver_label":    "Algoritmo",
            "objective_mean":  "Obj. μ",
            "objective_stdev": "Obj. σ",
            "objective_best":  "Mín.",
            "objective_worst": "Máx.",
            "km_mean":         "km μ",
            "late_mean":       "Tarde μ (min)",
            "wait_mean":       "Espera μ (min)",
            "route_time_mean": "T. Ruta μ (min)",
            "runtime_mean":    "Runtime μ (s)",
        })
        st.dataframe(
            tbl_df.sort_values(["Escenario", "Obj. μ"]).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ── Función auxiliar para barras agrupadas ─────────────────────────
        def _bar_chart(df: pd.DataFrame, col: str, title: str, ytitle: str) -> go.Figure:
            agg = (
                df.groupby(["scenario", "solver_label"], observed=True)[col]
                .mean()
                .reset_index()
                .rename(columns={col: ytitle})
            )
            fig = px.bar(
                agg.sort_values("scenario"),
                x="scenario", y=ytitle,
                color="solver_label",
                barmode="group",
                color_discrete_map=SOLVER_COLORS,
                labels={"solver_label": "Algoritmo", "scenario": ""},
                title=title,
                height=340,
            )
            fig.update_xaxes(tickangle=12)
            fig.update_layout(
                legend=dict(orientation="h", y=1.12, title_text=""),
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis=dict(gridcolor="#E5E7EB"),
                margin={"t": 50},
            )
            return fig

        # ── 6 gráficas en 2 columnas ───────────────────────────────────────
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.plotly_chart(
                _bar_chart(df_c, "objective_mean", "Objetivo medio", "Objetivo μ"),
                use_container_width=True,
            )
        with r1c2:
            st.plotly_chart(
                _bar_chart(df_c, "km_mean", "Distancia media (km)", "km μ"),
                use_container_width=True,
            )

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.plotly_chart(
                _bar_chart(df_c, "late_mean", "Tardanza media (min)", "Tarde μ"),
                use_container_width=True,
            )
        with r2c2:
            st.plotly_chart(
                _bar_chart(df_c, "wait_mean", "Espera media (min)", "Espera μ"),
                use_container_width=True,
            )

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.plotly_chart(
                _bar_chart(df_c, "route_time_mean", "Tiempo de ruta (min)", "T. Ruta μ"),
                use_container_width=True,
            )
        with r3c2:
            st.plotly_chart(
                _bar_chart(df_c, "runtime_mean", "Runtime medio (s)", "Runtime μ"),
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_rutas:
    st.header("Rutas Óptimas")

    nodes_r = _load_nodes()
    if nodes_r is None:
        st.error("No se encontró data/dataset_artegasaltillo.csv")
    else:
        depot_r  = nodes_r[nodes_r["node_type"] == "depot"].iloc[0]
        stores_r = nodes_r[nodes_r["node_type"] == "store"].sort_values("id").reset_index(drop=True)

        # ── Selectores ────────────────────────────────────────────────────
        sel_col1, sel_col2 = st.columns(2)
        with sel_col1:
            sel_sc_r = st.selectbox(
                "Escenario:",
                options=list(_SC_TO_FILE.keys()),
                key="ruta_sc",
            )
        with sel_col2:
            sel_alg_r = st.selectbox(
                "Algoritmo:",
                options=list(_ALG_TO_FILE.keys()),
                key="ruta_alg",
            )

        route_data = _load_route(sel_sc_r, sel_alg_r)

        st.divider()

        if route_data is not None:
            # ── Métricas de la ruta ────────────────────────────────────────
            m = route_data.get("metrics", {})
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Objetivo",      f"{m.get('objective', 0):.2f}")
            mc2.metric("Distancia",     f"{m.get('total_km', 0):.2f} km")
            mc3.metric("Tardanza",      f"{m.get('late_minutes', 0):.1f} min")
            mc4.metric("Espera",        f"{m.get('wait_minutes', 0):.1f} min")
            mc5.metric("Tiempo ruta",   f"{m.get('route_time_minutes', 0):.1f} min")

            st.divider()

            # ── Construcción del mapa de ruta ──────────────────────────────
            node_coords: dict[int, dict] = {
                nc["id"]: nc
                for nc in route_data.get("node_coords", [])
            }

            fig_route = go.Figure()

            # Dibujar la ruta de cada vehículo
            route_colors = ["#1D4ED8", "#15803D", "#B45309"]
            for veh_idx, veh in enumerate(route_data.get("routes", [])):
                stops    = veh.get("stops", [])
                stop_nc  = [node_coords[s] for s in stops if s in node_coords]
                if not stop_nc:
                    continue
                lats  = [n["lat"] for n in stop_nc]
                lons  = [n["lon"] for n in stop_nc]
                names = [n["name"].replace("OXXO ", "") for n in stop_nc]
                color = route_colors[veh_idx % len(route_colors)]
                # Línea de ruta
                fig_route.add_trace(go.Scattermap(
                    lat=lats, lon=lons,
                    mode="lines",
                    line=dict(width=3, color=color),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                # Puntos con número de orden
                for order_i, (lat, lon, name) in enumerate(zip(lats, lons, names)):
                    is_depot = (order_i == 0 or order_i == len(lats) - 1)
                    if is_depot:
                        continue
                    fig_route.add_trace(go.Scattermap(
                        lat=[lat], lon=[lon],
                        mode="markers+text",
                        marker=dict(size=18, color=color),
                        text=[f"{order_i}"],
                        textposition="middle center",
                        textfont=dict(color="white", size=11, family="Arial Black"),
                        name=name,
                        hovertext=f"<b>Parada {order_i}</b><br>{name}",
                        hoverinfo="text",
                        showlegend=False,
                    ))

            # CEDIS (siempre visible)
            fig_route.add_trace(go.Scattermap(
                lat=[depot_r["lat"]], lon=[depot_r["lon"]],
                mode="markers+text",
                marker=dict(size=26, color="#DC2626"),
                text=["CEDIS"],
                textposition="top right",
                textfont=dict(color="#1E293B", size=11),
                name="CEDIS Saltillo",
                hovertext="CEDIS Saltillo — Punto de origen y destino",
                hoverinfo="text",
                showlegend=True,
            ))

            fig_route.update_layout(
                map=dict(
                    style="open-street-map",
                    zoom=11,
                    center=dict(
                        lat=nodes_r["lat"].mean(),
                        lon=nodes_r["lon"].mean(),
                    ),
                ),
                height=500,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                legend=dict(orientation="h", y=1.03),
            )
            st.plotly_chart(fig_route, use_container_width=True)

            # ── Tabla de paradas ───────────────────────────────────────────
            st.subheader("Secuencia de paradas")
            for veh in route_data.get("routes", []):
                names_list = veh.get("stop_names", [])
                stops_list = veh.get("stops", [])
                paradas = []
                for order_i, (sid, sname) in enumerate(zip(stops_list, names_list)):
                    role = "Depot" if sid == 0 else f"Parada {order_i}"
                    paradas.append({"Orden": role, "Nodo": sname.replace("OXXO ", "")})

                stops_df = pd.DataFrame(paradas)
                st.write(
                    f"**Vehículo {veh.get('vehicle', 1)}** — "
                    f"{veh.get('load_bultos', 0)} bultos · "
                    f"{veh.get('load_kg', 0):.0f} kg"
                )
                st.dataframe(stops_df, use_container_width=True, hide_index=True)

            st.caption(
                f"Escenario: **{route_data.get('scenario', sel_sc_r)}** · "
                f"Algoritmo: **{route_data.get('solver', '').upper()}** · "
                f"traffic_factor: {route_data.get('traffic_factor', '—')} · "
                f"service_extra: {route_data.get('service_extra', 0)} min"
            )

        else:
            # Mapa base con todos los nodos (sin ruta específica)
            fig_base = go.Figure()
            for _, s in stores_r.iterrows():
                fig_base.add_trace(go.Scattermap(
                    lat=[depot_r["lat"], s["lat"]],
                    lon=[depot_r["lon"], s["lon"]],
                    mode="lines",
                    line=dict(width=1, color="#94A3B8"),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            fig_base.add_trace(go.Scattermap(
                lat=stores_r["lat"], lon=stores_r["lon"],
                mode="markers+text",
                marker=dict(size=16, color="#1D4ED8"),
                text=stores_r["name"].str.replace("OXXO ", "", regex=False),
                textposition="top center",
                name="Tiendas OXXO",
                hoverinfo="text",
            ))
            fig_base.add_trace(go.Scattermap(
                lat=[depot_r["lat"]], lon=[depot_r["lon"]],
                mode="markers+text",
                marker=dict(size=24, color="#DC2626"),
                text=["CEDIS"],
                textposition="top right",
                name="CEDIS Saltillo",
                hoverinfo="text",
            ))
            fig_base.update_layout(
                map=dict(
                    style="open-street-map",
                    zoom=11,
                    center=dict(lat=nodes_r["lat"].mean(), lon=nodes_r["lon"].mean()),
                ),
                height=500,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
            )
            st.plotly_chart(fig_base, use_container_width=True)

        st.divider()
        st.subheader("Métricas de la instancia")
        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Nodos",          len(nodes_r))
        ic2.metric("Demanda total",  f"{int(stores_r['demand'].sum())} bultos")
        ic3.metric("Carga total",    f"{stores_r['demand_kg'].sum():.0f} kg")
        ic4.metric("Utilización",    f"{stores_r['demand_kg'].sum() / 15000 * 100:.1f}%")
