import flet as ft
from flet import Icons
import asyncio
from storage.data.message_storage_instance import message_store
from serial_service import SerialService
from serial.tools import list_ports

# ✅ Estado compartido global SerialService
from app_state import serial_ref

# ===== Paleta oscura (estática) =====
CARD_BG            = "#161B22"
CARD_BORDER        = "#30363D"
TEXT_PRIMARY       = "#E6EDF3"
TEXT_MUTED         = "#9BA8B3"
PRIMARY            = "#3B82F6"
BUBBLE_USER_BG     = "#1F6FEB"
BUBBLE_USER_TEXT   = "#FFFFFF"
BUBBLE_OTHER_BG    = "#1F242D"
BUBBLE_OTHER_TEXT  = "#E6EDF3"
INPUT_BG           = CARD_BG

DEFAULT_BAUDS = ["9600", "19200", "38400", "57600", "115200"]

def chat_content(page: ft.Page):
    ps = page.pubsub

    # --- área de mensajes
    chat_display = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    mounted = False

    def safe_update(ctrl: ft.Control):
        if ctrl.page: ctrl.update()

    def render_messages():
        chat_display.controls.clear()
        for msg in message_store.get_messages():
            is_user = msg["from"] == "user"
            bubble_bg   = BUBBLE_USER_BG   if is_user else BUBBLE_OTHER_BG
            text_color  = BUBBLE_USER_TEXT if is_user else BUBBLE_OTHER_TEXT
            align = ft.alignment.center_right if is_user else ft.alignment.center_left
            chat_display.controls.append(
                ft.Container(
                    content=ft.Text(f'[{msg["from"]}] {msg["text"]}', color=text_color),
                    bgcolor=bubble_bg,
                    padding=10,
                    margin=5,
                    border_radius=10,
                    alignment=align,
                    width=360,
                )
            )
        if chat_display.page: chat_display.update()

    # --- estilo
    def style_input(tf: ft.TextField):
        tf.bgcolor = INPUT_BG
        tf.color = TEXT_PRIMARY
        tf.border_color = CARD_BORDER
        tf.focused_border_color = PRIMARY
        tf.hint_style = ft.TextStyle(color=TEXT_MUTED)

    def style_dropdown(dd: ft.Dropdown):
        dd.bgcolor = INPUT_BG
        dd.color = TEXT_PRIMARY
        dd.border_color = CARD_BORDER
        dd.focused_border_color = PRIMARY

    # --- entrada de texto
    input_field = ft.TextField(hint_text="Escribe...", expand=True)
    style_input(input_field)

    def send_message(e):
        text = input_field.value.strip()
        if not text: return

        message_store.add_message("user", text)

        if serial_ref["svc"] and serial_ref["svc"].is_running:
            try:
                serial_ref["svc"].send(text)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error enviando al serial: {ex}"))
                page.snack_bar.open = True
                page.update()

        input_field.value = ""
        input_field.update()

    send_btn = ft.IconButton(icon=Icons.SEND, on_click=send_message)
    input_row = ft.Row([input_field, send_btn], spacing=5)

    # --- encabezado y estado
    status_text = ft.Text("Serial: desconectado", size=12, color=TEXT_MUTED)
    title = ft.Text("💬 Chat con el Asistente THD", size=20, color=TEXT_PRIMARY)

    # --- Serial controls
    port_dd = ft.Dropdown(label="Puerto", options=[], width=220)
    baud_dd = ft.Dropdown(
        label="Baudrate",
        options=[ft.dropdown.Option(v) for v in DEFAULT_BAUDS],
        value="9600", width=160
    )

    style_dropdown(port_dd)
    style_dropdown(baud_dd)

    def refresh_ports(e=None):
        ports = list_ports.comports()
        opts = []
        for p in ports:
            desc = f"{p.device} ({p.description})" if p.description else p.device
            opts.append(ft.dropdown.Option(key=p.device, text=desc))
        port_dd.options = opts
        if opts and (not port_dd.value or port_dd.value not in [o.key for o in opts]):
            port_dd.value = opts[0].key
        port_dd.update()

    refresh_btn = ft.IconButton(icon=Icons.REFRESH, tooltip="Actualizar puertos", on_click=refresh_ports)

    def connect(e):
        if serial_ref["svc"] and serial_ref["svc"].is_running:
            page.snack_bar = ft.SnackBar(ft.Text("Ya hay una conexión activa."))
            page.snack_bar.open = True
            page.update()
            return

        if not port_dd.value:
            page.snack_bar = ft.SnackBar(ft.Text("Selecciona un puerto."))
            page.snack_bar.open = True
            page.update()
            return

        try:
            svc = SerialService(port=port_dd.value, baudrate=int(baud_dd.value), pubsub=ps)
            svc.start()
            serial_ref["svc"] = svc   # ✅ publicar serial global
            status_text.value = f"Serial: conectado a {port_dd.value} @ {baud_dd.value}"
            status_text.color = PRIMARY
            safe_update(status_text)

        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"No se pudo conectar: {ex}"))
            page.snack_bar.open = True
            page.update()

    def disconnect(e):
        if serial_ref["svc"]:
            try: serial_ref["svc"].stop()
            except: pass
            serial_ref["svc"] = None

        status_text.value = "Serial: desconectado"
        status_text.color = TEXT_MUTED
        safe_update(status_text)

    connect_btn = ft.ElevatedButton("Conectar", icon=Icons.PLAY_ARROW, on_click=connect)
    disconnect_btn = ft.OutlinedButton("Desconectar", icon=Icons.STOP, on_click=disconnect)

    # --- FilePicker
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)
    page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if not e.files or not serial_ref["svc"]:
            return
        path = e.files[0].path
        try:
            serial_ref["svc"].send_from_file(path, default_interval=1.0)
            page.snack_bar = ft.SnackBar(ft.Text(f"Enviando archivo: {path}"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al enviar archivo: {ex}"))
            page.snack_bar.open = True
            page.update()

    file_picker.on_result = on_file_picked

    # --- Batch dialog
    commands_tf = ft.TextField(label="Comandos", multiline=True, min_lines=6, max_lines=12, width=360,
                               bgcolor=INPUT_BG, color=TEXT_PRIMARY, border_color=CARD_BORDER,
                               focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=TEXT_MUTED))
    interval_tf = ft.TextField(label="Intervalo (s)", width=120, value="1.0",
                               bgcolor=INPUT_BG, color=TEXT_PRIMARY, border_color=CARD_BORDER,
                               focused_border_color=PRIMARY, hint_style=ft.TextStyle(color=TEXT_MUTED))

    def send_batch_now(e):
        if not serial_ref["svc"]: return
        cmds = [ln.strip() for ln in (commands_tf.value or "").splitlines() if ln.strip()]
        try: interval = float(interval_tf.value or "1.0")
        except: interval = 1.0
        if cmds:
            serial_ref["svc"].send_lines(cmds, interval=interval)
        dlg.open = False; page.update()

    dlg = ft.AlertDialog(
        modal=True, title=ft.Text("Enviar lote de comandos", color=TEXT_PRIMARY),
        content=ft.Column([commands_tf, interval_tf], spacing=10),
        actions=[ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
                 ft.ElevatedButton("Enviar", on_click=send_batch_now)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)

    def open_batch_dialog(e): dlg.open = True; page.update()

    def stop_read(e):  
        if serial_ref["svc"]: serial_ref["svc"].stop_read()

    def start_read(e): 
        if serial_ref["svc"]: serial_ref["svc"].start_read()

    actions_row = ft.Row(
        [
            ft.ElevatedButton("Enviar lote…", icon=Icons.LIST, on_click=open_batch_dialog),
            ft.ElevatedButton("Enviar archivo…", icon=Icons.UPLOAD_FILE,
                              on_click=lambda e: file_picker.pick_files(allow_multiple=False)),
            ft.OutlinedButton("Detener lectura", icon=Icons.PAUSE, on_click=stop_read),
            ft.OutlinedButton("Reanudar lectura", icon=Icons.PLAY_ARROW, on_click=start_read),
        ],
        wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START,
    )

    controls_row = ft.Row(
        [port_dd, refresh_btn, baud_dd, connect_btn, disconnect_btn],
        wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START,
    )

    chat_ui = ft.Column(
        controls=[title, status_text, controls_row, actions_row, chat_display, input_row],
        expand=True,
    )

    root = ft.Container(content=chat_ui, bgcolor=CARD_BG)

    # PubSub
    def on_pubsub_msg(data):
        if isinstance(data, dict) and "from" in data and "text" in data:
            message_store.add_message(data["from"], data["text"])

    async def after_mount():
        ps.subscribe(on_pubsub_msg)
        message_store.subscribe(render_messages)
        render_messages()
        refresh_ports()

    page.run_task(after_mount)

    def on_close(e):
        if serial_ref["svc"]:
            serial_ref["svc"].stop()
            serial_ref["svc"] = None

    page.on_close = on_close
    return root
