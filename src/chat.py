import flet as ft
from flet import Icons, Colors
import asyncio
from storage.data.message_storage_instance import message_store

def chat_content(page: ft.Page):
    # Crear ListView para mostrar los mensajes
    chat_display = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
    )

    # Función que actualiza visualmente los mensajes
    def render_messages():
        chat_display.controls.clear()
        for msg in message_store.get_messages():
            align = ft.alignment.center_right if msg["from"] == "user" else ft.alignment.center_left
            color = Colors.BLUE_100 if msg["from"] == "user" else Colors.GREY_200

            chat_display.controls.append(
                ft.Container(
                    content=ft.Text(msg["text"]),
                    bgcolor=color,
                    padding=10,
                    margin=5,
                    border_radius=10,
                    alignment=align,
                    width=300,
                )
            )
        chat_display.update()

    # Campo de entrada
    input_field = ft.TextField(
        hint_text="Escribe...",
        expand=True
    )

    # Botón para enviar mensajes
    def send_message(e):
        text = input_field.value.strip()
        if text:
            message_store.add_message("user", text)
            input_field.value = ""
            input_field.update()

    send_btn = ft.IconButton(
        icon=Icons.SEND,
        on_click=send_message
    )

    input_row = ft.Row([input_field, send_btn], spacing=5)

    # Layout principal del chat
    chat_ui = ft.Column(
        controls=[
            ft.Text("💬 Chat con el Asistente THD", size=20),
            chat_display,
            input_row,
        ],
        expand=True
    )

    # 🔁 Suscripción diferida al store para evitar error de ListView no montado
    async def delayed_subscription():
        await asyncio.sleep(0.1)  # espera que el control esté en la página
        message_store.subscribe(render_messages)
        render_messages()

    page.run_task(delayed_subscription)

    return chat_ui
