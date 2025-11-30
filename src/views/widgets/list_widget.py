"""
List Widget
Widget para representar una lista completa con pasos expandibles/colapsables
"""

import logging
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QCursor
from datetime import datetime

logger = logging.getLogger(__name__)


class ListStepPreview(QFrame):
    """
    Widget para mostrar un paso individual dentro de una lista expandida
    """

    # Señal emitida cuando se copia el contenido del paso
    step_copied = pyqtSignal(int, str, str)  # (step_number, label, content)

    def __init__(self, step_number: int, label: str, content: str, item_type: str, parent=None):
        """
        Inicializa el preview de un paso

        Args:
            step_number: Número del paso
            label: Etiqueta del paso
            content: Contenido del paso
            item_type: Tipo (TEXT, CODE, URL, PATH)
            parent: Widget padre
        """
        super().__init__(parent)
        self.step_number = step_number
        self.label = label
        self.content = content
        self.item_type = item_type

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        """Configura la interfaz del paso"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header: número + label
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Número del paso
        number_label = QLabel(f"{self.step_number}.")
        number_font = QFont()
        number_font.setBold(True)
        number_font.setPointSize(10)
        number_label.setFont(number_font)
        number_label.setStyleSheet("color: #4a9eff;")
        number_label.setFixedWidth(25)
        header_layout.addWidget(number_label)

        # Label del paso
        label_text = QLabel(self.label)
        label_font = QFont()
        label_font.setPointSize(10)
        label_text.setFont(label_font)
        label_text.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        label_text.setWordWrap(True)
        header_layout.addWidget(label_text, stretch=1)

        # Tipo badge
        type_badge = QLabel(self.item_type)
        type_badge.setStyleSheet("""
            QLabel {
                background-color: #3a3a3a;
                color: #aaaaaa;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
        """)
        type_badge.setFixedHeight(18)
        header_layout.addWidget(type_badge)

        layout.addLayout(header_layout)

        # Content preview (primeras 2 líneas)
        if self.content:
            content_lines = self.content.split('\n')
            preview_text = '\n'.join(content_lines[:2])
            if len(content_lines) > 2:
                preview_text += "..."

            content_label = QLabel(preview_text)
            content_label.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 9px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    padding: 4px;
                    background-color: #1a1a1a;
                    border-radius: 3px;
                }
            """)
            content_label.setWordWrap(True)
            content_label.setMaximumHeight(50)
            layout.addWidget(content_label)

        # Botón copiar
        copy_btn = QPushButton("📋 Copiar")
        copy_btn.setFixedWidth(80)
        copy_btn.setFixedHeight(24)
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_btn.clicked.connect(self.on_copy_clicked)
        layout.addWidget(copy_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def apply_styles(self):
        """Aplica estilos al frame"""
        self.setStyleSheet("""
            ListStepPreview {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                color: #e0e0e0;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)

    def on_copy_clicked(self):
        """Handler cuando se hace click en copiar"""
        self.step_copied.emit(self.step_number, self.label, self.content)


class ListWidget(QFrame):
    """
    Widget para mostrar una lista completa con capacidad de expandir/colapsar

    Estados:
    - Colapsado: Muestra nombre, icono, contador de pasos, metadata
    - Expandido: Muestra todos los pasos con preview + botones de acción
    """

    # Señales (nueva arquitectura v3.1.0)
    list_executed = pyqtSignal(int, int)  # (lista_id, category_id)
    list_edited = pyqtSignal(int, int)  # (lista_id, category_id)
    list_deleted = pyqtSignal(int, int)  # (lista_id, category_id)
    item_copied = pyqtSignal(str)  # (content)
    copy_all_requested = pyqtSignal(int, int)  # (lista_id, category_id)

    def __init__(self, list_data: Dict[str, Any], category_id: int,
                 list_items: List[Dict[str, Any]], parent=None):
        """
        Inicializa el widget de lista

        Args:
            list_data: Diccionario con metadata de la lista (nueva arquitectura v3.1.0)
                      Debe contener: id (lista_id), name, item_count, etc
            category_id: ID de la categoría
            list_items: Lista de items/pasos ordenados
            parent: Widget padre
        """
        super().__init__(parent)
        self.list_data = list_data
        self.category_id = category_id
        self.list_items = list_items
        self.is_expanded = False

        # Nueva arquitectura v3.1.0: usar lista_id y name
        self.lista_id = list_data.get('id', 0)
        self.list_name = list_data.get('name', 'Lista sin nombre')
        self.item_count = list_data.get('item_count', len(list_items))

        self.setup_ui()
        self.apply_styles()

        logger.debug(f"[LIST_WIDGET] Created for lista_id={self.lista_id}, name='{self.list_name}' ({self.item_count} steps)")

    def setup_ui(self):
        """Configura la interfaz del widget"""
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # === HEADER (siempre visible) ===
        self.header_widget = QWidget()
        self.header_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(4)

        # Primera línea: icono + nombre + toggle
        first_line = QHBoxLayout()
        first_line.setSpacing(8)

        # Icono de lista
        icon_label = QLabel("📝")
        icon_label.setFixedWidth(20)
        icon_font = QFont()
        icon_font.setPointSize(12)
        icon_label.setFont(icon_font)
        first_line.addWidget(icon_label)

        # Nombre de la lista
        name_label = QLabel(self.list_name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #e0e0e0;")
        first_line.addWidget(name_label, stretch=1)

        # Toggle button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.clicked.connect(self.toggle_expanded)
        first_line.addWidget(self.toggle_btn)

        header_layout.addLayout(first_line)

        # Segunda línea: metadata
        metadata_label = QLabel(f"{self.item_count} pasos")
        metadata_label.setStyleSheet("color: #888888; font-size: 10px;")
        header_layout.addWidget(metadata_label)

        self.main_layout.addWidget(self.header_widget)

        # === CONTENT AREA (expandible) ===
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(6)

        # Scroll area para los pasos
        steps_scroll = QScrollArea()
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        steps_scroll.setMaximumHeight(300)

        steps_container = QWidget()
        self.steps_layout = QVBoxLayout(steps_container)
        self.steps_layout.setSpacing(6)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)

        # Agregar pasos
        for item in self.list_items:
            step_widget = ListStepPreview(
                step_number=item.get('orden_lista', 0),
                label=item.get('label', 'Sin nombre'),
                content=item.get('content', ''),
                item_type=item.get('type', 'TEXT')
            )
            step_widget.step_copied.connect(self.on_step_copied)
            self.steps_layout.addWidget(step_widget)

        steps_scroll.setWidget(steps_container)
        content_layout.addWidget(steps_scroll)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3a3a3a;")
        separator.setFixedHeight(1)
        content_layout.addWidget(separator)

        # === BOTONES DE ACCIÓN ===
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        # Botón Ejecutar Todo
        execute_btn = QPushButton("⚡ Ejecutar Todo")
        execute_btn.setToolTip("Ejecutar pasos secuencialmente")
        execute_btn.clicked.connect(self.on_execute_clicked)
        actions_layout.addWidget(execute_btn)

        # Botón Copiar Todo
        copy_all_btn = QPushButton("📋 Copiar Todo")
        copy_all_btn.setToolTip("Copiar todo el contenido")
        copy_all_btn.clicked.connect(self.on_copy_all_clicked)
        actions_layout.addWidget(copy_all_btn)

        # Botón Editar
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.clicked.connect(self.on_edit_clicked)
        actions_layout.addWidget(edit_btn)

        # Botón Eliminar
        delete_btn = QPushButton("🗑️ Eliminar")
        delete_btn.setObjectName("deleteButton")
        delete_btn.clicked.connect(self.on_delete_clicked)
        actions_layout.addWidget(delete_btn)

        content_layout.addLayout(actions_layout)

        # Ocultar content inicialmente
        self.content_widget.setVisible(False)
        self.content_widget.setMaximumHeight(0)

        self.main_layout.addWidget(self.content_widget)

    def apply_styles(self):
        """Aplica estilos al widget"""
        self.setStyleSheet("""
            ListWidget {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 10px;
                color: #e0e0e0;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton#deleteButton {
                background-color: #3a2a2a;
                border: 1px solid #5a3a3a;
                color: #ff6666;
            }
            QPushButton#deleteButton:hover {
                background-color: #5a3a3a;
                border: 1px solid #7a4a4a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Estilo especial para el toggle button
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #aaaaaa;
                font-size: 12px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #e0e0e0;
            }
        """)

    def toggle_expanded(self):
        """Alterna entre estado expandido y colapsado"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.expand()
        else:
            self.collapse()

    def expand(self):
        """Expande el widget para mostrar los pasos"""
        self.is_expanded = True
        self.toggle_btn.setText("▲")
        self.content_widget.setVisible(True)

        # Animación suave
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(500)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

        logger.debug(f"[LIST_WIDGET] Expanded lista_id={self.lista_id}")

    def collapse(self):
        """Colapsa el widget para ocultar los pasos"""
        self.is_expanded = False
        self.toggle_btn.setText("▼")

        # Animación suave
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setStartValue(self.content_widget.height())
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(lambda: self.content_widget.setVisible(False))
        self.animation.start()

        logger.debug(f"[LIST_WIDGET] Collapsed lista_id={self.lista_id}")

    def on_step_copied(self, step_number: int, label: str, content: str):
        """Handler cuando se copia un paso individual"""
        import pyperclip
        try:
            pyperclip.copy(content)
            self.item_copied.emit(content)
            logger.info(f"[LIST_WIDGET] Step {step_number} copied: {label}")
        except Exception as e:
            logger.error(f"[LIST_WIDGET] Error copying step: {e}")

    def on_execute_clicked(self):
        """Handler para ejecutar todos los pasos secuencialmente"""
        self.list_executed.emit(self.lista_id, self.category_id)
        logger.info(f"[LIST_WIDGET] Execute requested for lista_id={self.lista_id}")

    def on_copy_all_clicked(self):
        """Handler para copiar todo el contenido"""
        self.copy_all_requested.emit(self.lista_id, self.category_id)
        logger.info(f"[LIST_WIDGET] Copy all requested for lista_id={self.lista_id}")

    def on_edit_clicked(self):
        """Handler para editar la lista"""
        self.list_edited.emit(self.lista_id, self.category_id)
        logger.info(f"[LIST_WIDGET] Edit requested for lista_id={self.lista_id}")

    def on_delete_clicked(self):
        """Handler para eliminar la lista"""
        from PyQt6.QtWidgets import QMessageBox

        # Confirmación
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar la lista '{self.list_name}' con {self.item_count} pasos?\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.list_deleted.emit(self.lista_id, self.category_id)
            logger.info(f"[LIST_WIDGET] Delete confirmed for lista_id={self.lista_id}")

    # Nueva arquitectura v3.1.0
    def get_lista_id(self) -> int:
        """Retorna el ID de la lista"""
        return self.lista_id

    def get_list_name(self) -> str:
        """Retorna el nombre de la lista"""
        return self.list_name

    # Método legacy (deprecado)
    def get_list_group(self) -> str:
        """DEPRECADO: Usar get_list_name() en su lugar"""
        return self.list_name

    def get_category_id(self) -> int:
        """Retorna el ID de categoría"""
        return self.category_id

    def get_item_count(self) -> int:
        """Retorna el número de pasos"""
        return self.item_count
