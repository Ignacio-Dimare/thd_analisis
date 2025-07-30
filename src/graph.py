import flet as ft
from flet.plotly_chart import PlotlyChart
import plotly.express as px
import pandas as pd

def graph_content(page: ft.Page):
    page.scroll = None

    df = pd.read_csv("thd_data.csv")

    freq_start_field = ft.TextField(label="Frecuencia de Inicio (Hz)", width=180, value="20")
    freq_end_field = ft.TextField(label="Frecuencia de Fin (Hz)", width=180, value="20000")
    increment_field = ft.TextField(label="Incremento (Hz)", width=180, value="100")

    controls_row = ft.Row(
        controls=[freq_start_field, freq_end_field, increment_field],
        wrap=True,
        spacing=20,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    chart_container = ft.Container(alignment=ft.alignment.center, expand=True)

    def create_figure(width, height):
        fig = px.line(
            df,
            x="Frecuencia",
            y="THD",
            title="THD vs Frecuencia",
            markers=True,
        )
        fig.update_layout(
            autosize=False,
            width=width,
            height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis_title="Frecuencia (Hz)",
            yaxis_title="THD (%)",
            template="plotly_dark",
            hovermode="x unified",
        )
        return fig

    def update_chart():
        ancho = max(page.width // 2, 300)
        alto = max(page.height - 120, 300)
        fig = create_figure(ancho, alto)
        chart_container.content = PlotlyChart(fig)
        page.update()

    update_chart()
    page.on_resize = lambda e: update_chart()

    return ft.Column(
        controls=[
            ft.Text("Configuración de Barrido en Frecuencia", style=ft.TextThemeStyle.TITLE_MEDIUM),
            controls_row,
            chart_container,
        ],
        expand=True,
    )
