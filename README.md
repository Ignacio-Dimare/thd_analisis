# THD Analyzer – Interfaz Flet para medición por puerto serial

Este proyecto es una aplicación gráfica hecha con **Flet + Python** para comunicarte con un analizador THD (u otro equipo de medición) mediante **puerto serial (COM/USB)**, ejecutar secuencias de mediciones y visualizar resultados en tiempo real mediante un gráfico THD vs Frecuencia. Este proyecto fue diseñado con el proposito especifico de comunicarse con un equipo Amber 5500 GPIB mediante un Arduino capaz de convertir el COM/USB a GPIB

## Características principales
- Interfaz gráfica en Flet
- Comunicación serial (pyserial)
- Chat para enviar comandos manuales
- Envío de comandos por lote y archivos
- Ejecución automática de secuencias
- Guardado automático en `thd_data.csv`
- Gráfico dinámico THD vs Frecuencia (Plotly)
- Lectura continua del CSV para actualizar el gráfico

---

## 📂 Estructura del proyecto

```
src/
 ├── main.py                  # Punto de entrada de la app
 ├── chat.py                  # Panel derecho: serial, chat y comandos
 ├── graph.py                 # Panel izquierdo: gráfico dinámico THD
 ├── serial_service.py        # Manejo de comunicación serial
storage/
 └── data/
     └── message_storage_instance.py # Almacenamiento de mensajes
pyproject.toml               
README.md                    
```

---

## Descripción rápida de cada archivo

| Archivo | Función |
|--------|--------|
`main.py` | Layout principal (split: gráfico + chat) |
`chat.py` | Puerto serial, chat, envío de comandos, secuencia RL |
`graph.py` | Configuración gráfico, lectura CSV, actualización gráfica |
`serial_service.py` | Comunicación serial y medición automática |
`message_storage_instance.py` | Buffer y suscripción de mensajes UI |

---

## Cómo inicializar el proyecto
### Con Poetry
```bash
poetry install
poetry run python src/main.py
```
---

## Archivos generados automáticamente

| Archivo | Propósito |
|---|---|
`log.txt` | Registro de datos recibidos |
`thd_data.csv` | Datos de medición para graficar |

---

## Stack Tecnológico

- Python 3.9+
- Flet
- PySerial
- Plotly
- Pandas

---

## Autores

Proyecto para mediciones THD vía puerto serial desarrollado por:
1. Campagnoli Felipe
2. Dimare Ignacio
3. Dominguez Matias

---
