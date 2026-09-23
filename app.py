from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
import threading

# ============================================================
# DATOS DESDE SHAREPOINT
# ============================================================

URL = "https://continentaledupe-my.sharepoint.com/:x:/g/personal/csti_continental_edu_pe/IQCjStTQmlgHSJJX3DVmCDDJATq0TNbEBNkn6N_o80VqmJc?e=szWhsf&download=1"

CONFIG_HOJAS = {
    "Inventario Alquiler Adm.": {"MODALIDAD": "ALQUILER", "CATEGORIA": "ADMINISTRATIVA"},
    "Inventario Propio Acad.": {"MODALIDAD": "PROPIO", "CATEGORIA": "ACADEMICA"},
    "Inventario Propio Adm.": {"MODALIDAD": "PROPIO", "CATEGORIA": "ADMINISTRATIVA"},
    "Inventario Renta Administrativo": {"MODALIDAD": "RENTA", "CATEGORIA": "ADMINISTRATIVA"},
    "Inventario Renta Académico": {"MODALIDAD": "RENTA", "CATEGORIA": "ACADEMICA"},
}

def cargar_inventario():
    r = requests.get(URL, allow_redirects=True, timeout=60)
    r.raise_for_status()

    frames = []

    for hoja, cfg in CONFIG_HOJAS.items():
        df = pd.read_excel(BytesIO(r.content), sheet_name=hoja, header=6)
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        df = df.rename(columns={
            "N°": "NRO",
            "AREA": "ÁREA",
            "SUB AREA": "SUB ÁREA"
        })

        df["MODALIDAD"] = cfg["MODALIDAD"]
        df["CATEGORIA"] = cfg["CATEGORIA"]
        df["HOJA_ORIGEN"] = hoja

        if "EQUIPO" in df.columns:
            df = df[df["EQUIPO"].notna()]
            df = df[df["EQUIPO"].astype(str).str.strip().ne("")]

        frames.append(df)

    inv = pd.concat(frames, ignore_index=True, sort=False)

    columnas_texto = [
        "EQUIPO", "MODALIDAD", "CATEGORIA", "MARCA", "MODELO",
        "SERIE", "SERIE REAL", "USUARIO", "RESPONSABLE", "ÁREA",
        "AMBIENTE", "AMBIENTE_ACADÉMICO", "PABELLÓN", "CONTRATO"
    ]

    for c in columnas_texto:
        if c in inv.columns:
            inv[c] = inv[c].astype("string").str.strip()

    if "EQUIPO" in inv.columns:
        inv["EQUIPO"] = inv["EQUIPO"].str.upper().replace({
            "MONITOR1": "MONITOR",
            "PC1": "PC",
            "PROYECTOR1": "PROYECTOR MULTIMEDIA",
            "DISPOCITIVO INALAMBRICO": "DISPOSITIVO INALAMBRICO"
        })

    for c in ["MODALIDAD", "CATEGORIA", "PABELLÓN"]:
        if c in inv.columns:
            inv[c] = inv[c].str.upper()

    return inv


# ============================================================
# CACHÉ EN MEMORIA
# ============================================================

DATA_LOCK = threading.Lock()

inventario_dash = cargar_inventario()
ultima_actualizacion = datetime.now(ZoneInfo("America/Lima"))


def actualizar_datos():
    global inventario_dash, ultima_actualizacion

    nuevo_inventario = cargar_inventario()

    with DATA_LOCK:
        inventario_dash = nuevo_inventario
        ultima_actualizacion = datetime.now(ZoneInfo("America/Lima"))

    return ultima_actualizacion


def obtener_inventario():
    with DATA_LOCK:
        return inventario_dash.copy()


def texto_actualizacion():
    with DATA_LOCK:
        fecha = ultima_actualizacion

    return "Última actualización: " + fecha.strftime("%d/%m/%Y %H:%M:%S")


# ============================================================
# APP
# ============================================================

app = Dash(__name__)
server = app.server

FONDO = "#F4F7FB"
BLANCO = "#FFFFFF"
TEXTO = "#172033"
GRIS = "#667085"

COLORES = {
    "PROPIO": "#636EFA",
    "RENTA": "#00CC96",
    "ALQUILER": "#FFA15A"
}

tarjeta = {
    "backgroundColor": BLANCO,
    "borderRadius": "14px",
    "padding": "22px",
    "boxShadow": "0 2px 8px rgba(0,0,0,.08)"
}

grafico = {
    "backgroundColor": BLANCO,
    "borderRadius": "14px",
    "padding": "8px",
    "boxShadow": "0 2px 8px rgba(0,0,0,.06)"
}

cfg_grafico = {
    "displayModeBar": False,
    "responsive": True
}


def filtrar(categorias, modalidades, pabellones):
    df = obtener_inventario()

    if categorias:
        df = df[df["CATEGORIA"].isin(categorias)]

    if modalidades:
        df = df[df["MODALIDAD"].isin(modalidades)]

    if pabellones:
        df = df[df["PABELLÓN"].isin(pabellones)]

    return df


def vacia(titulo):
    fig = go.Figure()

    fig.add_annotation(
        text="No hay datos para mostrar",
        x=.5,
        y=.5,
        showarrow=False,
        font=dict(size=16, color=GRIS)
    )

    fig.update_layout(
        title=titulo,
        template="plotly_white",
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin=dict(l=30, r=30, t=60, b=30)
    )

    return fig


def formato(fig):
    fig.update_layout(
        template="plotly_white",
        transition_duration=0,
        font=dict(family="Arial", color=TEXTO),
        margin=dict(l=40, r=50, t=70, b=40),
        paper_bgcolor=BLANCO,
        plot_bgcolor=BLANCO
    )

    return fig


def kpi(titulo, ident):
    return html.Div([
        html.P(
            titulo,
            style={
                "color": GRIS,
                "fontWeight": "bold",
                "margin": "0"
            }
        ),

        html.H2(
            id=ident,
            style={
                "fontSize": "36px",
                "margin": "12px 0 0",
                "color": TEXTO
            }
        )
    ], style=tarjeta)


def filtro_card(titulo, ident, opciones):
    return html.Div([
        html.Div(
            titulo,
            style={
                "fontWeight": "bold",
                "fontSize": "17px",
                "color": TEXTO,
                "marginBottom": "5px"
            }
        ),

        html.Div(
            "Sin selección = Todas",
            style={
                "fontSize": "12px",
                "color": GRIS,
                "marginBottom": "15px"
            }
        ),

        dcc.Checklist(
            id=ident,
            options=opciones,
            value=[],
            labelStyle={
                "display": "block",
                "marginBottom": "12px",
                "cursor": "pointer"
            },
            inputStyle={"marginRight": "8px"},
            style={"fontSize": "16px"}
        )

    ], style={**tarjeta, "padding": "20px"})


# ============================================================
# LAYOUT
# ============================================================

app.layout = html.Div(
    style={
        "backgroundColor": FONDO,
        "minHeight": "100vh",
        "padding": "25px",
        "fontFamily": "Arial"
    },

    children=[

        # Intervalo: 5 minutos
        dcc.Interval(
            id="intervalo-actualizacion",
            interval=5 * 60 * 1000,
            n_intervals=0
        ),

        # Señal que obliga a refrescar KPI, gráficos y tabla
        dcc.Store(
            id="version-datos",
            data=0
        ),

        # ----------------------------------------------------
        # CABECERA
        # ----------------------------------------------------

        html.Div([

            html.Div([

                html.H1(
                    "Inventario TI - Filial Ayacucho",
                    style={
                        "margin": "0",
                        "color": TEXTO,
                        "fontSize": "34px"
                    }
                ),

                html.P(
                    "Panel de control de equipos tecnológicos",
                    style={
                        "color": GRIS,
                        "marginTop": "6px",
                        "marginBottom": "4px"
                    }
                ),

                html.Div(
                    id="ultima-actualizacion",
                    children=texto_actualizacion(),
                    style={
                        "fontSize": "13px",
                        "color": GRIS
                    }
                )

            ]),

            html.Button(
                "↻ Actualizar datos",
                id="btn-actualizar",
                n_clicks=0,
                style={
                    "backgroundColor": "#1565C0",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "9px",
                    "padding": "12px 20px",
                    "fontSize": "14px",
                    "fontWeight": "bold",
                    "cursor": "pointer",
                    "height": "44px"
                }
            )

        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "gap": "20px",
            "marginBottom": "25px"
        }),

        html.Div(
            id="estado-actualizacion",
            style={
                "fontSize": "13px",
                "marginTop": "-15px",
                "marginBottom": "15px",
                "color": GRIS
            }
        ),

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        html.Div([
            kpi("TOTAL EQUIPOS", "card-total"),
            kpi("ALQUILER", "card-alquiler"),
            kpi("RENTA", "card-renta"),
            kpi("PROPIOS", "card-propio")
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(4,1fr)",
            "gap": "18px",
            "marginBottom": "20px"
        }),

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        html.Div([

            filtro_card(
                "Categoría",
                "filtro-categoria",
                [
                    {"label": " Académica", "value": "ACADEMICA"},
                    {"label": " Administrativa", "value": "ADMINISTRATIVA"}
                ]
            ),

            filtro_card(
                "Modalidad",
                "filtro-modalidad",
                [
                    {"label": " Alquiler", "value": "ALQUILER"},
                    {"label": " Renta", "value": "RENTA"},
                    {"label": " Propio", "value": "PROPIO"}
                ]
            ),

            filtro_card(
                "Ubicación",
                "filtro-pabellon",
                [
                    {"label": " Filial", "value": "FILIAL"},
                    {"label": " Área Comercial", "value": "AREA COMERCIAL"},
                    {"label": " Pendiente de asignación (TI)", "value": "TI"}
                ]
            )

        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(3,minmax(0,1fr))",
            "gap": "20px",
            "marginBottom": "20px"
        }),

        # ----------------------------------------------------
        # GRÁFICOS 1
        # ----------------------------------------------------

        html.Div([

            html.Div(
                dcc.Loading(
                    children=dcc.Graph(
                        id="grafico-equipos",
                        config=cfg_grafico,
                        style={"height": "480px"}
                    )
                ),
                style=grafico
            ),

            html.Div(
                dcc.Loading(
                    children=dcc.Graph(
                        id="grafico-modalidad",
                        config=cfg_grafico,
                        style={"height": "480px"}
                    )
                ),
                style=grafico
            )

        ], style={
            "display": "grid",
            "gridTemplateColumns": "2fr 1fr",
            "gap": "20px",
            "marginBottom": "20px"
        }),

        # ----------------------------------------------------
        # GRÁFICOS 2
        # ----------------------------------------------------

        html.Div([

            html.Div(
                dcc.Loading(
                    children=dcc.Graph(
                        id="grafico-detalle",
                        config=cfg_grafico,
                        style={"height": "500px"}
                    )
                ),
                style=grafico
            ),

            html.Div(
                dcc.Loading(
                    children=dcc.Graph(
                        id="grafico-ubicacion",
                        config=cfg_grafico,
                        style={"height": "500px"}
                    )
                ),
                style=grafico
            )

        ], style={
            "display": "grid",
            "gridTemplateColumns": "2fr 1fr",
            "gap": "20px",
            "marginBottom": "20px"
        }),

        # ----------------------------------------------------
        # TABLA
        # ----------------------------------------------------

        html.Div([

            html.H2(
                "Detalle de equipos",
                style={
                    "marginTop": "0",
                    "color": TEXTO
                }
            ),

            dcc.Input(
                id="buscar",
                type="text",
                placeholder="Buscar por equipo, serie, usuario, responsable, marca, modelo, contrato...",
                debounce=True,
                style={
                    "width": "100%",
                    "padding": "13px",
                    "border": "1px solid #D0D5DD",
                    "borderRadius": "8px",
                    "boxSizing": "border-box",
                    "marginBottom": "12px",
                    "fontSize": "14px"
                }
            ),

            html.Div(
                id="cantidad-registros",
                style={
                    "fontSize": "14px",
                    "color": GRIS,
                    "marginBottom": "12px"
                }
            ),

            dcc.Loading(
                children=dash_table.DataTable(
                    id="tabla-inventario",
                    page_current=0,
                    page_size=15,
                    page_action="custom",
                    sort_action="native",

                    style_table={
                        "overflowX": "auto"
                    },

                    style_cell={
                        "textAlign": "left",
                        "padding": "9px",
                        "fontFamily": "Arial",
                        "fontSize": "12px",
                        "minWidth": "100px",
                        "maxWidth": "250px",
                        "whiteSpace": "normal"
                    },

                    style_header={
                        "backgroundColor": "#EEF2F7",
                        "fontWeight": "bold",
                        "color": TEXTO,
                        "border": "1px solid #D0D5DD"
                    },

                    style_data={
                        "backgroundColor": BLANCO,
                        "border": "1px solid #EAECF0"
                    }
                )
            )

        ], style=tarjeta)

    ]
)


# ============================================================
# ACTUALIZACIÓN MANUAL + AUTOMÁTICA
# ============================================================

@app.callback(
    Output("version-datos", "data"),
    Output("ultima-actualizacion", "children"),
    Output("estado-actualizacion", "children"),

    Input("btn-actualizar", "n_clicks"),
    Input("intervalo-actualizacion", "n_intervals"),

    State("version-datos", "data"),

    prevent_initial_call=True
)
def refrescar_datos(n_clicks, n_intervals, version_actual):
    try:
        actualizar_datos()

        version_nueva = (version_actual or 0) + 1

        if ctx.triggered_id == "btn-actualizar":
            estado = "Datos actualizados correctamente desde SharePoint."
        else:
            estado = "Actualización automática completada."

        return (
            version_nueva,
            texto_actualizacion(),
            estado
        )

    except Exception as e:
        return (
            version_actual or 0,
            texto_actualizacion(),
            f"No se pudo actualizar: {str(e)}"
        )


# ============================================================
# KPI
# ============================================================

@app.callback(
    Output("card-total", "children"),
    Output("card-alquiler", "children"),
    Output("card-renta", "children"),
    Output("card-propio", "children"),

    Input("filtro-categoria", "value"),
    Input("filtro-modalidad", "value"),
    Input("filtro-pabellon", "value"),
    Input("version-datos", "data")
)
def tarjetas(cats, mods, pabs, version):
    df = filtrar(cats, mods, pabs)

    return (
        len(df),
        int(df["MODALIDAD"].eq("ALQUILER").sum()),
        int(df["MODALIDAD"].eq("RENTA").sum()),
        int(df["MODALIDAD"].eq("PROPIO").sum())
    )


# ============================================================
# GRÁFICOS
# ============================================================

@app.callback(
    Output("grafico-equipos", "figure"),
    Output("grafico-modalidad", "figure"),
    Output("grafico-detalle", "figure"),
    Output("grafico-ubicacion", "figure"),

    Input("filtro-categoria", "value"),
    Input("filtro-modalidad", "value"),
    Input("filtro-pabellon", "value"),
    Input("version-datos", "data")
)
def graficos(cats, mods, pabs, version):
    df = filtrar(cats, mods, pabs)

    # 1. Equipos por tipo
    eq = df["EQUIPO"].dropna().value_counts().reset_index()
    eq.columns = ["EQUIPO", "TOTAL"]

    if len(eq):
        f1 = px.bar(
            eq,
            x="TOTAL",
            y="EQUIPO",
            orientation="h",
            text="TOTAL",
            title="Equipos por tipo"
        )

        f1.update_layout(
            yaxis={"categoryorder": "total ascending"},
            showlegend=False
        )

        f1.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        formato(f1)

    else:
        f1 = vacia("Equipos por tipo")

    # 2. Modalidad
    md = df["MODALIDAD"].dropna().value_counts().reset_index()
    md.columns = ["MODALIDAD", "TOTAL"]

    if len(md):
        f2 = px.pie(
            md,
            names="MODALIDAD",
            values="TOTAL",
            hole=.60,
            title="Distribución por modalidad",
            color="MODALIDAD",
            color_discrete_map=COLORES
        )

        f2.update_traces(
            textinfo="percent+label"
        )

        formato(f2)

    else:
        f2 = vacia("Distribución por modalidad")

    # 3. Detalle por modalidad
    det = (
        df[["EQUIPO", "MODALIDAD"]]
        .dropna()
        .groupby(["EQUIPO", "MODALIDAD"])
        .size()
        .reset_index(name="TOTAL")
    )

    if len(det):
        orden = (
            det.groupby("EQUIPO")["TOTAL"]
            .sum()
            .sort_values()
            .index
            .tolist()
        )

        f3 = px.bar(
            det,
            x="TOTAL",
            y="EQUIPO",
            color="MODALIDAD",
            orientation="h",
            text="TOTAL",
            title="Detalle de equipos por modalidad",
            barmode="stack",
            color_discrete_map=COLORES,
            category_orders={
                "EQUIPO": orden,
                "MODALIDAD": ["PROPIO", "RENTA", "ALQUILER"]
            }
        )

        f3.update_traces(
            textposition="inside"
        )

        f3.update_layout(
            yaxis={
                "categoryorder": "array",
                "categoryarray": orden
            },

            legend={
                "title": {"text": "Modalidad"},
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1
            }
        )

        formato(f3)

    else:
        f3 = vacia("Detalle de equipos por modalidad")

    # 4. Ubicación
    if "PABELLÓN" in df.columns:
        ub = (
            df["PABELLÓN"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace({
                "FILIAL": "Filial",
                "AREA COMERCIAL": "Área Comercial",
                "TI": "Pendiente (TI)"
            })
        )

        ub = ub[ub.ne("")].value_counts().reset_index()
        ub.columns = ["UBICACION", "TOTAL"]

    else:
        ub = pd.DataFrame(
            columns=["UBICACION", "TOTAL"]
        )

    if len(ub):
        f4 = px.bar(
            ub,
            x="TOTAL",
            y="UBICACION",
            orientation="h",
            text="TOTAL",
            title="Equipos por ubicación"
        )

        f4.update_layout(
            yaxis={"categoryorder": "total ascending"},
            showlegend=False
        )

        f4.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        formato(f4)

    else:
        f4 = vacia("Equipos por ubicación")

    return f1, f2, f3, f4


# ============================================================
# TABLA
# ============================================================

@app.callback(
    Output("tabla-inventario", "data"),
    Output("tabla-inventario", "columns"),
    Output("tabla-inventario", "page_count"),
    Output("cantidad-registros", "children"),

    Input("filtro-categoria", "value"),
    Input("filtro-modalidad", "value"),
    Input("filtro-pabellon", "value"),
    Input("buscar", "value"),
    Input("tabla-inventario", "page_current"),
    Input("tabla-inventario", "page_size"),
    Input("version-datos", "data")
)
def tabla(cats, mods, pabs, buscar, pagina, tamano, version):
    df = filtrar(cats, mods, pabs).copy()

    if buscar:
        texto = buscar.strip().lower()

        cols_busqueda = [
            "EQUIPO", "MARCA", "MODELO", "SERIE", "SERIE REAL",
            "USUARIO", "RESPONSABLE", "ÁREA", "AMBIENTE",
            "PABELLÓN", "CONTRATO"
        ]

        mascara = pd.Series(False, index=df.index)

        for c in cols_busqueda:
            if c in df.columns:
                mascara |= (
                    df[c]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(texto, regex=False)
                )

        df = df[mascara]

    deseadas = [
        "EQUIPO", "MARCA", "MODELO", "SERIE", "SERIE REAL",
        "USUARIO", "RESPONSABLE", "ÁREA", "AMBIENTE",
        "PABELLÓN", "CONTRATO", "MODALIDAD", "CATEGORIA"
    ]

    cols = [
        c for c in deseadas
        if c in df.columns
    ]

    total = len(df)

    tamano = tamano or 15
    pagina = pagina or 0

    paginas = (
        1 if total == 0
        else (total + tamano - 1) // tamano
    )

    pagina = min(
        pagina,
        max(paginas - 1, 0)
    )

    inicio = pagina * tamano
    fin = inicio + tamano

    datos = (
        df.iloc[inicio:fin][cols]
        .fillna("")
        .to_dict("records")
    )

    columnas = [
        {"name": c, "id": c}
        for c in cols
    ]

    if total == 0:
        mensaje = (
            "No se encontraron equipos "
            "con los filtros seleccionados."
        )
    else:
        mensaje = (
            f"Mostrando {inicio + 1} - "
            f"{min(fin, total)} de {total} equipos"
        )

    return (
        datos,
        columnas,
        paginas,
        mensaje
    )


# ============================================================
# EJECUCIÓN LOCAL
# Render usa: gunicorn app:server --bind 0.0.0.0:$PORT
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)
