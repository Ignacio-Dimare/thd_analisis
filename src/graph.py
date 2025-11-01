import flet as ft
from flet.plotly_chart import PlotlyChart
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from uuid import uuid4
import os
import asyncio
import time

# ✅ Compartir SerialService y mandar mensajes al chat
from app_state import serial_ref
from storage.data.message_storage_instance import message_store
from flet import Icons

# ===== Paleta oscura =====
CARD_BG       = "#161B22"
CARD_BORDER   = "#30363D"
TEXT_PRIMARY  = "#E6EDF3"
TEXT_MUTED    = "#9BA8B3"
PRIMARY       = "#3B82F6"
GRID_COLOR    = "#30363D"
HOVER_BG      = "#1F242D"

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

    # Campos visuales de configuración (aún no usados para CSV)
    freq_start_field = ft.TextField(label="Frecuencia de Inicio (Hz)", width=180, value="20")
    freq_end_field   = ft.TextField(label="Frecuencia de Fin (Hz)",   width=180, value="20000")
    increment_field  = ft.TextField(label="Incremento (Hz)",          width=180, value="100")
    for tf in (freq_start_field, freq_end_field, increment_field):
        style_textfield(tf)

    controls_row = ft.Row(
        controls=[freq_start_field, freq_end_field, increment_field],
        wrap=True, spacing=20, alignment=ft.MainAxisAlignment.CENTER,
    )

    # ---------- NUEVO: controles de secuencia RL ----------
    repeats_tf = ft.TextField(label="Repeticiones", value="10", width=140)
    delay_seq_tf = ft.TextField(label="Delay (s)", value="0.5", width=120)
    for tf in (repeats_tf, delay_seq_tf):
        style_textfield(tf)

    running_seq = {"flag": False}

    def run_sequence_clicked(e):
        if running_seq["flag"]:
            return
        if not serial_ref["svc"] or not serial_ref["svc"].is_running:
            page.snack_bar = ft.SnackBar(ft.Text("Conecta el serial antes de ejecutar la secuencia."))
            page.snack_bar.open = True
            page.update()
            return

        try:
            repeats = int((repeats_tf.value or "10").strip())
        except:
            repeats = 10
        try:
            delay_s = float((delay_seq_tf.value or "0.5").strip())
        except:
            delay_s = 0.5

        async def run_sequence_task():
            running_seq["flag"] = True
            seq_btn.disabled = True
            seq_btn.text = "Ejecutando…"
            seq_btn.icon = Icons.HOURGLASS_EMPTY
            seq_btn.update()

            message_store.add_message("system",
                                      f"Iniciando secuencia RL (reps={repeats}, delay={delay_s}s)…")

            values = await asyncio.to_thread(
                serial_ref["svc"].run_measurement_sequence,
                repeats, delay_s
            )

            if values:
                message_store.add_message("system", f"RL lecturas: {values}")
                try:
                    avg = sum(values) / len(values)
                    message_store.add_message("system", f"Promedio RL: {avg:.6f}")
                except:
                    pass
            else:
                message_store.add_message("system", "No se obtuvieron lecturas RL (lista vacía).")

            seq_btn.disabled = False
            seq_btn.text = "Secuencia RL"
            seq_btn.icon = Icons.ANALYTICS
            seq_btn.update()
            running_seq["flag"] = False

        page.run_task(run_sequence_task)

    seq_btn = ft.ElevatedButton("Secuencia RL", icon=Icons.ANALYTICS, on_click=run_sequence_clicked)

    rl_row = ft.Row(
        controls=[repeats_tf, delay_seq_tf, seq_btn],
        wrap=True, spacing=20, alignment=ft.MainAxisAlignment.CENTER,
    )

    # ---------- Gráfico ----------
    chart_container = ft.Container(alignment=ft.alignment.center, expand=True)
    title = ft.Text("Configuración de Barrido en Frecuencia",
                    style=ft.TextThemeStyle.TITLE_MEDIUM, color=TEXT_PRIMARY)

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
        fig.add_annotation(text=msg, showarrow=False, font=dict(color=TEXT_MUTED, size=14),
                           xref="paper", yref="paper", x=0.5, y=0.5)
        fig.update_layout(hoverlabel=dict(bgcolor=HOVER_BG, bordercolor=CARD_BORDER,
                                          font=dict(color=TEXT_PRIMARY)))
        return fig

    def create_figure(df: pd.DataFrame | None, width: int, height: int):
        if df is None or df.empty or not set(["Frecuencia", "THD"]).issubset(df.columns):
            return make_empty_figure(width, height, "Esperando archivo 'thd_data.csv'…")

        try:
            df_plot = df.copy()
            df_plot["THD"] = pd.to_numeric(df_plot["THD"].astype(str).str.replace(",", "."), errors="coerce")
            df_plot = df_plot.dropna(subset=["Frecuencia", "THD"])
            if df_plot.empty:
                return make_empty_figure(width, height, "Sin datos válidos en el CSV.")
        except:
            return make_empty_figure(width, height, "Error leyendo datos del CSV.")

        fig = px.line(df_plot, x="Frecuencia", y="THD", title="THD vs Frecuencia", markers=True)
        fig.update_traces(line=dict(width=2, color=PRIMARY), marker=dict(size=6, color=PRIMARY))
        fig.update_layout(
            autosize=False, width=width, height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis_title="Frecuencia (Hz)", yaxis_title="THD (%)",
            hovermode="x unified",
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            font=dict(color=TEXT_PRIMARY), title=dict(font=dict(color=TEXT_PRIMARY)),
            colorway=[PRIMARY],
        )
        axis_common = dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False,
                           linecolor=CARD_BORDER, tickfont=dict(color=TEXT_MUTED))
        fig.update_xaxes(**axis_common)
        fig.update_yaxes(**axis_common)
        fig.update_layout(hoverlabel=dict(bgcolor=HOVER_BG, bordercolor=CARD_BORDER,
                                          font=dict(color=TEXT_PRIMARY)))
        return fig

    def update_chart(df: pd.DataFrame | None):
        ancho = max(int(page.width // 2), 300)
        alto = max(int(page.height - 180), 300)
        fig = create_figure(df, ancho, alto)
        chart_container.content = PlotlyChart(fig, key=str(uuid4()))
        if chart_container.page: chart_container.update()

    # Primer render
    update_chart(None)

    page.on_resize = lambda e: update_chart(state["df"])

    # ---------- Polling CSV ----------
    state = {"df": None, "mtime": None}

    async def poll_csv():
        while True:
            try:
                if os.path.exists(CSV_PATH):
                    mtime = os.path.getmtime(CSV_PATH)
                    if state["mtime"] is None or mtime != state["mtime"]:
                        await asyncio.sleep(0.05)
                        new_df = pd.read_csv(CSV_PATH)
                        state["df"] = new_df
                        state["mtime"] = mtime
                        update_chart(state["df"])
                else:
                    if state["df"] is not None or state["mtime"] is not None:
                        state["df"] = None
                        state["mtime"] = None
                        update_chart(None)
            except:
                pass
            await asyncio.sleep(POLL_SECS)

    page.run_task(poll_csv)

    root = ft.Container(
        bgcolor=CARD_BG,
        content=ft.Column(
            controls=[title, controls_row, rl_row, chart_container],
            expand=True,
        ),
    )
    return root
