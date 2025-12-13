"""
Widget para items de tipo URL

Muestra items de URL con formato de enlace clickeable.
Para contenido extenso (>1500 chars) muestra botón de colapsar/expandir.

Autor: Widget Sidebar Team
Versión: 2.0
"""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from .base_item_widget import BaseItemWidget
from ...styles.full_view_styles import FullViewStyles
import webbrowser


class URLItemWidget(BaseItemWidget):
    """
    Widget para items de tipo URL

    Características:
    - Muestra URL como enlace sin límites
    - Click en URL abre en navegador predeterminado
    - Icono 🔗 para identificación visual
    - Para contenido extenso (>1500 chars): botón de colapsar/expandir
    - Por defecto: todo el contenido visible (expandido)
    """

    COLLAPSIBLE_LENGTH = 1500  # Límite para mostrar botón de colapso
    COLLAPSED_PREVIEW = 200    # Caracteres a mostrar cuando está colapsado

    def __init__(self, item_data: dict, parent=None):
        """
        Inicializar widget de item de URL

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
        """Renderizar contenido de URL sin límites ni scroll"""
        # Layout horizontal para icono + título
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # Icono de enlace
        icon_label = QLabel("🔗")
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

        # URL clickeable
        content = self.get_item_content()
        if content:
            self.content_label = QLabel()
            self.content_label.setObjectName("url_text")
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
            self.content_label.mousePressEvent = lambda event: self.open_url(content)
            self.content_label.setToolTip("Click para abrir en navegador")
            self.content_label.setStyleSheet("""
                color: #5BA4E5;
                font-size: 13px;
                text-decoration: underline;
                font-family: 'Segoe UI', Arial, sans-serif;
                word-wrap: break-word;
                word-break: break-word;
                overflow-wrap: anywhere;
            """)

            # Si el contenido es largo, mostrar todo por defecto (expandido)
            if len(content) > self.COLLAPSIBLE_LENGTH:
                self.content_label.setText(content)
                self.content_layout.addWidget(self.content_label)

                # Agregar botón de colapsar/expandir
                self.toggle_button = QPushButton("▲ Colapsar")
                self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
                self.toggle_button.clicked.connect(self.toggle_content)
                self.toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 1px solid #2C3E73;
                        border-radius: 4px;
                        padding: 6px 12px;
                        color: #5BA4E5;
                        font-size: 12px;
                        font-weight: bold;
                        margin-top: 8px;
                    }
                    QPushButton:hover {
                        background-color: #232342;
                        border-color: #5BA4E5;
                    }
                """)
                self.content_layout.addWidget(self.toggle_button)
            else:
                # Contenido corto: mostrar todo sin botón
                self.content_label.setText(content)
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

    def open_url(self, url: str):
        """
        Abrir URL en navegador predeterminado

        Args:
            url: URL a abrir
        """
        try:
            webbrowser.open(url)
            print(f"✓ URL abierta: {url}")
        except Exception as e:
            print(f"✗ Error al abrir URL: {e}")

    def apply_styles(self):
        """Aplicar estilos CSS"""
        self.setStyleSheet(FullViewStyles.get_url_item_style())
