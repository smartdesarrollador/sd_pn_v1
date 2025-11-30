"""
List Editor Dialog
Ventana dedicada para editar listas existentes
"""

import logging
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QScrollArea,
    QWidget, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Importar el widget de paso
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from views.widgets.step_item_widget import StepItemWidget
from controllers.list_controller import ListController

logger = logging.getLogger(__name__)


class ListEditorDialog(QDialog):
    """
    Diálogo dedicado para editar listas existentes

    Características:
    - Precarga datos de lista existente
    - Permite renombrar lista (valida nuevo nombre único)
    - Permite agregar/eliminar/reordenar pasos
    - Actualiza lista existente en DB
    - Confirmación antes de eliminar pasos si lista original tiene muchos pasos
    """

    # Señal emitida cuando se actualiza la lista exitosamente
    # Nueva arquitectura v3.1.0: usa lista_id en lugar de list_name
    list_updated = pyqtSignal(int, int)  # (lista_id, category_id)

    def __init__(self, list_controller: ListController, category_id: int,
                 lista_id: int, categories: list, parent=None):
        """
        Inicializa el diálogo de edición de listas

        Args:
            list_controller: Controlador de listas
            category_id: ID de la categoría
            lista_id: ID de la lista a editar (nueva arquitectura v3.1.0)
            categories: Lista de categorías disponibles
            parent: Widget padre
        """
        super().__init__(parent)
        self.list_controller = list_controller
        self.category_id = category_id
        self.lista_id = lista_id
        self.categories = categories

        self.step_widgets: List[StepItemWidget] = []
        self.original_items_count = 0  # Para confirmación al eliminar
        self.original_list_name = ""  # Se cargará en load_list_data()

        # Obtener nombre de la lista para el título
        lista = self.list_controller.db.get_lista(lista_id)
        list_name = lista['name'] if lista else "Lista"

        self.setWindowTitle(f"✏️ Editar Lista - {list_name}")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self.setup_ui()
        self.apply_styles()

        # Cargar datos de la lista existente
        self.load_list_data()

        # Conectar señales del controlador (nueva arquitectura v3.1.0)
        self.list_controller.list_updated.connect(self.on_list_updated_signal)
        self.list_controller.list_renamed.connect(self.on_list_renamed_signal)
        self.list_controller.error_occurred.connect(self.on_error_signal)

        logger.info(f"[LIST_EDITOR] Dialog opened for lista_id: {lista_id}")

    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === HEADER ===
        header_label = QLabel("Edita los pasos de la lista existente")
        header_font = QFont()
        header_font.setPointSize(11)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: #aaaaaa;")
        main_layout.addWidget(header_label)

        # === NOMBRE DE LA LISTA ===
        name_label = QLabel("Nombre de la lista:*")
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        main_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre de la lista...")
        self.name_input.textChanged.connect(self.on_name_changed)
        main_layout.addWidget(self.name_input)

        # Label de validación del nombre
        self.name_validation_label = QLabel("")
        self.name_validation_label.setStyleSheet("color: #ff6666; font-size: 11px;")
        main_layout.addWidget(self.name_validation_label)

        # === CATEGORÍA (SOLO LECTURA) ===
        category_layout = QHBoxLayout()
        category_label = QLabel("Categoría:")
        category_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        category_label.setFixedWidth(150)
        category_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        for cat in self.categories:
            cat_id = cat.get('id') if isinstance(cat, dict) else cat.id
            cat_name = cat.get('name') if isinstance(cat, dict) else cat.name
            cat_icon = cat.get('icon') if isinstance(cat, dict) else cat.icon
            self.category_combo.addItem(f"{cat_icon} {cat_name}", cat_id)

        # Seleccionar categoría actual
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.category_id:
                self.category_combo.setCurrentIndex(i)
                break

        # Deshabilitar cambio de categoría (complejidad adicional)
        self.category_combo.setEnabled(False)
        category_layout.addWidget(self.category_combo)
        main_layout.addLayout(category_layout)

        # Info sobre categoría
        category_info_label = QLabel("ℹ️ La categoría no puede cambiarse al editar")
        category_info_label.setStyleSheet("color: #888888; font-size: 10px; font-style: italic;")
        main_layout.addWidget(category_info_label)

        # === SEPARADOR ===
        separator_label = QLabel("──────── Pasos del Proceso ────────")
        separator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator_label.setStyleSheet("color: #666666; margin: 10px 0;")
        main_layout.addWidget(separator_label)

        # === SCROLL AREA PARA PASOS ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Widget contenedor para los pasos
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(10)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.steps_container)
        main_layout.addWidget(scroll, stretch=1)

        # === BOTÓN AGREGAR PASO ===
        add_step_button = QPushButton("+ Agregar Paso")
        add_step_button.setFixedWidth(150)
        add_step_button.clicked.connect(self.add_step)
        main_layout.addWidget(add_step_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # === BOTONES DE ACCIÓN ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_button = QPushButton("Cancelar")
        cancel_button.setFixedWidth(120)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        self.save_button = QPushButton("Guardar Cambios")
        self.save_button.setFixedWidth(150)
        self.save_button.clicked.connect(self.save_changes)
        buttons_layout.addWidget(self.save_button)

        main_layout.addLayout(buttons_layout)

    def apply_styles(self):
        """Aplica estilos al diálogo"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4a9eff;
            }
            QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QComboBox:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 16px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QScrollArea {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)

        # Estilo especial para el botón guardar
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2a5a5a;
                border: 1px solid #3a7a7a;
                border-radius: 4px;
                padding: 8px 16px;
                color: #e0e0e0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a7a7a;
                border: 1px solid #4a9a9a;
            }
            QPushButton:pressed {
                background-color: #1a4a4a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                color: #666666;
            }
        """)

    def load_list_data(self):
        """Carga los datos de la lista existente (nueva arquitectura v3.1.0)"""
        try:
            # Obtener datos de la lista
            logger.info(f"[LIST_EDITOR] Loading list data:")
            logger.info(f"   - lista_id: {self.lista_id}")
            logger.info(f"   - category_id: {self.category_id}")

            # Obtener registro de la lista
            lista = self.list_controller.db.get_lista(self.lista_id)
            if not lista:
                logger.error(f"[LIST_EDITOR] Lista not found: lista_id={self.lista_id}")
                QMessageBox.critical(self, "Error", f"No se encontró la lista con ID {self.lista_id}")
                return

            # Guardar nombre original
            self.original_list_name = lista['name']

            # Obtener items de la lista (usando lista_id)
            items = self.list_controller.get_list_items(self.lista_id)

            logger.info(f"   - lista name: '{lista['name']}'")
            logger.info(f"   - items returned: {len(items) if items else 0}")

            if not items:
                logger.warning(f"[LIST_EDITOR] No items found for lista_id={self.lista_id}")
                QMessageBox.warning(self, "Advertencia", f"No se encontraron items en esta lista")
                return

            # Guardar conteo original
            self.original_items_count = len(items)

            # Cargar nombre de la lista
            self.name_input.setText(lista['name'])

            # Crear widgets para cada item
            for item in items:
                step_widget = StepItemWidget(item['orden_lista'])
                step_widget.set_step_data(
                    label=item['label'],
                    content=item['content'],
                    step_type=item['type']
                )

                # Conectar señales
                step_widget.delete_requested.connect(lambda w=step_widget: self.delete_step(w))
                step_widget.move_up_requested.connect(lambda w=step_widget: self.move_step_up(w))
                step_widget.move_down_requested.connect(lambda w=step_widget: self.move_step_down(w))
                step_widget.data_changed.connect(self.update_save_button_text)

                # Agregar al layout y lista
                self.steps_layout.addWidget(step_widget)
                self.step_widgets.append(step_widget)

            # Actualizar números y botones
            self.update_step_numbers()
            self.update_save_button_text()

            logger.info(f"[LIST_EDITOR] Loaded {len(items)} items for lista_id: {self.lista_id}")

        except Exception as e:
            logger.error(f"[LIST_EDITOR] Error loading list data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar la lista: {str(e)}")

    def add_step(self):
        """Agrega un nuevo paso a la lista"""
        step_number = len(self.step_widgets) + 1
        step_widget = StepItemWidget(step_number)

        # Conectar señales
        step_widget.delete_requested.connect(lambda: self.delete_step(step_widget))
        step_widget.move_up_requested.connect(lambda: self.move_step_up(step_widget))
        step_widget.move_down_requested.connect(lambda: self.move_step_down(step_widget))
        step_widget.data_changed.connect(self.update_save_button_text)

        # Agregar al layout y lista
        self.steps_layout.addWidget(step_widget)
        self.step_widgets.append(step_widget)

        # Actualizar números y botones
        self.update_step_numbers()
        self.update_save_button_text()

        logger.debug(f"[LIST_EDITOR] Added step {step_number}, total: {len(self.step_widgets)}")

    def delete_step(self, step_widget: StepItemWidget):
        """
        Elimina un paso de la lista

        Args:
            step_widget: Widget del paso a eliminar
        """
        # Mínimo 1 paso
        if len(self.step_widgets) <= 1:
            QMessageBox.warning(self, "Advertencia", "Debe haber al menos 1 paso en la lista")
            return

        # Confirmación si estamos eliminando pasos de lista original con muchos items
        if self.original_items_count > 5 and len(self.step_widgets) <= self.original_items_count:
            reply = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Está seguro de eliminar el paso '{step_widget.get_step_data()['label']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Eliminar widget
        self.steps_layout.removeWidget(step_widget)
        self.step_widgets.remove(step_widget)
        step_widget.deleteLater()

        # Actualizar números
        self.update_step_numbers()
        self.update_save_button_text()

        logger.debug(f"[LIST_EDITOR] Deleted step, remaining: {len(self.step_widgets)}")

    def move_step_up(self, step_widget: StepItemWidget):
        """Mueve un paso hacia arriba"""
        index = self.step_widgets.index(step_widget)
        if index == 0:
            return  # Ya está al principio

        # Intercambiar en la lista
        self.step_widgets[index], self.step_widgets[index - 1] = \
            self.step_widgets[index - 1], self.step_widgets[index]

        # Actualizar UI
        self.rebuild_steps_layout()
        self.update_step_numbers()

    def move_step_down(self, step_widget: StepItemWidget):
        """Mueve un paso hacia abajo"""
        index = self.step_widgets.index(step_widget)
        if index >= len(self.step_widgets) - 1:
            return  # Ya está al final

        # Intercambiar en la lista
        self.step_widgets[index], self.step_widgets[index + 1] = \
            self.step_widgets[index + 1], self.step_widgets[index]

        # Actualizar UI
        self.rebuild_steps_layout()
        self.update_step_numbers()

    def rebuild_steps_layout(self):
        """Reconstruye el layout de pasos después de reordenar"""
        # Limpiar layout
        while self.steps_layout.count():
            self.steps_layout.takeAt(0)

        # Re-agregar en nuevo orden
        for widget in self.step_widgets:
            self.steps_layout.addWidget(widget)

    def update_step_numbers(self):
        """Actualiza los números de los pasos y los botones de movimiento"""
        for i, widget in enumerate(self.step_widgets):
            widget.set_step_number(i + 1)
            # Habilitar/deshabilitar botones de movimiento
            widget.enable_move_buttons(
                enable_up=(i > 0),
                enable_down=(i < len(self.step_widgets) - 1)
            )

    def update_save_button_text(self):
        """Actualiza el texto del botón guardar con el contador de pasos"""
        total_steps = len(self.step_widgets)
        self.save_button.setText(f"Guardar Cambios ({total_steps} pasos)")

    def on_name_changed(self, text: str):
        """Callback cuando cambia el nombre de la lista"""
        if not text.strip():
            self.name_validation_label.setText("⚠ El nombre no puede estar vacío")
            return

        if len(text) > 100:
            self.name_validation_label.setText("⚠ El nombre es demasiado largo (máx 100 caracteres)")
            return

        # Validar unicidad (excluyendo la lista actual por ID)
        if text.strip() != self.original_list_name:
            if not self.list_controller.db.is_list_name_unique_v2(
                self.category_id, text.strip(), exclude_lista_id=self.lista_id
            ):
                self.name_validation_label.setText("⚠ Ya existe una lista con este nombre en la categoría")
                return

        # Todo OK
        self.name_validation_label.setText("")

    def validate_form(self) -> tuple[bool, str]:
        """
        Valida el formulario completo

        Returns:
            Tuple (is_valid, error_message)
        """
        # Validar nombre
        list_name = self.name_input.text().strip()
        if not list_name:
            return False, "El nombre de la lista no puede estar vacío"

        if len(list_name) > 100:
            return False, "El nombre es demasiado largo (máximo 100 caracteres)"

        # Validar pasos
        valid_steps = [w for w in self.step_widgets if w.has_label()]
        if len(valid_steps) == 0:
            return False, "Debe haber al menos 1 paso con nombre"

        return True, ""

    def get_steps_data(self) -> List[dict]:
        """
        Obtiene los datos de todos los pasos

        Returns:
            Lista de diccionarios con datos de cada paso
        """
        steps_data = []
        for widget in self.step_widgets:
            data = widget.get_step_data()
            # Solo incluir pasos que tengan al menos label
            if data['label']:
                steps_data.append(data)
        return steps_data

    def save_changes(self):
        """Guarda los cambios en la lista existente (nueva arquitectura v3.1.0)"""
        # Validar formulario
        is_valid, error_msg = self.validate_form()
        if not is_valid:
            QMessageBox.warning(self, "Validación", error_msg)
            return

        # Obtener datos
        new_list_name = self.name_input.text().strip()
        steps_data = self.get_steps_data()

        # Verificar si hubo cambios
        name_changed = new_list_name != self.original_list_name
        items_changed = len(steps_data) != self.original_items_count  # Simplificado

        if not name_changed and not items_changed:
            # Podría no haber cambios significativos, pero permitir guardar de todos modos
            pass

        # Actualizar lista a través del controlador (nueva arquitectura v3.1.0)
        success, message = self.list_controller.update_list(
            lista_id=self.lista_id,
            new_name=new_list_name if name_changed else None,
            description=None,  # TODO: Agregar campo description en UI
            items_data=steps_data
        )

        if success:
            QMessageBox.information(self, "Éxito", message)
            self.list_updated.emit(self.lista_id, self.category_id)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)

    def on_list_updated_signal(self, lista_id: int, category_id: int):
        """Callback cuando el controlador emite señal de lista actualizada (v3.1.0)"""
        logger.info(f"[LIST_EDITOR] List updated signal received: lista_id={lista_id}, category={category_id}")

    def on_list_renamed_signal(self, lista_id: int, old_name: str, new_name: str, category_id: int):
        """Callback cuando el controlador emite señal de lista renombrada (v3.1.0)"""
        logger.info(f"[LIST_EDITOR] List renamed signal received: lista_id={lista_id}, {old_name} -> {new_name}")

    def on_error_signal(self, error_message: str):
        """Callback cuando el controlador emite señal de error"""
        logger.error(f"[LIST_EDITOR] Error signal received: {error_message}")
