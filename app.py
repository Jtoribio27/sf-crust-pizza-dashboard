"""
San Francisco Crust Pizza - Sistema Inteligente de Apoyo a la Toma de Decisiones
Dashboard comercial en Streamlit + Plotly con asistente de IA (Google Gemini).
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SF Crust Pizza | Inteligencia Comercial",
    page_icon="🍕",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_FILES = {
    "Ventas": DATA_DIR / "Ventas.xlsx",
    "Clientes": DATA_DIR / "Clientes.xlsx",
    "Productos": DATA_DIR / "Productos.xlsx",
}
REQUIRED_COLS = {
    "Ventas": ["VentaID", "Fecha", "Ciudad", "Sucursal", "ClienteID", "ProductoID",
               "Cantidad", "PrecioUnitario", "CostoUnitario", "DescuentoPct",
               "VentaNeta", "CostoTotal", "UtilidadBruta", "Canal", "FormaPago",
               "TiempoEntregaMin", "TiempoPreparacionMin"],
    "Clientes": ["ClienteID", "Segmento", "ClienteActivo", "NPS", "MotivoPerdida"],
    "Productos": ["ProductoID", "Categoria", "Producto", "Tamaño", "Activo"],
}

# Paleta validada (orden fijo, nunca cíclico)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
GRAY = "#a3a29d"
CAT = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {font-size: 1.6rem;}
    [data-testid="stMetric"] {background: rgba(42,120,214,0.06); border-radius: 10px;
        padding: 12px 14px; border: 1px solid rgba(42,120,214,0.15);}
    .block-container {padding-top: 1.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
def usd(x, dec=0):
    return f"${x:,.{dec}f}"


def pct(x, dec=1):
    return f"{x:.{dec}%}"


def num(x):
    return f"{x:,.0f}"


def style_fig(fig, height=360, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None)
        if legend else dict(),
        showlegend=legend,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_size=12),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", title=None, zeroline=False)
    return fig


# ---------------------------------------------------------------------------
# Carga y validación de datos
# ---------------------------------------------------------------------------
def read_table(src):
    name = getattr(src, "name", str(src)).lower()
    if name.endswith(".csv"):
        return pd.read_csv(src)
    return pd.read_excel(src)


@st.cache_data(show_spinner="Cargando datos...")
def load_default(name):
    return read_table(DEFAULT_FILES[name])


@st.cache_data(show_spinner="Procesando archivo cargado...")
def load_uploaded(file_bytes, file_name):
    import io
    buf = io.BytesIO(file_bytes)
    buf.name = file_name
    return read_table(buf)


def validate(df, name):
    missing = [c for c in REQUIRED_COLS[name] if c not in df.columns]
    return missing


@st.cache_data(show_spinner=False)
def build_model(ventas, clientes, productos):
    v = ventas.copy()
    v["Fecha"] = pd.to_datetime(v["Fecha"])
    v["Año"] = v["Fecha"].dt.year
    v["Mes"] = v["Fecha"].dt.month
    v["Periodo"] = v["Fecha"].dt.to_period("M").dt.to_timestamp()
    p = productos.copy()
    p["ProductoNombre"] = p["Producto"].astype(str) + " " + p["Tamaño"].astype(str)
    p["ProductoNombre"] = p["ProductoNombre"].str.replace(" Único", "", regex=False)
    c = clientes.copy()
    m = v.merge(p[["ProductoID", "Categoria", "ProductoNombre", "Activo"]],
                on="ProductoID", how="left")
    m = m.merge(c[["ClienteID", "Segmento"]], on="ClienteID", how="left")
    m["Categoria"] = m["Categoria"].fillna("Sin categoría")
    m["ProductoNombre"] = m["ProductoNombre"].fillna(m["ProductoID"])
    m["Segmento"] = m["Segmento"].fillna("Sin segmento")
    m["ConDescuento"] = m["DescuentoPct"] > 0
    return m, c


# ---------------------------------------------------------------------------
# Barra lateral: actualización de datos
# ---------------------------------------------------------------------------
st.sidebar.title("🍕 SF Crust Pizza")
st.sidebar.caption("Sistema Inteligente de Apoyo a la Toma de Decisiones")

with st.sidebar.expander("📂 Actualizar bases de datos", expanded=False):
    st.caption("Sube un archivo nuevo (.xlsx o .csv) con las mismas columnas. "
               "Todos los indicadores se recalculan automáticamente.")
    up_v = st.file_uploader("Ventas", type=["xlsx", "csv"], key="up_v")
    up_c = st.file_uploader("Clientes (opcional)", type=["xlsx", "csv"], key="up_c")
    up_p = st.file_uploader("Productos (opcional)", type=["xlsx", "csv"], key="up_p")

frames, sources = {}, {}
for name, up in (("Ventas", up_v), ("Clientes", up_c), ("Productos", up_p)):
    if up is not None:
        df = load_uploaded(up.getvalue(), up.name)
        missing = validate(df, name)
        if missing:
            st.sidebar.error(f"El archivo de {name} no tiene las columnas: {', '.join(missing)}. "
                             "Se usa la base original.")
            df = load_default(name)
            sources[name] = "original"
        else:
            sources[name] = up.name
    else:
        df = load_default(name)
        sources[name] = "original"
    frames[name] = df

data, clientes = build_model(frames["Ventas"], frames["Clientes"], frames["Productos"])

if sources["Ventas"] != "original":
    st.sidebar.success(f"Ventas cargadas desde: {sources['Ventas']}")

# ---------------------------------------------------------------------------
# Barra lateral: filtros
# ---------------------------------------------------------------------------
st.sidebar.header("Filtros")
fmin, fmax = data["Fecha"].min().date(), data["Fecha"].max().date()
rango = st.sidebar.date_input("Rango de fechas", value=(fmin, fmax), min_value=fmin,
                              max_value=fmax, format="DD/MM/YYYY")
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    f_ini, f_fin = rango
else:
    f_ini, f_fin = fmin, fmax


def ms(label, options, help_txt=None):
    return st.sidebar.multiselect(label, sorted(options), placeholder="Todas", help=help_txt)


sel_ciudad = ms("Ciudad", data["Ciudad"].unique())
suc_opts = data[data["Ciudad"].isin(sel_ciudad)]["Sucursal"].unique() if sel_ciudad \
    else data["Sucursal"].unique()
sel_suc = ms("Sucursal", suc_opts)
sel_seg = ms("Segmento de cliente", data["Segmento"].unique())
sel_cat = ms("Categoría", data["Categoria"].unique())
prod_opts = data[data["Categoria"].isin(sel_cat)]["ProductoNombre"].unique() if sel_cat \
    else data["ProductoNombre"].unique()
sel_prod = ms("Producto", prod_opts)


def apply_filters(df, use_dates=True):
    out = df
    if use_dates:
        out = out[(out["Fecha"].dt.date >= f_ini) & (out["Fecha"].dt.date <= f_fin)]
    for col, sel in (("Ciudad", sel_ciudad), ("Sucursal", sel_suc), ("Segmento", sel_seg),
                     ("Categoria", sel_cat), ("ProductoNombre", sel_prod)):
        if sel:
            out = out[out[col].isin(sel)]
    return out


df = apply_filters(data)
st.sidebar.caption(f"{num(len(df))} de {num(len(data))} registros seleccionados")

if df.empty:
    st.warning("No hay datos para los filtros seleccionados. Ajusta los filtros.")
    st.stop()


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
def kpis(d):
    ventas = d["VentaNeta"].sum()
    util = d["UtilidadBruta"].sum()
    trans = d["VentaID"].nunique()
    return {
        "ventas": ventas,
        "utilidad": util,
        "margen": util / ventas if ventas else 0,
        "ticket": ventas / trans if trans else 0,
        "clientes": d["ClienteID"].nunique(),
        "trans": trans,
        "unidades": d["Cantidad"].sum(),
    }


def group_kpis(d, by):
    g = d.groupby(by).agg(Ventas=("VentaNeta", "sum"), Utilidad=("UtilidadBruta", "sum"),
                          Transacciones=("VentaID", "nunique"),
                          Clientes=("ClienteID", "nunique"), Unidades=("Cantidad", "sum"),
                          DescuentoProm=("DescuentoPct", "mean"),
                          PctConDescuento=("ConDescuento", "mean")).reset_index()
    g["Margen"] = g["Utilidad"] / g["Ventas"]
    g["Ticket"] = g["Ventas"] / g["Transacciones"]
    g["Participacion"] = g["Ventas"] / g["Ventas"].sum()
    return g.sort_values("Ventas", ascending=False)


K = kpis(df)
years = sorted(df["Año"].unique())
yoy = None
if len(years) >= 2:
    y1, y0 = years[-1], years[-2]
    k1, k0 = kpis(df[df["Año"] == y1]), kpis(df[df["Año"] == y0])
    yoy = {"y1": y1, "y0": y0, "k1": k1, "k0": k0}


def delta(key, kind="pct"):
    if not yoy or not yoy["k0"][key]:
        return None
    if kind == "pp":
        return f"{(yoy['k1'][key] - yoy['k0'][key]) * 100:+.1f} pp vs {yoy['y0']}"
    return f"{yoy['k1'][key] / yoy['k0'][key] - 1:+.1%} vs {yoy['y0']}"


# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.title("San Francisco Crust Pizza · Inteligencia Comercial")
st.caption(f"Periodo: {f_ini:%d/%m/%Y} – {f_fin:%d/%m/%Y} · Fuente de ventas: {sources['Ventas']}")

tab_dash, tab_prod, tab_suc, tab_cli, tab_ia, tab_datos = st.tabs(
    ["📊 Dashboard ejecutivo", "🍕 Productos", "🏬 Sucursales y operación",
     "👥 Clientes", "🤖 Asistente IA", "🗂️ Datos"])

# ---------------------------------------------------------------------------
# 1. Dashboard ejecutivo
# ---------------------------------------------------------------------------
with tab_dash:
    c = st.columns(6)
    c[0].metric("Ventas totales", usd(K["ventas"]), delta("ventas"))
    c[1].metric("Utilidad bruta", usd(K["utilidad"]), delta("utilidad"))
    c[2].metric("Margen bruto", pct(K["margen"]), delta("margen", "pp"))
    c[3].metric("Ticket promedio", usd(K["ticket"], 2), delta("ticket"))
    c[4].metric("Clientes", num(K["clientes"]), delta("clientes"))
    c[5].metric("Transacciones", num(K["trans"]), delta("trans"))
    if yoy:
        st.caption(f"Las variaciones comparan {yoy['y1']} contra {yoy['y0']} dentro de la selección "
                   "actual (si algún año está incompleto en el filtro, la comparación también lo está).")

    st.subheader("Evolución mensual de ventas")
    mens = df.groupby(["Año", "Mes"])["VentaNeta"].sum().reset_index()
    mens["Año"] = mens["Año"].astype(str)
    ycols = {str(y): CAT[i % 8] for i, y in enumerate(years)}
    fig = px.line(mens, x="Mes", y="VentaNeta", color="Año", markers=True,
                  color_discrete_map=ycols,
                  labels={"VentaNeta": "Ventas (USD)"})
    fig.update_traces(line_width=2, marker_size=8,
                      hovertemplate="Mes %{x}<br>Ventas: $%{y:,.0f}<extra>%{fullData.name}</extra>")
    fig.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                     ticktext=["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep",
                               "Oct", "Nov", "Dic"])
    fig.update_yaxes(tickprefix="$", tickformat=",.0f", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(style_fig(fig, 340), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ventas por ciudad")
        gc = group_kpis(df, "Ciudad").sort_values("Ventas")
        fig = px.bar(gc, x="Ventas", y="Ciudad", orientation="h",
                     color_discrete_sequence=[BLUE],
                     custom_data=["Utilidad", "Margen", "Participacion"])
        fig.update_traces(marker_cornerradius=4, texttemplate="$%{x:,.0f}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Utilidad: $%{customdata[0]:,.0f}"
                                        "<br>Margen: %{customdata[1]:.1%}<br>Participación: %{customdata[2]:.1%}<extra></extra>")
        fig.update_xaxes(tickprefix="$", tickformat=",.0f", range=[0, gc["Ventas"].max() * 1.22])
        st.plotly_chart(style_fig(fig, 300, False), width="stretch")
    with col2:
        st.subheader("Ventas por segmento de cliente")
        gs = group_kpis(df, "Segmento").sort_values("Ventas")
        fig = px.bar(gs, x="Ventas", y="Segmento", orientation="h",
                     color_discrete_sequence=[BLUE],
                     custom_data=["Clientes", "Ticket", "Participacion", "Margen"])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{customdata[2]:.1%}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Clientes: %{customdata[0]:,}"
                                        "<br>Ticket: $%{customdata[1]:,.2f}<br>Margen: %{customdata[3]:.1%}<extra></extra>")
        fig.update_xaxes(tickprefix="$", tickformat=",.0f", range=[0, gs["Ventas"].max() * 1.18])
        st.plotly_chart(style_fig(fig, 300, False), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ventas por sucursal")
        gsu = group_kpis(df, "Sucursal").sort_values("Ventas")
        fig = px.bar(gsu, x="Ventas", y="Sucursal", orientation="h",
                     color_discrete_sequence=[BLUE], custom_data=["Utilidad", "Margen", "Ticket"])
        fig.update_traces(marker_cornerradius=4, texttemplate="$%{x:,.0f}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Utilidad: $%{customdata[0]:,.0f}"
                                        "<br>Margen: %{customdata[1]:.1%}<br>Ticket: $%{customdata[2]:,.2f}<extra></extra>")
        fig.update_xaxes(tickprefix="$", tickformat=",.0f", range=[0, gsu["Ventas"].max() * 1.22])
        st.plotly_chart(style_fig(fig, 360, False), width="stretch")
    with col2:
        st.subheader("Top 10 productos más vendidos")
        metrica = st.radio("Ordenar por", ["Ventas", "Unidades"], horizontal=True, key="top_metric")
        gp = group_kpis(df, "ProductoNombre").sort_values(metrica, ascending=False).head(10) \
            .sort_values(metrica)
        fig = px.bar(gp, x=metrica, y="ProductoNombre", orientation="h",
                     color_discrete_sequence=[BLUE], custom_data=["Ventas", "Unidades", "Margen"])
        fmt = "$%{x:,.0f}" if metrica == "Ventas" else "%{x:,}"
        fig.update_traces(marker_cornerradius=4, texttemplate=fmt, textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Ventas: $%{customdata[0]:,.0f}<br>Unidades: "
                                        "%{customdata[1]:,}<br>Margen: %{customdata[2]:.1%}<extra></extra>")
        fig.update_xaxes(range=[0, gp[metrica].max() * 1.22], tickformat=",.0f",
                         tickprefix="$" if metrica == "Ventas" else "")
        st.plotly_chart(style_fig(fig, 310, False), width="stretch")

    st.subheader("Ventas por canal")
    gca = group_kpis(df, "Canal").sort_values("Ventas")
    fig = px.bar(gca, x="Ventas", y="Canal", orientation="h", color_discrete_sequence=[BLUE],
                 custom_data=["Participacion", "Ticket", "Margen"])
    fig.update_traces(marker_cornerradius=4, texttemplate="%{customdata[0]:.1%}", textposition="outside",
                      hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Ticket: $%{customdata[1]:,.2f}"
                                    "<br>Margen: %{customdata[2]:.1%}<extra></extra>")
    fig.update_xaxes(tickprefix="$", tickformat=",.0f", range=[0, gca["Ventas"].max() * 1.15])
    st.plotly_chart(style_fig(fig, 220, False), width="stretch")

# ---------------------------------------------------------------------------
# 2. Productos
# ---------------------------------------------------------------------------
with tab_prod:
    gp = group_kpis(df, "ProductoNombre")
    cat_map = df.drop_duplicates("ProductoNombre").set_index("ProductoNombre")["Categoria"]
    act_map = df.drop_duplicates("ProductoNombre").set_index("ProductoNombre")["Activo"]
    gp["Categoria"] = gp["ProductoNombre"].map(cat_map)
    gp["Activo"] = gp["ProductoNombre"].map(act_map)

    st.subheader("Matriz de rentabilidad: volumen vs margen")
    st.caption("Cada punto es un producto. Arriba a la derecha: alto volumen y alto margen (estrellas). "
               "Abajo a la izquierda: candidatos a revisar. El tamaño del punto es la utilidad bruta.")
    cats = sorted(gp["Categoria"].unique())
    cat_colors = {c_: CAT[i % 8] for i, c_ in enumerate(cats)}
    fig = px.scatter(gp, x="Unidades", y="Margen", size="Utilidad", color="Categoria",
                     hover_name="ProductoNombre", color_discrete_map=cat_colors, size_max=34,
                     custom_data=["Ventas", "Utilidad"])
    fig.update_traces(marker=dict(line=dict(width=2, color="white"), opacity=0.85),
                      hovertemplate="<b>%{hovertext}</b><br>Unidades: %{x:,}<br>Margen: %{y:.1%}"
                                    "<br>Ventas: $%{customdata[0]:,.0f}<br>Utilidad: $%{customdata[1]:,.0f}<extra></extra>")
    fig.add_hline(y=gp["Utilidad"].sum() / gp["Ventas"].sum(), line_dash="dot", line_color=GRAY,
                  annotation_text="Margen promedio", annotation_position="top left")
    fig.add_vline(x=gp["Unidades"].median(), line_dash="dot", line_color=GRAY,
                  annotation_text="Mediana de unidades", annotation_position="top right")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(style_fig(fig, 460), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 por utilidad bruta")
        t = gp.sort_values("Utilidad", ascending=False).head(10).sort_values("Utilidad")
        fig = px.bar(t, x="Utilidad", y="ProductoNombre", orientation="h", color_discrete_sequence=[BLUE],
                     custom_data=["Margen", "Ventas"])
        fig.update_traces(marker_cornerradius=4, texttemplate="$%{x:,.0f}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Utilidad: $%{x:,.0f}<br>Margen: %{customdata[0]:.1%}"
                                        "<br>Ventas: $%{customdata[1]:,.0f}<extra></extra>")
        fig.update_xaxes(range=[0, t["Utilidad"].max() * 1.25], tickprefix="$", tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 340, False), width="stretch")
    with col2:
        st.subheader("10 productos con menor utilidad")
        b = gp.sort_values("Utilidad").head(10).sort_values("Utilidad", ascending=False)
        fig = px.bar(b, x="Utilidad", y="ProductoNombre", orientation="h", color_discrete_sequence=[ORANGE],
                     custom_data=["Margen", "Ventas"])
        fig.update_traces(marker_cornerradius=4, texttemplate="$%{x:,.0f}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Utilidad: $%{x:,.0f}<br>Margen: %{customdata[0]:.1%}"
                                        "<br>Ventas: $%{customdata[1]:,.0f}<extra></extra>")
        fig.update_xaxes(range=[0, b["Utilidad"].max() * 1.3], tickprefix="$", tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 340, False), width="stretch")

    st.subheader("Desempeño por categoría")
    gcat = group_kpis(df, "Categoria")
    st.dataframe(
        gcat[["Categoria", "Ventas", "Utilidad", "Margen", "Unidades", "Ticket", "Participacion"]],
        hide_index=True, width="stretch",
        column_config={
            "Ventas": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen": st.column_config.NumberColumn(format="percent"),
            "Unidades": st.column_config.NumberColumn(format="%,d"),
            "Ticket": st.column_config.NumberColumn(format="$%.2f"),
            "Participacion": st.column_config.NumberColumn("Participación", format="percent"),
        })

    inact = gp[gp["Activo"].astype(str).str.lower().isin(["no", "false", "0"])]
    if not inact.empty:
        st.warning(f"⚠️ {len(inact)} producto(s) marcados como **inactivos** en el catálogo registran ventas "
                   f"por {usd(inact['Ventas'].sum())} ({pct(inact['Ventas'].sum() / K['ventas'])} del total): "
                   + ", ".join(inact["ProductoNombre"]))

    with st.expander("Ver tabla completa de productos"):
        st.dataframe(
            gp[["ProductoNombre", "Categoria", "Activo", "Ventas", "Utilidad", "Margen", "Unidades",
                "Transacciones", "Participacion"]],
            hide_index=True, width="stretch",
            column_config={
                "ProductoNombre": "Producto",
                "Ventas": st.column_config.NumberColumn(format="$%,.0f"),
                "Utilidad": st.column_config.NumberColumn(format="$%,.0f"),
                "Margen": st.column_config.NumberColumn(format="percent"),
                "Participacion": st.column_config.NumberColumn("Participación", format="percent"),
            })

# ---------------------------------------------------------------------------
# 3. Sucursales y operación
# ---------------------------------------------------------------------------
with tab_suc:
    gsu = group_kpis(df, "Sucursal")
    deliv = df[(df["Canal"] == "Delivery") & (df["TiempoEntregaMin"] > 0)]
    ent = deliv.groupby("Sucursal")["TiempoEntregaMin"].mean().rename("EntregaMin")
    prep = df.groupby("Sucursal")["TiempoPreparacionMin"].mean().rename("PreparacionMin")
    gsu = gsu.merge(ent, on="Sucursal", how="left").merge(prep, on="Sucursal", how="left")

    if yoy:
        a = df[df["Año"] == yoy["y1"]].groupby("Sucursal")["VentaNeta"].sum()
        b_ = df[df["Año"] == yoy["y0"]].groupby("Sucursal")["VentaNeta"].sum()
        gsu["VarVentas"] = gsu["Sucursal"].map(a / b_ - 1)

    best = gsu.sort_values("Utilidad", ascending=False).iloc[0]
    worst = gsu.sort_values("Utilidad").iloc[0]
    c1, c2 = st.columns(2)
    c1.success(f"**Mayor utilidad:** {best['Sucursal']} · {usd(best['Utilidad'])} · margen {pct(best['Margen'])}")
    c2.error(f"**Menor utilidad:** {worst['Sucursal']} · {usd(worst['Utilidad'])} · margen {pct(worst['Margen'])}")

    st.subheader("Scorecard de sucursales")
    cols = ["Sucursal", "Ventas", "Utilidad", "Margen", "Ticket", "Transacciones", "DescuentoProm",
            "PctConDescuento", "EntregaMin", "PreparacionMin"] + (["VarVentas"] if yoy else [])
    st.dataframe(
        gsu.sort_values("Utilidad", ascending=False)[cols], hide_index=True, width="stretch",
        column_config={
            "Ventas": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen": st.column_config.NumberColumn(format="percent"),
            "Ticket": st.column_config.NumberColumn(format="$%.2f"),
            "Transacciones": st.column_config.NumberColumn(format="%,d"),
            "DescuentoProm": st.column_config.NumberColumn("Descuento prom. (%)", format="%.1f"),
            "PctConDescuento": st.column_config.NumberColumn("Ventas con descuento", format="percent"),
            "EntregaMin": st.column_config.NumberColumn("Entrega delivery (min)", format="%.1f"),
            "PreparacionMin": st.column_config.NumberColumn("Preparación (min)", format="%.1f"),
            "VarVentas": st.column_config.NumberColumn(
                f"Var. ventas {yoy['y1']} vs {yoy['y0']}" if yoy else "Var.", format="percent"),
        })

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Margen bruto por sucursal")
        t = gsu.sort_values("Margen")
        fig = px.bar(t, x="Margen", y="Sucursal", orientation="h", color_discrete_sequence=[BLUE])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:.1%}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Margen: %{x:.1%}<extra></extra>")
        lo = max(0, t["Margen"].min() - 0.05)
        fig.update_xaxes(tickformat=".0%", range=[lo, t["Margen"].max() + 0.02])
        st.plotly_chart(style_fig(fig, 330, False), width="stretch")
        st.caption("Eje recortado para resaltar diferencias de margen.")
    with col2:
        st.subheader("Tiempo promedio de entrega (Delivery)")
        t = gsu.dropna(subset=["EntregaMin"]).sort_values("EntregaMin")
        fig = px.bar(t, x="EntregaMin", y="Sucursal", orientation="h", color_discrete_sequence=[BLUE])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:.1f} min", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Entrega: %{x:.1f} min<extra></extra>")
        fig.update_xaxes(range=[0, (t["EntregaMin"].max() if len(t) else 1) * 1.25])
        st.plotly_chart(style_fig(fig, 330, False), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("% de ventas con descuento por sucursal")
        t = gsu.sort_values("PctConDescuento")
        fig = px.bar(t, x="PctConDescuento", y="Sucursal", orientation="h", color_discrete_sequence=[ORANGE],
                     custom_data=["DescuentoProm"])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:.0%}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Ventas con descuento: %{x:.1%}"
                                        "<br>Descuento promedio: %{customdata[0]:.1f}%<extra></extra>")
        fig.update_xaxes(tickformat=".0%", range=[0, t["PctConDescuento"].max() * 1.25])
        st.plotly_chart(style_fig(fig, 330, False), width="stretch")
    with col2:
        st.subheader("Impacto del descuento en margen y ticket")
        gd = group_kpis(df, "DescuentoPct").sort_values("DescuentoPct")
        gd["Nivel"] = gd["DescuentoPct"].astype(int).astype(str) + "%"
        fig = px.bar(gd, x="Nivel", y="Margen", color_discrete_sequence=[BLUE],
                     custom_data=["Ticket", "Transacciones"])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{y:.1%}", textposition="outside",
                          hovertemplate="Descuento %{x}<br>Margen: %{y:.1%}<br>Ticket: $%{customdata[0]:.2f}"
                                        "<br>Transacciones: %{customdata[1]:,}<extra></extra>")
        fig.update_yaxes(tickformat=".0%", range=[0, gd["Margen"].max() * 1.18])
        fig.update_xaxes(title="Nivel de descuento", type="category")
        st.plotly_chart(style_fig(fig, 330, False), width="stretch")

    if yoy:
        st.subheader(f"Variación de ventas por sucursal: {yoy['y1']} vs {yoy['y0']}")
        t = gsu.dropna(subset=["VarVentas"]).sort_values("VarVentas")
        fig = px.bar(t, x="VarVentas", y="Sucursal", orientation="h",
                     color=t["VarVentas"] >= 0, color_discrete_map={True: BLUE, False: ORANGE})
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:+.1%}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Variación: %{x:+.1%}<extra></extra>")
        rng = max(abs(t["VarVentas"].min()), abs(t["VarVentas"].max())) * 1.3
        fig.update_xaxes(tickformat=".0%", range=[min(-rng, 0), max(rng, 0) if t["VarVentas"].max() > 0 else 0.02])
        st.plotly_chart(style_fig(fig, 330, False), width="stretch")

# ---------------------------------------------------------------------------
# 4. Clientes
# ---------------------------------------------------------------------------
with tab_cli:
    ids = df["ClienteID"].unique()
    cl = clientes[clientes["ClienteID"].isin(ids)].copy()
    if sel_seg:
        cl = cl[cl["Segmento"].isin(sel_seg)]
    cl["Activo"] = cl["ClienteActivo"].astype(str).str.strip().str.lower().isin(["sí", "si", "yes", "true", "1"])

    c = st.columns(4)
    c[0].metric("Clientes en la selección", num(len(cl)))
    c[1].metric("Clientes activos", pct(cl["Activo"].mean() if len(cl) else 0))
    c[2].metric("NPS promedio (0-10)", f"{cl['NPS'].mean():.1f}" if len(cl) else "-")
    c[3].metric("Clientes inactivos", num((~cl["Activo"]).sum()))
    st.caption("Los indicadores de esta pestaña vienen de la base de Clientes (CRM) para los clientes "
               "que compraron en la selección actual.")

    gseg = cl.groupby("Segmento").agg(Clientes=("ClienteID", "count"), Activos=("Activo", "mean"),
                                      NPS=("NPS", "mean")).reset_index()
    vseg = group_kpis(df, "Segmento")[["Segmento", "Ventas", "Ticket", "Participacion"]]
    gseg = gseg.merge(vseg, on="Segmento", how="left")
    gseg["VentasPorCliente"] = gseg["Ventas"] / gseg["Clientes"]

    st.subheader("Segmentos: tamaño, valor y lealtad")
    st.dataframe(
        gseg.sort_values("Ventas", ascending=False), hide_index=True, width="stretch",
        column_config={
            "Activos": st.column_config.NumberColumn("% activos", format="percent"),
            "NPS": st.column_config.NumberColumn("NPS prom.", format="%.1f"),
            "Ventas": st.column_config.NumberColumn(format="$%,.0f"),
            "Ticket": st.column_config.NumberColumn(format="$%.2f"),
            "Participacion": st.column_config.NumberColumn("Participación ventas", format="percent"),
            "VentasPorCliente": st.column_config.NumberColumn("Ventas por cliente", format="$%,.0f"),
        })

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("% de clientes activos por segmento")
        t = gseg.sort_values("Activos")
        fig = px.bar(t, x="Activos", y="Segmento", orientation="h", color_discrete_sequence=[BLUE])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:.0%}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Activos: %{x:.1%}<extra></extra>")
        fig.update_xaxes(tickformat=".0%", range=[0, 1.1])
        st.plotly_chart(style_fig(fig, 280, False), width="stretch")
    with col2:
        st.subheader("NPS promedio por segmento")
        t = gseg.sort_values("NPS")
        fig = px.bar(t, x="NPS", y="Segmento", orientation="h", color_discrete_sequence=[BLUE])
        fig.update_traces(marker_cornerradius=4, texttemplate="%{x:.1f}", textposition="outside",
                          hovertemplate="<b>%{y}</b><br>NPS: %{x:.2f}<extra></extra>")
        fig.update_xaxes(range=[0, 10.5])
        st.plotly_chart(style_fig(fig, 280, False), width="stretch")

    st.subheader("Motivos de pérdida de clientes")
    mot = cl[cl["MotivoPerdida"].notna()]
    if mot.empty:
        st.info("No hay clientes con motivo de pérdida en la selección.")
    else:
        gm = mot.groupby("MotivoPerdida").size().reset_index(name="Clientes").sort_values("Clientes")
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(gm, x="Clientes", y="MotivoPerdida", orientation="h", color_discrete_sequence=[ORANGE])
            fig.update_traces(marker_cornerradius=4, texttemplate="%{x}", textposition="outside",
                              hovertemplate="<b>%{y}</b><br>Clientes: %{x}<extra></extra>")
            fig.update_xaxes(range=[0, gm["Clientes"].max() * 1.2])
            st.plotly_chart(style_fig(fig, 300, False), width="stretch")
        with col2:
            pv = mot.pivot_table(index="Segmento", columns="MotivoPerdida", values="ClienteID",
                                 aggfunc="count", fill_value=0)
            fig = go.Figure(go.Heatmap(z=pv.values, x=pv.columns, y=pv.index,
                                       colorscale=[[0, "#cde2fb"], [1, "#104281"]],
                                       text=pv.values, texttemplate="%{text}", xgap=2, ygap=2,
                                       hovertemplate="%{y} · %{x}: %{z} clientes<extra></extra>",
                                       colorbar=dict(title="Clientes")))
            st.plotly_chart(style_fig(fig, 300, False), width="stretch")

# ---------------------------------------------------------------------------
# 5. Asistente IA
# ---------------------------------------------------------------------------
def build_context(d):
    """Resumen compacto de los KPIs filtrados para enviar al modelo."""
    k = kpis(d)
    lines = [
        f"Periodo: {f_ini} a {f_fin}. Filtros: ciudad={sel_ciudad or 'todas'}, sucursal={sel_suc or 'todas'}, "
        f"segmento={sel_seg or 'todos'}, categoría={sel_cat or 'todas'}, producto={sel_prod or 'todos'}.",
        f"KPIs: ventas {usd(k['ventas'])}, utilidad bruta {usd(k['utilidad'])}, margen {pct(k['margen'])}, "
        f"ticket promedio {usd(k['ticket'], 2)}, clientes {num(k['clientes'])}, transacciones {num(k['trans'])}, "
        f"unidades {num(k['unidades'])}.",
    ]
    if yoy:
        lines.append(f"Variación {yoy['y1']} vs {yoy['y0']}: ventas {delta('ventas')}, transacciones "
                     f"{delta('trans')}, ticket {delta('ticket')}, margen {delta('margen', 'pp')}.")

    def tbl(title, g, cols):
        out = [f"\n{title}:"]
        for _, r in g.iterrows():
            out.append(" - " + ", ".join(
                f"{c_}={usd(r[c_]) if c_ in ('Ventas', 'Utilidad') else pct(r[c_]) if c_ in ('Margen', 'Participacion', 'PctConDescuento', 'Activos', 'VarVentas') else f'{r[c_]:.2f}' if isinstance(r[c_], float) else r[c_]}"
                for c_ in cols))
        return out

    gsu_ = group_kpis(d, "Sucursal")
    deliv_ = d[(d["Canal"] == "Delivery") & (d["TiempoEntregaMin"] > 0)]
    gsu_ = gsu_.merge(deliv_.groupby("Sucursal")["TiempoEntregaMin"].mean().rename("EntregaMin"),
                      on="Sucursal", how="left")
    if yoy:
        a = d[d["Año"] == yoy["y1"]].groupby("Sucursal")["VentaNeta"].sum()
        b_ = d[d["Año"] == yoy["y0"]].groupby("Sucursal")["VentaNeta"].sum()
        gsu_["VarVentas"] = gsu_["Sucursal"].map(a / b_ - 1)
    scols = ["Sucursal", "Ventas", "Utilidad", "Margen", "Ticket", "PctConDescuento", "DescuentoProm",
             "EntregaMin"] + (["VarVentas"] if yoy else [])
    lines += tbl("Sucursales", gsu_, scols)
    lines += tbl("Ciudades", group_kpis(d, "Ciudad"), ["Ciudad", "Ventas", "Margen", "Participacion"])
    lines += tbl("Segmentos (ventas)", group_kpis(d, "Segmento"),
                 ["Segmento", "Ventas", "Participacion", "Ticket", "Clientes"])
    lines += tbl("Categorías", group_kpis(d, "Categoria"), ["Categoria", "Ventas", "Utilidad", "Margen"])
    gp_ = group_kpis(d, "ProductoNombre")
    lines += tbl("Top 8 productos por utilidad", gp_.sort_values("Utilidad", ascending=False).head(8),
                 ["ProductoNombre", "Ventas", "Utilidad", "Margen", "Unidades"])
    lines += tbl("8 productos con menor utilidad", gp_.sort_values("Utilidad").head(8),
                 ["ProductoNombre", "Ventas", "Utilidad", "Margen", "Unidades"])
    lines += tbl("Margen por nivel de descuento", group_kpis(d, "DescuentoPct").sort_values("DescuentoPct"),
                 ["DescuentoPct", "Margen", "Ticket", "Transacciones"])
    lines += tbl("Canales", group_kpis(d, "Canal"), ["Canal", "Ventas", "Participacion", "Margen"])
    inact_ = d[d["Activo"].astype(str).str.lower().isin(["no", "false", "0"])]
    if not inact_.empty:
        lines.append(f"\nProductos inactivos en catálogo que aún venden: "
                     f"{', '.join(inact_['ProductoNombre'].unique())} ({usd(inact_['VentaNeta'].sum())}).")
    cl_ = clientes[clientes["ClienteID"].isin(d["ClienteID"].unique())].copy()
    cl_["Activos"] = cl_["ClienteActivo"].astype(str).str.lower().isin(["sí", "si", "yes", "true", "1"])
    gc_ = cl_.groupby("Segmento").agg(Clientes=("ClienteID", "count"), Activos=("Activos", "mean"),
                                      NPS=("NPS", "mean")).reset_index()
    lines += tbl("Clientes (CRM) por segmento", gc_, ["Segmento", "Clientes", "Activos", "NPS"])
    mot_ = cl_["MotivoPerdida"].value_counts()
    if len(mot_):
        lines.append("Motivos de pérdida: " + ", ".join(f"{i}={v}" for i, v in mot_.items()))
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "Eres un consultor senior de inteligencia comercial para San Francisco Crust Pizza, una cadena regional "
    "de pizzerías en Texas (Estados Unidos). Respondes en español, de forma clara y ejecutiva. "
    "Usa EXCLUSIVAMENTE los datos del resumen que se te entrega; no inventes cifras. "
    "Cada recomendación debe citar la evidencia numérica que la respalda, proponer una acción concreta, "
    "un indicador para medirla y una meta realista. Si los datos no alcanzan para concluir algo, dilo."
)


def get_secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def ask_gemini(question, context):
    api_key = get_secret("GEMINI_API_KEY")
    model = get_secret("GEMINI_MODEL", "gemini-flash-latest")
    if not api_key:
        return None, "Falta configurar la clave GEMINI_API_KEY en los secrets de la aplicación."
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model,
            contents=f"RESUMEN DEL DASHBOARD (selección actual):\n{context}\n\nSOLICITUD:\n{question}",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4),
        )
        return resp.text, None
    except Exception as e:  # noqa: BLE001
        return None, f"No fue posible obtener respuesta del asistente ({type(e).__name__}: {e})."


with tab_ia:
    st.subheader("🤖 Asistente comercial con IA")
    st.caption("El asistente analiza los indicadores de la selección actual (respeta todos los filtros) y "
               "propone recomendaciones. Sus respuestas deben validarse con criterio comercial antes de usarse.")
    context = build_context(df)

    if "ia_history" not in st.session_state:
        st.session_state.ia_history = []

    c1, c2 = st.columns([1, 1])
    preset = None
    if c1.button("💡 Generar 5 recomendaciones comerciales", width="stretch", type="primary"):
        preset = ("Analiza los datos y propone las 5 recomendaciones comerciales más importantes para mejorar "
                  "ventas y rentabilidad. Para cada una: hallazgo con cifras, acción concreta, responsable, "
                  "KPI y meta a 6 meses.")
    if c2.button("🗑️ Limpiar conversación", width="stretch"):
        st.session_state.ia_history = []

    ejemplos = ["¿Qué sucursal tiene el peor desempeño y por qué?",
                "¿Qué productos debería revisar y qué haría con ellos?",
                "¿Qué segmento de clientes tiene más potencial de crecimiento?",
                "¿Están funcionando los descuentos?"]
    st.caption("Ejemplos: " + " · ".join(ejemplos))
    question = st.chat_input("Escribe tu pregunta para el asistente...")
    q = preset or question
    if q:
        with st.spinner("El asistente está analizando los datos..."):
            answer, err = ask_gemini(q, context)
        st.session_state.ia_history.append({"q": q, "a": answer, "err": err})

    for item in reversed(st.session_state.ia_history):
        with st.chat_message("user"):
            st.write(item["q"])
        with st.chat_message("assistant"):
            if item["err"]:
                st.warning(item["err"])
            else:
                st.markdown(item["a"])

    with st.expander("Ver los datos que recibe el asistente"):
        st.code(context, language="text")

# ---------------------------------------------------------------------------
# 6. Datos
# ---------------------------------------------------------------------------
with tab_datos:
    st.subheader("Bases de datos en uso")
    c = st.columns(3)
    for col, name in zip(c, ["Ventas", "Clientes", "Productos"]):
        col.metric(name, f"{num(len(frames[name]))} filas", sources[name], delta_color="off")
    st.markdown(
        "**Cómo actualizar la información:** abre *📂 Actualizar bases de datos* en la barra lateral y sube "
        "un nuevo archivo de Ventas (.xlsx o .csv) con las mismas columnas. La aplicación valida el archivo y "
        "recalcula todos los indicadores, gráficas y el contexto del asistente sin modificar el código.")
    st.markdown("**Columnas obligatorias de Ventas:** " + ", ".join(REQUIRED_COLS["Ventas"]))
    st.markdown("**Definición de indicadores:** Ventas = suma de VentaNeta · Utilidad bruta = suma de "
                "UtilidadBruta · Margen = Utilidad / Ventas · Ticket promedio = Ventas / transacciones "
                "(VentaID únicos) · Clientes = ClienteID únicos.")
    st.dataframe(df.drop(columns=["Periodo"]).head(500), width="stretch", hide_index=True)
    st.download_button("⬇️ Descargar selección filtrada (CSV)",
                       df.drop(columns=["Periodo"]).to_csv(index=False).encode("utf-8-sig"),
                       "ventas_filtradas.csv", "text/csv")
