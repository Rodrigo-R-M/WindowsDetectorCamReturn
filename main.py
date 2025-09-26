# main.py (cliente PyQt6) - versión corregida y limpia
import sys
import requests
import os
import pickle
import json
import cv2
import numpy as np
import urllib.request
from VentanaRegistro import VentanaRegistro
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QLineEdit, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal


class VideoThread(QThread):
    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = False

    def run(self):
        self.running = True
        try:
            stream = urllib.request.urlopen(self.url, timeout=10)
            bytes_data = bytes()
            while self.running:
                chunk = stream.read(1024)
                if not chunk:
                    break
                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b + 2]
                    bytes_data = bytes_data[b + 2:]
                    img_array = np.frombuffer(jpg, dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    if frame is not None:
                        self.frame_received.emit(frame)
        except Exception as e:
            error_msg = f"Error en stream: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
        finally:
            try:
                stream.close()
            except:
                pass

    def stop(self):
        self.running = False
        self.wait(3000)


class MiInterfaz(QWidget):
    COOKIE_FILE = "session_cookies.pkl"

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.ip_servidor = None
        self.puerto_servidor = None
        self.url_publica = None
        self.camaras_disponibles = []
        self.camara_actual = 0
        self.streaming_activo = False
        self.video_thread = None

        if os.path.exists(self.COOKIE_FILE):
            with open(self.COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
                self.session.cookies.update(cookies)

        self.setWindowTitle("DetectorCam")
        self.setGeometry(100, 100, 1200, 800)

        self.setStyleSheet("""
            QWidget {
                background-color: #0A2463;
                color: #FFFFFF;
            }
            QFrame {
                background-color: #FFFFFF;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #1E3A8A;
                border: none;
                border-radius: 15px;
                padding: 5px;
                min-width: 70px;
                max-width: 80px;
            }
            QPushButton:hover {
                background-color: #0E2A68;
            }
            #titulo_principal {
                font-weight: bold;
                color: #FFFFFF;
            }
            #boton_camara {
                min-width: 100px;
                max-width: 120px;
                padding: 8px;
            }
            #boton_navegacion {
                min-width: 50px;
                max-width: 60px;
                font-size: 18px;
                font-weight: bold;
            }
        """)

        self.setup_ui()
        self.verificar_sesion()

    def setup_ui(self):
        self.boton_toggle = QPushButton()
        self.boton_toggle.setFixedSize(80, 80)
        self.boton_toggle.setIcon(QIcon("logoApp.svg"))
        self.boton_toggle.setIconSize(QSize(50, 50))
        self.boton_toggle.setObjectName("boton_toggle")
        self.boton_toggle.clicked.connect(self.toggle_menu)

        self.label_titulo = QLabel("DetectorCam")
        self.label_titulo.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        self.label_titulo.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_titulo.setFixedHeight(80)

        self.input_usuario_login = QLineEdit()
        self.input_usuario_login.setPlaceholderText("Usuario")
        self.input_usuario_login.setFixedWidth(100)
        self.input_usuario_login.setStyleSheet("background-color: white; color: black;")

        self.input_password_login = QLineEdit()
        self.input_password_login.setPlaceholderText("Contraseña")
        self.input_password_login.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password_login.setFixedWidth(100)
        self.input_password_login.setStyleSheet("background-color: white; color: black;")

        self.label_usuario = QLabel("")
        self.label_usuario.setStyleSheet("background: transparent;color: white; font-weight: bold;")
        self.label_usuario.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_usuario.hide()

        self.boton_login = QPushButton("Iniciar sesión")
        self.boton_register = QPushButton("Registrarse")
        self.boton_logout = QPushButton("Cerrar sesión")
        self.boton_logout.hide()

        self.boton_camara_remota = QPushButton("Activar Cámaras")
        self.boton_camara_remota.setObjectName("boton_camara")
        self.boton_camara_remota.setStyleSheet("""
            QPushButton#boton_camara {
                background-color: #1E3A8A;
                border: none;
                border-radius: 50px;
                padding: 8px;
                min-width: 80px;
                max-width: 120px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton#boton_camara:hover {
                background-color: #0E2A68;
            }
        """)
        self.boton_camara_remota.clicked.connect(self.llamar_cambio_estado)
        self.boton_camara_remota.hide()

        self.boton_login.clicked.connect(self.iniciar_sesion)
        self.boton_register.clicked.connect(self.abrir_registro)
        self.boton_logout.clicked.connect(self.cerrar_sesion)

        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setSpacing(20)
        self.menu_layout.setContentsMargins(5, 10, 15, 10)

        self.menu_layout.addWidget(self.input_usuario_login)
        self.menu_layout.addWidget(self.input_password_login)
        self.menu_layout.addWidget(self.boton_login)
        self.menu_layout.addWidget(self.boton_register)
        self.menu_layout.addWidget(self.label_usuario)
        self.menu_layout.addWidget(self.boton_logout)

        self.layout_boton_camara = QHBoxLayout()
        self.layout_boton_camara.addWidget(self.boton_camara_remota)
        self.layout_boton_camara.addStretch()
        self.menu_layout.addLayout(self.layout_boton_camara)

        self.menu_layout.addStretch(1)

        self.menu_widget.setLayout(self.menu_layout)
        self.menu_widget.setMaximumWidth(120)

        self.area_principal = QFrame()
        self.area_principal.setMinimumSize(400, 350)

        self.layout_area_principal = QVBoxLayout(self.area_principal)

        self.label_video = QLabel("")
        self.label_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_video.setStyleSheet("background: transparent;")
        self.label_video.setMinimumSize(400, 300)

        self.controls_widget = QWidget()
        self.controls_widget.setStyleSheet("background: transparent;")
        self.controls_layout = QHBoxLayout(self.controls_widget)

        self.boton_anterior = QPushButton("◀")
        self.boton_anterior.setObjectName("boton_navegacion")
        self.boton_anterior.clicked.connect(self.camara_anterior)
        self.boton_anterior.hide()

        self.label_camara_info = QLabel("")
        self.label_camara_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_camara_info.setStyleSheet("color: #333333; font-weight: bold; background: transparent;")
        self.label_camara_info.hide()

        self.boton_siguiente = QPushButton("▶")
        self.boton_siguiente.setObjectName("boton_navegacion")
        self.boton_siguiente.clicked.connect(self.camara_siguiente)
        self.boton_siguiente.hide()

        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.boton_anterior)
        self.controls_layout.addWidget(self.label_camara_info)
        self.controls_layout.addWidget(self.boton_siguiente)
        self.controls_layout.addStretch()

        self.layout_area_principal.addWidget(self.label_video)
        self.layout_area_principal.addWidget(self.controls_widget)

        layout_principal = QVBoxLayout()
        layout_superior = QHBoxLayout()
        layout_superior.addWidget(self.boton_toggle)
        layout_superior.addWidget(self.label_titulo)
        layout_superior.addStretch()
        layout_principal.addLayout(layout_superior)

        layout_inferior = QHBoxLayout()
        layout_inferior.addWidget(self.menu_widget)
        layout_inferior.addWidget(self.area_principal)
        layout_principal.addLayout(layout_inferior)

        self.setLayout(layout_principal)

    def toggle_menu(self):
        self.menu_widget.setVisible(not self.menu_widget.isVisible())

    def abrir_registro(self):
        ventana = VentanaRegistro()
        ventana.exec()

    def iniciar_sesion(self):
        username = self.input_usuario_login.text().strip()
        password = self.input_password_login.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Campos vacíos", "Por favor, completa todos los campos.")
            return

        try:
            response = self.session.post(
                "https://apidetectorcamreturn.onrender.com/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                with open(self.COOKIE_FILE, "wb") as f:
                    pickle.dump(self.session.cookies, f)

                QMessageBox.information(self, "Éxito", data.get("message", "Sesión iniciada"))
                self.verificar_sesion()
            else:
                data = response.json()
                QMessageBox.critical(self, "Error", data.get("detail", "Credenciales inválidas"))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de red", f"No se pudo conectar al servidor:\n{e}")

    def verificar_sesion(self) -> bool:
        try:
            resp = self.session.get("https://apidetectorcamreturn.onrender.com/check-auth")
            logged_in = (resp.status_code == 200)
        except:
            logged_in = False

        if logged_in:
            data = resp.json()
            if data.get("tipo") != "cliente":
                QMessageBox.warning(self, "Acceso denegado",
                                    "Solo los usuarios tipo 'cliente' pueden usar esta aplicación.")
                self.cerrar_sesion()
                return False

            self.ip_servidor = data.get("ip_servidor")
            self.puerto_servidor = data.get("puerto_servidor")
            self.url_publica = data.get("url_publica_servidor") or data.get("url_publica")
            print(f"💻 IP del servidor: {self.ip_servidor}")
            print(f"🔌 Puerto del servidor: {self.puerto_servidor}")
            print(f"🌐 URL Pública: {self.url_publica}")

            usuario = data.get("user", "")
            for w in (
                    self.input_usuario_login,
                    self.input_password_login,
                    self.boton_login,
                    self.boton_register
            ):
                w.hide()
            self.label_usuario.setText(usuario)
            self.label_usuario.show()
            self.boton_logout.show()
            self.boton_camara_remota.show()
        else:
            for w in (
                    self.input_usuario_login,
                    self.input_password_login,
                    self.boton_login,
                    self.boton_register
            ):
                w.show()
            self.label_usuario.hide()
            self.boton_logout.hide()
            self.boton_camara_remota.hide()

        return logged_in

    def cerrar_sesion(self):
        try:
            self.session.post("https://apidetectorcamreturn.onrender.com/logout")
        except Exception:
            pass

        self.detener_streaming()

        if os.path.exists(self.COOKIE_FILE):
            os.remove(self.COOKIE_FILE)

        for w in (
                self.input_usuario_login,
                self.input_password_login,
                self.boton_login,
                self.boton_register
        ):
            w.show()

        self.label_usuario.hide()
        self.boton_logout.hide()
        self.boton_camara_remota.hide()
        QMessageBox.information(self, "Cerrado", "Has cerrado la sesión")

    def llamar_cambio_estado(self):
        if not self.ip_servidor or not self.puerto_servidor:
            QMessageBox.warning(self, "Sin conexión", "No se tiene la IP o el puerto del servidor.")
            return

        if not self.streaming_activo:
            self.activar_streaming()
        else:
            self.detener_streaming()

    def activar_streaming(self):
        base_url = self.url_publica if self.url_publica else f"http://{self.ip_servidor}:{self.puerto_servidor}"

        url_activar = f"{base_url}/activar-camara"
        url_camaras = f"{base_url}/listar-camaras"

        try:
            self.boton_camara_remota.setText("Conectando...")
            self.label_video.setText("Activando cámaras...")
            self.label_video.setStyleSheet("color: #333333; font-size: 16px; background: transparent;")
            QApplication.processEvents()

            print("📡 Enviando petición para activar cámaras...")
            response = requests.get(url_activar, timeout=20)
            print(f"📨 Respuesta activar: {response.status_code}")

            if response.status_code != 200:
                error_msg = f"No se pudo activar las cámaras: {response.status_code}"
                print(f"❌ {error_msg}")
                QMessageBox.warning(self, "Error", error_msg)
                self.boton_camara_remota.setText("Activar Cámaras")
                self.label_video.clear()
                return

            self.label_video.setText("Obteniendo lista de cámaras...")
            QApplication.processEvents()
            import time
            time.sleep(1)

            print("📡 Solicitando lista de cámaras...")
            response_camaras = requests.get(url_camaras, timeout=5)
            print(f"📨 Respuesta lista cámaras: {response_camaras.status_code}")

            if response_camaras.status_code == 200:
                data = response_camaras.json()
                print(f"📋 Datos recibidos: {data}")

                self.camaras_disponibles = data.get("camaras", [])
                print(f"📹 Cámaras disponibles: {self.camaras_disponibles}")

                if not self.camaras_disponibles:
                    self.label_video.setText("El sistema no detecta ninguna cámara")
                    self.label_video.setStyleSheet(
                        "color: #ff6b6b; font-size: 18px; font-weight: bold; background: transparent;")
                    self.boton_camara_remota.setText("Activar Cámaras")
                    return

                camara_activa = data.get("camara_activa", False)
                print(f"🟢 Estado cámaras activas: {camara_activa}")

                if not camara_activa:
                    QMessageBox.warning(self, "Advertencia", "Las cámaras no están activas en el servidor")
                    self.boton_camara_remota.setText("Activar Cámaras")
                    self.label_video.clear()
                    return

                self.label_video.setText("Iniciando transmisión...")
                QApplication.processEvents()

                self.camara_actual = 0
                self.iniciar_video_stream()
                self.streaming_activo = True
                self.boton_camara_remota.setText("Desactivar")
                self.mostrar_controles_navegacion()

            else:
                error_msg = f"No se pudo obtener la lista de cámaras: {response_camaras.status_code}"
                print(f"❌ {error_msg}")
                QMessageBox.warning(self, "Error", error_msg)
                self.boton_camara_remota.setText("Activar Cámaras")

        except requests.exceptions.Timeout:
            error_msg = "Tiempo de espera agotado al conectar con el servidor"
            print(f"⏰ {error_msg}")
            QMessageBox.critical(self, "Error de conexión", error_msg)
            self.boton_camara_remota.setText("Activar Cámaras")
            self.label_video.clear()
        except requests.exceptions.ConnectionError:
            error_msg = "No se pudo conectar con el servidor de cámaras"
            print(f"🔌 {error_msg}")
            QMessageBox.critical(self, "Error de conexión", error_msg)
            self.boton_camara_remota.setText("Activar Cámaras")
            self.label_video.clear()
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            print(f"💥 {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
            self.boton_camara_remota.setText("Activar Cámaras")
            self.label_video.clear()

    def detener_streaming(self):
        if self.video_thread:
            try:
                self.video_thread.frame_received.disconnect()
            except:
                pass
            self.video_thread.stop()
            self.video_thread = None

        self.streaming_activo = False

        pixmap_blanco = QPixmap(400, 300)
        pixmap_blanco.fill(Qt.GlobalColor.white)
        self.label_video.setPixmap(pixmap_blanco)

        self.boton_camara_remota.setText("Activar Cámaras")
        self.ocultar_controles_navegacion()

        if self.ip_servidor and self.puerto_servidor:
            QTimer.singleShot(100, self.desactivar_servidor_async)

    def desactivar_servidor_async(self):
        try:
            url = f"http://{self.ip_servidor}:{self.puerto_servidor}/desactivar-camara"
            requests.get(url, timeout=2)
        except Exception:
            pass

    def iniciar_video_stream(self):
        """Inicia el stream de video desde la URL pública con la ruta /video/{índice}"""
        if self.video_thread:
            print("🛑 Deteniendo stream anterior...")
            self.video_thread.stop()
            self.video_thread = None

        if not self.url_publica:
            error_msg = "No se tiene URL pública del servidor"
            print(f"❌ {error_msg}")
            self.manejar_error_video(error_msg)
            return

        # ✅ CORREGIDO: Usar la ruta correcta del stream
        url = f"{self.url_publica}/video/{self.camara_actual}"

        print(f"🎥 Iniciando stream desde: {url}")

        # Crear y iniciar el thread de video
        self.video_thread = VideoThread(url)
        self.video_thread.frame_received.connect(self.mostrar_frame)
        self.video_thread.error_occurred.connect(self.manejar_error_video)
        self.video_thread.start()
        print("✅ Thread de video iniciado")

    def mostrar_frame(self, frame):
        if not self.streaming_activo:
            return
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.label_video.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.label_video.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error al mostrar frame: {e}")
            if self.streaming_activo:
                self.label_video.setText(f"Error al procesar imagen: {e}")
                self.label_video.setStyleSheet("color: #ff6b6b; font-size: 16px; background: transparent;")

    def manejar_error_video(self, error_msg):
        self.label_video.setText(f"Error: {error_msg}")
        self.label_video.setStyleSheet("color: #ff6b6b; font-size: 16px; background: transparent;")

    def mostrar_controles_navegacion(self):
        if len(self.camaras_disponibles) > 1:
            self.boton_anterior.show()
            self.boton_siguiente.show()
        self.label_camara_info.setText(f"Cámara {self.camara_actual + 1} de {len(self.camaras_disponibles)}")
        self.label_camara_info.show()

    def ocultar_controles_navegacion(self):
        self.boton_anterior.hide()
        self.boton_siguiente.hide()
        self.label_camara_info.hide()

    def camara_anterior(self):
        if len(self.camaras_disponibles) > 1:
            self.camara_actual = (self.camara_actual - 1) % len(self.camaras_disponibles)
            self.iniciar_video_stream()
            self.label_camara_info.setText(f"Cámara {self.camara_actual + 1} de {len(self.camaras_disponibles)}")

    def camara_siguiente(self):
        if len(self.camaras_disponibles) > 1:
            self.camara_actual = (self.camara_actual + 1) % len(self.camaras_disponibles)
            self.iniciar_video_stream()
            self.label_camara_info.setText(f"Cámara {self.camara_actual + 1} de {len(self.camaras_disponibles)}")

    def closeEvent(self, event):
        self.detener_streaming()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MiInterfaz()
    ventana.show()
    sys.exit(app.exec())