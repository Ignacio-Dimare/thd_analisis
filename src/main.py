import flet as ft
from chat import chat_content
from graph import graph_content
from storage.data.message_storage_instance import message_store
import asyncio

def main(page: ft.Page):
    page.title = "Analizador THD - Vista Doble"
    page.scroll = "auto"

    layout = ft.Row(
        controls=[
            ft.Container(
                content=graph_content(page),
                expand=1,
                padding=20,
                margin=10,
                border_radius=10,
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
            ft.Container(
                content=chat_content(page),
                expand=1,
                padding=20,
                margin=10,
                border_radius=10,
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_300),
            ),
        ],
        expand=True,
    )

    page.add(layout)

    # 🔁 Prueba de mensajes programados desde main
    async def test_bot_messages():
        await asyncio.sleep(2)
        message_store.add_message("bot", "🔧 Mensaje de prueba desde main #1")
        await asyncio.sleep(2)
        message_store.add_message("bot", "✅ Reactividad confirmada desde main.py")
        await asyncio.sleep(2)
        message_store.add_message("bot", "🎉 Todo está funcionando perfectamente.")
    #page.run_task(test_bot_messages)

if __name__ == "__main__":
    ft.app(target=main)
