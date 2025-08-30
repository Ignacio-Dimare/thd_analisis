# src/main.py
import flet as ft
from chat import chat_content
from graph import graph_content

# ===== Paleta oscura (estática) =====
APP_BG       = "#0E1117"  # fondo general de la app
CARD_BG      = "#161B22"  # fondo de las cards/paneles
CARD_BORDER  = "#30363D"  # borde de las cards
TEXT_PRIMARY = "#E6EDF3"  # texto principal

def main(page: ft.Page):
    page.title = "Analizador THD - Vista Doble"
    page.scroll = "auto"
    page.bgcolor = APP_BG

    # Panel izquierdo: gráfico
    left_card = ft.Container(
        content=graph_content(page),
        expand=1,
        padding=20,
        margin=10,
        border_radius=10,
        bgcolor=CARD_BG,
        border=ft.border.all(1, CARD_BORDER),
    )

    # Panel derecho: chat
    right_card = ft.Container(
        content=chat_content(page),
        expand=1,
        padding=20,
        margin=10,
        border_radius=10,
        bgcolor=CARD_BG,
        border=ft.border.all(1, CARD_BORDER),
    )

    # Barra superior
    top_bar = ft.Row(
        controls=[
            ft.Text("Preferencias", weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # Layout principal
    layout = ft.Row(controls=[left_card, right_card], expand=True)
    page.add(ft.Column([top_bar, layout], expand=True))

if __name__ == "__main__":
    ft.app(target=main)
