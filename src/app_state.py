# src/app_state.py
from typing import Any, Dict

# Contenedor simple y compartido entre módulos
serial_ref: Dict[str, Any] = {"svc": None}
