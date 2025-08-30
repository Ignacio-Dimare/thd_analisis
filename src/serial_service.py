# src/serial_service.py
import serial
import serial.tools.list_ports
import threading
import time
import re
import csv
from typing import List, Optional, Iterable


class SerialService:
    """
    Servicio de puerto serie con:
      - abrir/cerrar
      - lectura continua (publica en pubsub con sender 'gpib' y guarda log)
      - envío con \r \n
      - envío por lotes con intervalo
      - envío desde archivo con comando especial \D <seg>
      - ejecución de secuencia de medición (UP -> RL) con reintentos
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        pubsub=None,
        auto_read: bool = True,
        log_path: str = "log.txt",
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.pubsub = pubsub
        self.auto_read = auto_read
        self.log_path = log_path

        self.ser: Optional[serial.Serial] = None
        self._read_thread: Optional[threading.Thread] = None
        self._reading = False
        self._send_lock = threading.Lock()

        # Hilos auxiliares de envío
        self._batch_thread: Optional[threading.Thread] = None
        self._file_thread: Optional[threading.Thread] = None

    # ---------- Utilidades estáticas ----------
    @staticmethod
    def available_ports() -> List[str]:
        """Solo nombres de dispositivo, ej: ['COM3', 'COM5']"""
        return [p.device for p in serial.tools.list_ports.comports()]

    @staticmethod
    def available_ports_with_desc() -> List[tuple]:
        """(device, description)"""
        out = []
        for p in serial.tools.list_ports.comports():
            out.append((p.device, p.description))
        return out

    # ---------- Estado ----------
    @property
    def is_running(self) -> bool:
        return self.ser is not None and self.ser.is_open

    # ---------- Apertura / Cierre ----------
    def start(self):
        """Abre el puerto (y arranca lectura si auto_read=True)."""
        if self.is_running:
            return
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            # Algunos Arduinos reinician al abrir el puerto
            time.sleep(2)
            self._emit_system(f"Puerto {self.port} abierto @ {self.baudrate} bps.")
            if self.auto_read:
                self.start_read()
        except Exception as e:
            self._emit_system(f"Error al abrir el puerto: {e}")
            raise

    def stop(self):
        """Detiene lectura (si la hay) y cierra el puerto."""
        self.stop_read()
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self._emit_system("Puerto cerrado.")
        finally:
            self.ser = None

    # ---------- Lectura continua ----------
    def start_read(self, log_path: Optional[str] = None):
        """Inicia la lectura continua en hilo aparte y loguea a archivo."""
        if not self.is_running:
            self._emit_system("Puerto no está abierto.")
            return
        if self._reading:
            self._emit_system("Ya está leyendo.")
            return

        self._reading = True
        path = log_path or self.log_path

        def _loop():
            # abre el archivo una vez y escribe por línea
            try:
                with open(path, "a", encoding="utf-8") as log_file:
                    while self._reading:
                        try:
                            line = self.ser.readline()
                            if not line:
                                continue
                            txt = line.decode("utf-8", errors="ignore").strip()
                            if txt:
                                # publica al chat como 'gpib'
                                self._emit_chat(txt)
                                # persiste
                                log_file.write(txt + "\r\n")
                                log_file.flush()
                        except Exception as ex:
                            self._emit_system(f"Error al leer: {ex}")
                            break
            finally:
                self._reading = False

        self._read_thread = threading.Thread(target=_loop, daemon=True)
        self._read_thread.start()
        self._emit_system(f"Lectura continua iniciada (log: {path}).")

    def stop_read(self):
        """Detiene el hilo de lectura continua."""
        if not self._reading:
            return
        self._reading = False
        # pequeña espera para que termine
        time.sleep(0.1)
        self._emit_system("Lectura continua detenida.")

    # ---------- Envío ----------
    def send(self, data: str):
        """Envía una línea terminada en \\n."""
        if not self.is_running:
            self._emit_system("Puerto no está abierto.")
            return
        try:
            with self._send_lock:
                self.ser.write((data + "\r\n").encode("utf-8"))
        except Exception as e:
            self._emit_system(f"Error al enviar dato: {e}")

    def send_lines(self, commands: Iterable[str], interval: float = 1.0):
        """Envía una lista/iterable de líneas con un intervalo fijo (en segundos)."""
        if self._batch_thread and self._batch_thread.is_alive():
            self._emit_system("Ya hay un envío por lotes en curso.")
            return

        def _send_job():
            cmds = list(commands)
            total = len(cmds)
            for i, cmd in enumerate(cmds, start=1):
                if not self.is_running:
                    self._emit_system("Puerto no está abierto. Envío cancelado.")
                    break
                try:
                    with self._send_lock:
                        self.ser.write((cmd + "\r\n").encode("utf-8"))
                    self._emit_system(f"[{i}/{total}] Enviado: {cmd}")
                except Exception as e:
                    self._emit_system(f"Error al enviar: {e}")
                    break
                time.sleep(max(0.0, float(interval)))
            else:
                self._emit_system("✅ Envío de comandos terminado.")

        self._batch_thread = threading.Thread(target=_send_job, daemon=True)
        self._batch_thread.start()

    def send_from_file(self, filename: str, default_interval: float = 1.0):
        """
        Lee comandos de archivo y los envía con un delay ajustable.
        Reglas:
          - Líneas vacías o que empiezan con '#' se ignoran.
          - Comando especial:  \D <segundos>   cambia el intervalo de envío.
        """
        if self._file_thread and self._file_thread.is_alive():
            self._emit_system("Ya hay un envío desde archivo en curso.")
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        except FileNotFoundError:
            self._emit_system(f"Archivo no encontrado: {filename}")
            return

        def _file_job():
            interval = float(default_interval)
            total = len(lines)
            i = 0
            while i < total:
                line = lines[i]
                # Comando especial
                if line.startswith("\\"):
                    upper = line.upper()
                    if upper.startswith("\\D"):
                        parts = line.split()
                        if len(parts) == 2:
                            try:
                                interval = float(parts[1])
                                self._emit_system(f"⏱️  Intervalo cambiado a {interval} s.")
                            except Exception as e:
                                self._emit_system(f"⚠️  Error al interpretar delay: {line} → {e}")
                        else:
                            self._emit_system(f"⚠️  Formato inválido: {line}")
                    else:
                        self._emit_system(f"⚠️  Comando especial no reconocido: {line}")
                else:
                    # Enviar línea normal
                    if not self.is_running:
                        self._emit_system("❌ Puerto no está abierto.")
                        break
                    try:
                        with self._send_lock:
                            self.ser.write((line + "\r\n").encode("utf-8"))
                        self._emit_system(f"[{i+1}/{total}] Enviado: {line}")
                    except Exception as e:
                        self._emit_system(f"❌ Error al enviar '{line}': {e}")
                        break
                    time.sleep(max(0.0, interval))
                i += 1

            self._emit_system("✅ Envío de comandos finalizado.")

        self._file_thread = threading.Thread(target=_file_job, daemon=True)
        self._file_thread.start()

    # ---------- Secuencia de medición (con reintentos RL) ----------
    def run_measurement_sequence(
        self,
        repeats: int = 10,
        delay: float = 0.5,
        csv_path: Optional[str] = "thd_data.csv",
        start_hz: int = 1000,
        step_hz: int = 1000,
        rl_retries: int = 3,
        rl_retry_delay: float = 0.2,
    ) -> list[float]:
        """
        Ejecuta la secuencia de comandos y retorna los valores de RL en un vector.
        Si csv_path no es None, exporta a CSV con columnas (Frecuencia, THD) y
        frecuencias 1000, 2000, ... según la cantidad de lecturas.
        Reintenta reenviando 'RL' hasta rl_retries veces si no se obtiene número.
        """
        if not self.is_running:
            self._emit_system("Puerto no está abierto.")
            return []

        # Pausar lectura continua para que no consuma respuestas RL
        restart_read = False
        if getattr(self, "_reading", False):
            restart_read = True
            try:
                self.stop_read()
            except Exception:
                pass

        # Limpiar buffer de entrada para evitar arrastre de líneas viejas
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        sequence_init = [
            "CLR",
            "34.0SP",
            "P2",
            "O1",
            "AP 1.0VL",
            "FR 1.0KZ",
            "FN 1.0KZ",
            "S3",
            "RL",
        ]

        results: list[float] = []

        try:
            # Enviar secuencia inicial
            for cmd in sequence_init:
                self.send(cmd)
                time.sleep(delay)
                if cmd == "RL":
                    val = self._read_numeric_with_retries(
                        max_wait=self.timeout, retries=rl_retries, retry_delay=rl_retry_delay
                    )
                    results.append(val)

            # Repetir ciclo UP -> RL
            for _ in range(repeats):
                self.send("UP")
                time.sleep(delay)
                self.send("RL")
                time.sleep(delay)
                val = self._read_numeric_with_retries(
                    max_wait=self.timeout, retries=rl_retries, retry_delay=rl_retry_delay
                )
                results.append(val)

        except Exception as e:
            self._emit_system(f"Error en secuencia: {e}")
        finally:
            # Reanudar lectura continua si estaba activa antes
            if restart_read:
                try:
                    self.start_read()
                except Exception:
                    pass

        # Exportar CSV si se pidió
        if csv_path:
            self.save_thd_csv(results, csv_path, start_hz=start_hz, step_hz=step_hz)

        print("Fin de la trama")
        print(results)
        return results

    # ---------- Lecturas numéricas con reintentos ----------
    def _try_read_numeric_once(self, max_wait: float = 1.0) -> Optional[float]:
        """
        Intenta leer UNA respuesta numérica dentro de max_wait.
        Devuelve float si lo logra, o None si no hay número.
        No reintenta; eso lo maneja _read_numeric_with_retries.
        """
        deadline = time.time() + max(0.0, float(max_wait))
        last_txt = ""
        number_regex = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")

        while time.time() < deadline:
            try:
                line = self.ser.readline()  # bytes
            except Exception as e:
                self._emit_system(f"Error al leer respuesta: {e}")
                return None

            if not line:
                continue

            txt = line.decode("utf-8", errors="ignore").strip()
            last_txt = txt
            print(f"Linea (raw): {line!r}  -> '{txt}'")

            if not txt:
                continue

            # 1) intento directo
            try:
                return float(txt.replace(",", "."))
            except ValueError:
                pass

            # 2) extraer primer número válido en la línea
            m = number_regex.search(txt.replace(",", "."))
            if m:
                try:
                    val = float(m.group(0))
                    self._emit_system(f"Respuesta parseada: '{txt}' -> {val}")
                    return val
                except ValueError:
                    pass

        # Sin número en este intento
        self._emit_system(f"Timeout esperando número. Última respuesta: '{last_txt}'")
        return None

    def _read_numeric_with_retries(self, max_wait: float = 1.0, retries: int = 3, retry_delay: float = 0.2) -> float:
        """
        Lee un número con hasta 'retries' reintentos.
        Cada reintento reenvía 'RL', espera retry_delay y vuelve a leer.
        Rechaza valores > 100 por inválidos (se reintenta). Devuelve 0.0 si todos fallan.
        """
        # Primer intento
        val = self._try_read_numeric_once(max_wait=max_wait)
        if val is not None:
            if val <= 100.0:
                return val
            else:
                self._emit_system(f"Valor fuera de rango (>100): {val} → reintentando…")

        # Reintentos reenviando RL
        for i in range(1, retries + 1):
            self._emit_system(f"Reintentando RL ({i}/{retries})…")
            self.send("RL")
            time.sleep(max(0.0, retry_delay))

            val = self._try_read_numeric_once(max_wait=max_wait)
            if val is not None:
                if val <= 100.0:
                    return val
                else:
                    self._emit_system(f"Valor fuera de rango (>100): {val} (intento {i}/{retries})")

        self._emit_system("No se obtuvo valor válido tras reintentos → 0.0")
        return 0.0

    # ---------- Exportar CSV ----------
    def save_thd_csv(
        self,
        values: Iterable[float],
        csv_path: str,
        start_hz: int = 1000,
        step_hz: int = 1000,
        float_fmt: str = "{:.6f}",
    ) -> str:
        """
        Guarda un CSV con columnas: Frecuencia, THD
        Filas: 1000, v0 ; 2000, v1 ; 3000, v2 ; etc.
        """
        try:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Frecuencia", "THD"])
                for i, v in enumerate(values):
                    freq = start_hz + i * step_hz
                    # Si querés dejar el valor crudo sin formato, usa "v" en vez de float_fmt.format(v)
                    w.writerow([freq, float_fmt.format(v)])
            self._emit_system(f"CSV guardado: {csv_path}")
            return csv_path
        except Exception as e:
            self._emit_system(f"Error guardando CSV: {e}")
            return ""

    # ---------- Emisores ----------
    def _emit_chat(self, text: str):
        """Publica una línea recibida al chat como GPIB/Arduino."""
        if self.pubsub:
            try:
                self.pubsub.send_all({"from": "gpib", "text": text})
            except Exception:
                pass
        # También a consola para debug
        print(f"[Arduino] {text}")

    def _emit_system(self, text: str):
        """Mensajes de estado/errores (van al chat como 'system')."""
        if self.pubsub:
            try:
                self.pubsub.send_all({"from": "system", "text": text})
            except Exception:
                pass
        print(text)
