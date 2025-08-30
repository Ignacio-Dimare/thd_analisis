import flet as ft

def apply_app_theme(page: ft.Page):
    # Paleta LIGHT (HEX)
    light = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#1E88E5",             # BLUE_600
            on_primary="#FFFFFF",
            secondary="#9C27B0",           # PURPLE_500
            on_secondary="#FFFFFF",
            background="#FAFAFA",          # GREY_50
            on_background="#000000",
            surface="#FFFFFF",
            on_surface="#000000",
            surface_variant="#F5F5F5",     # GREY_100
            on_surface_variant="#212121",  # GREY_900
            outline="#BDBDBD",             # GREY_400
            outline_variant="#E0E0E0",     # GREY_300
            error="#E53935",               # RED_600
            on_error="#FFFFFF",
            primary_container="#BBDEFB",   # BLUE_100
            on_primary_container="#0D47A1" # BLUE_900
        )
    )

    # Paleta DARK (HEX)
    dark = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#64B5F6",             # BLUE_300
            on_primary="#000000",
            secondary="#BA68C8",           # PURPLE_300
            on_secondary="#000000",
            background="#121212",          # material dark
            on_background="#FFFFFF",
            surface="#1E1E1E",
            on_surface="#FAFAFA",
            surface_variant="#424242",     # GREY_800
            on_surface_variant="#FAFAFA",
            outline="#616161",             # GREY_700
            outline_variant="#424242",     # GREY_800
            error="#EF5350",               # RED_400
            on_error="#000000",
            primary_container="#0D47A1",   # BLUE_900
            on_primary_container="#E3F2FD" # BLUE_50
        )
    )

    page.theme = light
    page.dark_theme = dark
    page.theme_mode = "system"  # o "light"/"dark"
