# VentanaRegistro.py
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFrame, QMessageBox, QComboBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import requests

class VentanaRegistro(QDialog):
    API_URL = "https://apidetectorcamreturn.onrender.com/register"  # ✅ Sin espacios

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro de usuario")
        self.setFixedSize(700, 700)

        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(40, 40, 40, 40)

        self.label_titulo = QLabel("Registrarse")
        self.label_titulo.setObjectName("titulo")
        self.label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(self.label_titulo)

        contenedor = QFrame()
        contenedor.setObjectName("contenedor")

        layout_contenedor = QVBoxLayout(contenedor)
        layout_contenedor.setContentsMargins(30, 30, 30, 30)
        layout_contenedor.setSpacing(15)

        campos = [
            ("Nombre completo:", QLineEdit()),
            ("Nombre de usuario:", QLineEdit()),
            ("Correo:", QLineEdit()),
            ("Contraseña:", QLineEdit()),
            ("Confirmar contraseña:", QLineEdit())
        ]

        self.inputs = {}
        for label_text, widget in campos:
            etiqueta = QLabel(label_text)
            layout_contenedor.addWidget(etiqueta)
            if "Contraseña" in label_text:
                widget.setEchoMode(QLineEdit.EchoMode.Password)
            layout_contenedor.addWidget(widget)
            self.inputs[label_text] = widget

        etiqueta_tipo = QLabel("Tipo de usuario:")
        layout_contenedor.addWidget(etiqueta_tipo)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["cliente"])
        layout_contenedor.addWidget(self.combo_tipo)

        self.boton_registrar = QPushButton("Registrarse")
        self.boton_registrar.setObjectName("registrar")
        self.boton_registrar.clicked.connect(self.registrar_usuario)
        layout_contenedor.addWidget(self.boton_registrar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_principal.addWidget(contenedor)
        self.setLayout(layout_principal)

    def registrar_usuario(self):
        nombre = self.inputs["Nombre completo:"].text().strip()
        username = self.inputs["Nombre de usuario:"].text().strip()
        email = self.inputs["Correo:"].text().strip()
        pw1 = self.inputs["Contraseña:"].text()
        pw2 = self.inputs["Confirmar contraseña:"].text()
        tipo = self.combo_tipo.currentText()

        if not all([nombre, username, email, pw1, pw2]):
            QMessageBox.warning(self, "Campos vacíos", "Rellena todos los campos.")
            return
        if pw1 != pw2:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return

        try:
            resp_cliente = requests.post(self.API_URL, json={
                "username": username,
                "email": email,
                "password": pw1,
                "tipo": "cliente"
            })

            username_server = f"{username}_server"
            email_server = f"{username}_server@example.com"

            resp_server = requests.post(self.API_URL, json={
                "username": username_server,
                "email": email_server,
                "password": pw1,
                "tipo": "server"
            })

            if resp_cliente.status_code == 200 and resp_server.status_code == 200:
                QMessageBox.information(self, "Registro exitoso",
                                        f"Usuarios creados:\n- Cliente: {username}\n- Servidor: {username_server}")
                self.accept()
            else:
                errores = []
                for r, rol in [(resp_cliente, "cliente"), (resp_server, "server")]:
                    if r.status_code != 200:
                        errores.append(f"{rol}: {r.json().get('detail', 'Error desconocido')}")
                QMessageBox.critical(self, "Error de registro", "\n".join(errores))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de red", f"No se pudo conectar al servidor:\n{e}")