"""
Widget para items de tipo PATH

Muestra items de ruta de archivo/carpeta clickeable.
Para contenido extenso (>1500 chars) muestra botón de colapsar/expandir.

Autor: Widget Sidebar Team
Versión: 2.0
"""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from .base_item_widget import BaseItemWidget
from ...styles.full_view_styles import FullViewStyles
import subprocess
import os


class PathItemWidget(BaseItemWidget):
    """
    Widget para items de tipo PATH

    Características:
    - Muestra ruta de archivo/carpeta sin límites
    - Click en path abre en explorador de archivos
    - Icono 📁 para carpetas, 📄 para archivos
    - Para contenido extenso (>1500 chars): botón de colapsar/expandir
    - Por defecto: todo el contenido visible (expandido)
    """

    COLLAPSIBLE_LENGTH = 1500  # Límite para mostrar botón de colapso
    COLLAPSED_PREVIEW = 200    # Caracteres a mostrar cuando está colapsado

    def __init__(self, item_data: dict, parent=None):
        """
        Inicializar widget de item de path

        Args:
            item_data: Diccionario con datos del item
            parent: Widget padre
        """
        self.is_expanded = True  # Por defecto expandido
        self.content_label = None
        self.toggle_button = None
        super().__init__(item_data, parent)
        self.apply_styles()

    def render_content(self):
        """Renderizar contenido de PATH sin límites ni scroll"""
        # Layout horizontal para icono + título
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # Determinar icono según tipo de path
        path_content = self.get_item_content()
        icon = "📁" if os.path.isdir(path_content) else "📄"

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px;")
        title_layout.addWidget(icon_label)

        # Título
        label = self.get_item_label()
        if label and label != 'Sin título':
            title_label = QLabel(label)
            title_label.setWordWrap(True)
            title_label.setMaximumWidth(680)  # Menor porque hay icono
            title_label.setStyleSheet("""
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                word-break: break-word;
                overflow-wrap: anywhere;
            """)
            title_layout.addWidget(title_label)

        title_layout.addStretch()
        self.content_layout.addLayout(title_layout)

        # Path clickeable
        if path_content:
            self.content_label = QLabel()
            self.content_label.setObjectName("path_text")
            self.content_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.content_label.setMaximumWidth(720)  # Limitar ancho para evitar overflow
            self.content_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.content_label.setWordWrap(True)  # IMPORTANTE: ajustar al ancho
            self.content_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred
            )
            self.content_label.mousePressEvent = lambda event: self.open_path(path_content)
            self.content_label.setToolTip("Click para abrir en explorador")
            self.content_label.setStyleSheet("""
                color: #FFA500;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                word-wrap: break-word;
                word-break: break-word;
                overflow-wrap: anywhere;
            """)

            # Si el contenido es largo, mostrar todo por defecto (expandido)
            if len(path_content) > self.COLLAPSIBLE_LENGTH:
                self.content_label.setText(path_content)
                self.content_layout.addWidget(self.content_label)

                # Agregar botón de colapsar/expandir
                self.toggle_button = QPushButton("▲ Colapsar")
                self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
                self.toggle_button.clicked.connect(self.toggle_content)
                self.toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 1px solid #8B4513;
                        border-radius: 4px;
                        padding: 6px 12px;
                        color: #FFA500;
                        font-size: 12px;
                        font-weight: bold;
                        margin-top: 8px;
                    }
                    QPushButton:hover {
                        background-color: #2A2A2A;
                        border-color: #FFA500;
                    }
                """)
                self.content_layout.addWidget(self.toggle_button)
            else:
                # Contenido corto: mostrar todo sin botón
                self.content_label.setText(path_content)
                self.content_layout.addWidget(self.content_label)

        # Descripción (si existe)
        description = self.get_item_description()
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                color: #808080;
                font-size: 12px;
                font-style: italic;
                padding-top: 4px;
                font-family: 'Segoe UI', Arial, sans-serif;
            """)
            desc_label.setWordWrap(True)
            self.content_layout.addWidget(desc_label)

    def toggle_content(self):
        """Alternar entre contenido colapsado y expandido"""
        content = self.get_item_content()

        if self.is_expanded:
            # Colapsar: mostrar solo preview
            preview = content[:self.COLLAPSED_PREVIEW] + "..."
            self.content_label.setText(preview)
            self.toggle_button.setText("▼ Expandir")
            self.is_expanded = False
        else:
            # Expandir: mostrar todo
            self.content_label.setText(content)
            self.toggle_button.setText("▲ Colapsar")
            self.is_expanded = True

    def open_path(self, path: str):
        """
        Abrir path en explorador de archivos

        Args:
            path: Ruta a abrir
        """
        try:
            if os.path.exists(path):
                # Windows: abrir en explorador con selección
                subprocess.Popen(f'explorer /select,"{path}"')
                print(f"✓ Path abierto: {path}")
            else:
                print(f"✗ Path no existe: {path}")
        except Exception as e:
            print(f"✗ Error al abrir path: {e}")

    def apply_styles(self):
        """Aplicar estilos CSS"""
        self.setStyleSheet(FullViewStyles.get_path_item_style())
