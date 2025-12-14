"""
Project Relation Widget - Widget para mostrar relaciones de proyecto

Muestra un elemento (tag, item, category, list, etc.) del proyecto con:
- Icono y nombre del elemento
- Botón clickeable para copiar al portapapeles
- Descripción/comentario (en modo edición)
- Controles de edición y eliminación (en modo edición)
- Botones de reordenamiento (en modo edición)
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                             QLabel, QFrame, QTextEdit, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
import logging

logger = logging.getLogger(__name__)


class ProjectRelationWidget(QWidget):
    """Widget para mostrar una relación proyecto-entidad"""

    # Señales
    copy_requested = pyqtSignal(str)  # Emite el contenido a copiar
    delete_requested = pyqtSignal(int)  # Emite relation_id
    edit_description_requested = pyqtSignal(int, str)  # relation_id, new_description
    move_up_requested = pyqtSignal(int)  # relation_id
    move_down_requested = pyqtSignal(int)  # relation_id
    checkbox_changed = pyqtSignal(int, bool)  # relation_id, checked

    def __init__(self, relation_data: dict, metadata: dict, view_mode: str = 'edit', show_ordering_arrows: bool = False, parent=None):
        """
        Args:
            relation_data: Diccionario con datos de la relación (id, project_id, entity_type, entity_id, description, order_index)
            metadata: Diccionario con metadata de la entidad (icon, name, content, type)
            view_mode: 'edit' o 'clean'
            show_ordering_arrows: Si True, muestra las flechas de ordenamiento (solo en modo edit)
        """
        super().__init__(parent)

        self.relation_data = relation_data
        self.metadata = metadata
        self.view_mode = view_mode
        self.show_ordering_arrows = show_ordering_arrows

        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz"""
        # Frame principal
        self.setObjectName("ProjectRelationWidget")

        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Container con borde
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #00ff88;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame:hover {
                border-color: #00ccff;
                background-color: #353535;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(5)

        # Fila superior: Checkbox + Botón principal + controles
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Checkbox para seleccionar posición de inserción (solo en modo edición)
        if self.view_mode == 'edit':
            self.checkbox = QCheckBox()
            self.checkbox.setToolTip("Marcar para insertar nuevos elementos debajo de este")
            self.checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 5px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #4d4d4d;
                    border-radius: 3px;
                    background-color: #2d2d2d;
                }
                QCheckBox::indicator:hover {
                    border-color: #00ff88;
                }
                QCheckBox::indicator:checked {
                    background-color: #00ff88;
                    border-color: #00ff88;
                }
                QCheckBox::indicator:checked:hover {
                    background-color: #00ccff;
                    border-color: #00ccff;
                }
            """)
            self.checkbox.stateChanged.connect(self.on_checkbox_changed)
            top_row.addWidget(self.checkbox)

        # Botón principal del elemento (clickeable para copiar)
        self.main_button = QPushButton(f"{self.metadata['icon']} {self.metadata['name']}")
        self.main_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.main_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 8px 12px;
                text-align: left;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff88,
                    stop:1 #00ccff
                );
                color: #000000;
                border-color: #00ff88;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.main_button.clicked.connect(self.on_copy_clicked)
        top_row.addWidget(self.main_button, 1)

        # Tipo de elemento (pequeño label)
        if self.view_mode == 'edit':
            type_label = QLabel(f"[{self.metadata['type']}]")
            type_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 8pt;
                    font-style: italic;
                }
            """)
            top_row.addWidget(type_label)

        # Controles de edición (solo en modo edición)
        if self.view_mode == 'edit':
            # Botones de reordenamiento (solo si show_ordering_arrows es True)
            if self.show_ordering_arrows:
                move_up_btn = QPushButton("▲")
                move_up_btn.setFixedSize(28, 28)
                move_up_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                move_up_btn.setStyleSheet(self._get_control_button_style())
                move_up_btn.setToolTip("Mover arriba")
                move_up_btn.clicked.connect(self.on_move_up)
                top_row.addWidget(move_up_btn)

                move_down_btn = QPushButton("▼")
                move_down_btn.setFixedSize(28, 28)
                move_down_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                move_down_btn.setStyleSheet(self._get_control_button_style())
                move_down_btn.setToolTip("Mover abajo")
                move_down_btn.clicked.connect(self.on_move_down)
                top_row.addWidget(move_down_btn)

            # Botón eliminar
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #e4475b;
                    border-color: #e4475b;
                }
            """)
            delete_btn.setToolTip("Eliminar de proyecto")
            delete_btn.clicked.connect(self.on_delete)
            top_row.addWidget(delete_btn)

        container_layout.addLayout(top_row)

        # Descripción/comentario (editable en modo edición)
        description = self.relation_data.get('description', '')
        if description or self.view_mode == 'edit':
            desc_container = QWidget()
            desc_layout = QHBoxLayout(desc_container)
            desc_layout.setContentsMargins(0, 0, 0, 0)
            desc_layout.setSpacing(5)

            if self.view_mode == 'edit':
                # TextEdit editable
                self.description_edit = QTextEdit()
                self.description_edit.setPlainText(description)
                self.description_edit.setMaximumHeight(60)
                self.description_edit.setPlaceholderText("Descripción o comentario del elemento...")
                self.description_edit.setStyleSheet("""
                    QTextEdit {
                        background-color: #252525;
                        color: #888888;
                        border: 1px solid #3d3d3d;
                        border-radius: 3px;
                        padding: 4px;
                        font-size: 9pt;
                        font-style: italic;
                    }
                """)
                self.description_edit.textChanged.connect(self.on_description_changed)
                desc_layout.addWidget(QLabel("└─"), 0)
                desc_layout.addWidget(self.description_edit, 1)
            else:
                # Label solo lectura
                if description:
                    desc_label = QLabel(f"└─ {description}")
                    desc_label.setWordWrap(True)
                    desc_label.setStyleSheet("""
                        QLabel {
                            color: #888888;
                            font-size: 9pt;
                            font-style: italic;
                        }
                    """)
                    desc_layout.addWidget(desc_label)

            container_layout.addWidget(desc_container)

        # Tags (chips visuales)
        self._add_tags_display(container_layout)

        main_layout.addWidget(container)

    def _add_tags_display(self, layout):
        """Agrega la visualización de tags"""
        try:
            from src.core.project_element_tag_manager import ProjectElementTagManager
            from src.views.widgets.project_tag_chip import ProjectTagChip
            from src.database.db_manager import DBManager

            # Obtener tags de esta relación
            relation_id = self.relation_data.get('id')
            if not relation_id:
                return

            # Crear tag manager (necesitamos el db_manager)
            # Por ahora usamos una instancia nueva, idealmente debería pasarse desde arriba
            db = DBManager()
            tag_manager = ProjectElementTagManager(db)

            # Obtener tags de la relación
            tags = tag_manager.get_relation_tags(relation_id)

            if tags:
                # Container de tags
                tags_container = QWidget()
                tags_layout = QHBoxLayout(tags_container)
                tags_layout.setContentsMargins(20, 5, 0, 5)
                tags_layout.setSpacing(5)

                # Label "Tags:"
                tags_label = QLabel("🏷️")
                tags_label.setStyleSheet("color: #888888; font-size: 9pt;")
                tags_layout.addWidget(tags_label)

                # Agregar chips de tags
                for tag in tags[:5]:  # Máximo 5 tags visibles
                    chip = ProjectTagChip(tag, removable=False)
                    chip.setMaximumHeight(24)
                    tags_layout.addWidget(chip)

                if len(tags) > 5:
                    more_label = QLabel(f"+{len(tags) - 5} más")
                    more_label.setStyleSheet("color: #888888; font-size: 8pt; font-style: italic;")
                    tags_layout.addWidget(more_label)

                tags_layout.addStretch()
                layout.addWidget(tags_container)

            db.close()

        except Exception as e:
            logger.warning(f"Could not load tags for relation: {e}")

    def _get_control_button_style(self) -> str:
        """Estilo para botones de control"""
        return """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                font-size: 9pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ff88;
                border-color: #00ff88;
                color: #000000;
            }
        """

    def on_copy_clicked(self):
        """Al hacer clic en el botón principal - copiar al portapapeles"""
        # Siempre copiar el nombre del elemento
        name = self.metadata.get('name', '').strip()

        if name:
            self.copy_requested.emit(name)
            logger.info(f"Copy requested (name): {name}")
        else:
            logger.warning(f"No name to copy for: {self.metadata}")

    def on_delete(self):
        """Al hacer clic en eliminar"""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar '{self.metadata['name']}' del proyecto?\n\nEl elemento original NO será eliminado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            relation_id = self.relation_data['id']
            self.delete_requested.emit(relation_id)
            logger.info(f"Delete requested for relation: {relation_id}")

    def on_description_changed(self):
        """Al cambiar la descripción"""
        if self.view_mode == 'edit' and hasattr(self, 'description_edit'):
            new_description = self.description_edit.toPlainText()
            relation_id = self.relation_data['id']
            self.edit_description_requested.emit(relation_id, new_description)

    def on_move_up(self):
        """Al hacer clic en mover arriba"""
        relation_id = self.relation_data['id']
        self.move_up_requested.emit(relation_id)
        logger.info(f"Move up requested for relation: {relation_id}")

    def on_move_down(self):
        """Al hacer clic en mover abajo"""
        relation_id = self.relation_data['id']
        self.move_down_requested.emit(relation_id)
        logger.info(f"Move down requested for relation: {relation_id}")

    def on_checkbox_changed(self, state):
        """Al cambiar el estado del checkbox"""
        if self.view_mode == 'edit' and hasattr(self, 'checkbox'):
            relation_id = self.relation_data['id']
            is_checked = state == Qt.CheckState.Checked.value
            self.checkbox_changed.emit(relation_id, is_checked)
            logger.info(f"Checkbox changed for relation {relation_id}: {is_checked}")

    def set_view_mode(self, mode: str):
        """Cambia el modo de vista"""
        if mode != self.view_mode:
            self.view_mode = mode
            # Recrear el widget con el nuevo modo
            self.clear_layout()
            self.init_ui()

    def clear_layout(self):
        """Limpia el layout actual"""
        layout = self.layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
