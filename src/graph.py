import flet as ft
from flet.plotly_chart import PlotlyChart
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from uuid import uuid4
import os
import asyncio
import time

# ===== Paleta oscura (estática) =====
CARD_BG       = "#161B22"  # fondo del panel
CARD_BORDER   = "#30363D"  # borde / ejes
TEXT_PRIMARY  = "#E6EDF3"  # texto principal
TEXT_MUTED    = "#9BA8B3"  # texto menos destacado
PRIMARY       = "#3B82F6"  # azul para la curva
GRID_COLOR    = "#30363D"  # grilla
HOVER_BG      = "#1F242D"  # fondo del hover

CSV_PATH = "thd_data.csv"
POLL_SECS = 1.0

def graph_content(page: ft.Page):
    page.scroll = None

    # ---------- estilo inputs ----------
    def style_textfield(tf: ft.TextField):
        tf.bgcolor = CARD_BG
        tf.color = TEXT_PRIMARY
        tf.border_color = CARD_BORDER
        tf.focused_border_color = PRIMARY
        tf.hint_style = ft.TextStyle(color=TEXT_MUTED)

    # Campos (por ahora informativos; el gráfico usa el CSV)
    freq_start_field = ft.TextField(label="Frecuencia de Inicio (Hz)", width=180, value="20")
    freq_end_field   = ft.TextField(label="Frecuencia de Fin (Hz)",   width=180, value="20000")
    increment_field  = ft.TextField(label="Incremento (Hz)",          width=180, value="100")
    for tf in (freq_start_field, freq_end_field, increment_field):
        style_textfield(tf)

    controls_row = ft.Row(
        controls=[freq_start_field, freq_end_field, increment_field],
        wrap=True, spacing=20, alignment=ft.MainAxisAlignment.CENTER,
    )

    chart_container = ft.Container(alignment=ft.alignment.center, expand=True)

    # Título
    title = ft.Text(
        "Configuración de Barrido en Frecuencia",
        style=ft.TextThemeStyle.TITLE_MEDIUM,
        color=TEXT_PRIMARY,
    )

    # ---------- Helpers de figura ----------
    def make_empty_figure(width: int, height: int, msg: str) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            autosize=False, width=width, height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font=dict(color=TEXT_PRIMARY),
            title=dict(text="THD vs Frecuencia", font=dict(color=TEXT_PRIMARY)),
        )
        axis_common = dict(
            showgrid=True, gridcolor=GRID_COLOR, zeroline=False,
            linecolor=CARD_BORDER, tickfont=dict(color=TEXT_MUTED)
        )
        fig.update_xaxes(**axis_common, title=dict(text="Frecuencia (Hz)", font=dict(color=TEXT_PRIMARY)))
        fig.update_yaxes(**axis_common, title=dict(text="THD (%)",        font=dict(color=TEXT_PRIMARY)))
        fig.add_annotation(
            text=msg, showarrow=False, font=dict(color=TEXT_MUTED, size=14),
            xref="paper", yref="paper", x=0.5, y=0.5
        )
        fig.update_layout(
            hoverlabel=dict(bgcolor=HOVER_BG, bordercolor=CARD_BORDER, font=dict(color=TEXT_PRIMARY))
        )
        return fig

    def create_figure(df: pd.DataFrame | None, width: int, height: int):
        # Validación de DF
        if df is None or df.empty or not set(["Frecuencia", "THD"]).issubset(df.columns):
            return make_empty_figure(width, height, "Esperando archivo 'thd_data.csv'…")

        # Intentar convertir THD a float (por si viene formateado como string)
        try:
            df_plot = df.copy()
            df_plot["THD"] = pd.to_numeric(df_plot["THD"].astype(str).str.replace(",", "."), errors="coerce")
            df_plot = df_plot.dropna(subset=["Frecuencia", "THD"])
            if df_plot.empty:
                return make_empty_figure(width, height, "Sin datos válidos en el CSV.")
        except Exception:
            return make_empty_figure(width, height, "Error leyendo datos del CSV.")

        fig = px.line(df_plot, x="Frecuencia", y="THD", title="THD vs Frecuencia", markers=True)
        fig.update_traces(line=dict(width=2, color=PRIMARY),
                          marker=dict(size=6, color=PRIMARY))
        fig.update_layout(
            autosize=False, width=width, height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis_title="Frecuencia (Hz)", yaxis_title="THD (%)",
            hovermode="x unified",
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font=dict(color=TEXT_PRIMARY),
            title=dict(font=dict(color=TEXT_PRIMARY)),
            colorway=[PRIMARY],
        )
        axis_common = dict(
            showgrid=True, gridcolor=GRID_COLOR, zeroline=False,
            linecolor=CARD_BORDER, tickfont=dict(color=TEXT_MUTED)
        )
        fig.update_xaxes(**axis_common, title=dict(text="Frecuencia (Hz)", font=dict(color=TEXT_PRIMARY)))
        fig.update_yaxes(**axis_common, title=dict(text="THD (%)",        font=dict(color=TEXT_PRIMARY)))
        fig.update_layout(
            hoverlabel=dict(bgcolor=HOVER_BG, bordercolor=CARD_BORDER, font=dict(color=TEXT_PRIMARY))
        )
        return fig

    def update_chart(df: pd.DataFrame | None):
        ancho = max(int(page.width // 2), 300)
        alto = max(int(page.height - 120), 300)
        fig = create_figure(df, ancho, alto)
        chart_container.content = PlotlyChart(fig, key=str(uuid4()))  # fuerza redraw
        if chart_container.page:
            chart_container.update()

    # Primer render (sin datos)
    update_chart(None)

    # Redibuja al cambiar tamaño
    page.on_resize = lambda e: update_chart(state["df"])

    # ---------- Polling del CSV cada 1s ----------
    state = {"df": None, "mtime": None}

    async def poll_csv():
        while True:
            try:
                if os.path.exists(CSV_PATH):
                    mtime = os.path.getmtime(CSV_PATH)
                    # Actualizar si es la primera vez o si cambió el archivo
                    if state["mtime"] is None or mtime != state["mtime"]:
                        # Pequeño delay para evitar leer mientras otro proceso escribe
                        await asyncio.sleep(0.05)
                        new_df = pd.read_csv(CSV_PATH)
                        state["df"] = new_df
                        state["mtime"] = mtime
                        update_chart(state["df"])
                else:
                    # Si desapareció, mostrar placeholder una sola vez
                    if state["df"] is not None or state["mtime"] is not None:
                        state["df"] = None
                        state["mtime"] = None
                        update_chart(None)
            except Exception:
                # Si hubo cualquier error de lectura/parsing, no romper la UI:
                # mantener el último gráfico válido o placeholder.
                pass
            await asyncio.sleep(POLL_SECS)

    page.run_task(poll_csv)

    # Contenedor raíz del panel (la “caja”)
    root = ft.Container(
        bgcolor=CARD_BG,
        content=ft.Column(
            controls=[title, controls_row, chart_container],
            expand=True,
        ),
    )
    return root
