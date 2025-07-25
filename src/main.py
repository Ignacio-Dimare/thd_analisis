import flet as ft
from flet.plotly_chart import PlotlyChart
import plotly.express as px
import pandas as pd


def main(page: ft.Page):
    page.title = "Analizador de THD en Frecuencia"
    page.padding = 0
    page.scroll = None

    # Leer datos del CSV
    df = pd.read_csv("thd_data.csv")

    # Controles
    freq_start_field = ft.TextField(
        label="Frecuencia de Inicio (Hz)",
        width=180,
        value="20",
    )
    freq_end_field = ft.TextField(
        label="Frecuencia de Fin (Hz)",
        width=180,
        value="20000",
    )
    increment_field = ft.TextField(
        label="Incremento (Hz)",
        width=180,
        value="100",
    )

    controls_row = ft.Row(
        controls=[
            freq_start_field,
            freq_end_field,
            increment_field,
        ],
        wrap=True,
        spacing=20,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    chart_container = ft.Container(
        alignment=ft.alignment.center,
        expand=True,
    )

    # Crear la figura con fondo oscuro
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
            template="plotly_dark",  # 🌙 Fondo oscuro
            hovermode="x unified",
        )
        return fig

    # Actualizar el gráfico dinámicamente
    def update_chart():
        ancho = max(page.width, 300)
        alto = max(page.height - 120, 300)
        fig = create_figure(ancho, alto)
        chart_container.content = PlotlyChart(fig)
        page.update()

    # Inicializar
    update_chart()

    # Redibujar cuando cambia tamaño
    def on_resize(e):
        update_chart()

    page.on_resize = on_resize

    # Layout principal
    page.add(
        ft.Column(
            controls=[
                ft.Row(
                    [ft.Text(
                        "Configuración de Barrido en Frecuencia",
                        style=ft.TextThemeStyle.TITLE_MEDIUM
                    )],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                controls_row,
                chart_container,
            ],
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(main)
