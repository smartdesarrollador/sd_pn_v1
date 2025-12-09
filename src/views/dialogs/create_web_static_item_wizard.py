"""
Wizard para crear items de tipo WEB_STATIC.
Permite crear aplicaciones web estáticas con validación y seguridad.
"""

import sys
from pathlib import Path
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QPlainTextEdit, QStackedWidget,
    QMessageBox, QWidget, QFormLayout, QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.html_validator import validate_web_static_content
from utils.constants import ITEM_TYPE_ICONS
from views.widgets.project_tag_selector import ProjectTagSelector
from core.global_tag_manager import GlobalTagManager

logger = logging.getLogger(__name__)


class CreateWebStaticItemWizard(QDialog):
    """Wizard para crear items WEB_STATIC en 2 pasos"""

    item_created = pyqtSignal()  # Señal emitida al crear item exitosamente

    def __init__(self, controller, parent=None):
        """
        Inicializa el wizard.

        Args:
            controller: MainController instance
            parent: Widget padre
        """
        super().__init__(parent)
        self.controller = controller
        self.current_step = 0
        self.total_steps = 2

        # Initialize GlobalTagManager
        self.global_tag_manager = None
        try:
            self.global_tag_manager = GlobalTagManager(controller.config_manager.db)
        except Exception as e:
            logger.error(f"Could not initialize GlobalTagManager: {e}")

        self.setWindowTitle("Crear Item Web Estático")
        self.setModal(True)
        self.resize(900, 700)

        self._init_ui()
        self._update_ui_state()

        logger.info("CreateWebStaticItemWizard initialized")

    def _init_ui(self):
        """Inicializa la interfaz del wizard"""
        # Aplicar tema oscuro consistente con el proyecto
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #00d4ff;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
                border-color: #3d3d3d;
            }
            QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
                border-color: #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_widget = self._create_header()
        layout.addWidget(header_widget)

        # Stacked widget para los pasos
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background-color: #252525;
                border: none;
            }
        """)
        layout.addWidget(self.stack)

        # Paso 1: Configuración básica
        self.step1_widget = self._create_step1()
        self.stack.addWidget(self.step1_widget)

        # Paso 2: Editor de código
        self.step2_widget = self._create_step2()
        self.stack.addWidget(self.step2_widget)

        # Barra de navegación
        nav_bar = self._create_navigation_bar()
        layout.addWidget(nav_bar)

    def _create_header(self) -> QWidget:
        """Crea el header con título y progreso"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom: 2px solid #00d4ff;
            }
        """)
        header_widget.setFixedHeight(80)

        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Título
        title = QLabel("🌐 Crear Item Web Estático")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #00d4ff;")
        header_layout.addWidget(title)

        # Indicador de paso
        self.step_label = QLabel()
        self.step_label.setStyleSheet("color: #888888; font-size: 10pt;")
        header_layout.addWidget(self.step_label)

        return header_widget

    def _create_step1(self) -> QWidget:
        """Paso 1: Configuración básica (categoría, tags, label)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Instrucciones
        intro_label = QLabel(
            "Configure la información básica del item web estático.\n"
            "Las aplicaciones web estáticas pueden ser calculadoras, conversores, "
            "timers o cualquier herramienta HTML/CSS/JS."
        )
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet(
            "background-color: #2d2d2d; "
            "padding: 15px; "
            "border-radius: 6px; "
            "border-left: 4px solid #00d4ff;"
        )
        layout.addWidget(intro_label)

        # Formulario
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Label del item
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Ej: Calculadora de Propinas")
        self.label_input.setMinimumHeight(35)
        form_layout.addRow("Nombre del Item: *", self.label_input)

        # Categoría
        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(35)
        self._load_categories()
        form_layout.addRow("Categoría: *", self.category_combo)

        # Tags con ProjectTagSelector
        tags_label = QLabel("Tags:")
        form_layout.addRow(tags_label)

        if self.global_tag_manager:
            self.tag_selector = ProjectTagSelector(self.global_tag_manager)
            self.tag_selector.setMinimumHeight(150)
            form_layout.addRow(self.tag_selector)
        else:
            # Fallback if no manager available
            self.tag_selector = QLineEdit()
            self.tag_selector.setPlaceholderText("tag1, tag2, tag3 (separados por coma)")
            self.tag_selector.setMinimumHeight(35)
            form_layout.addRow(self.tag_selector)

        # Tipo (readonly)
        type_label = QLabel(f"{ITEM_TYPE_ICONS['WEB_STATIC']} WEB_STATIC")
        type_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11pt;")
        form_layout.addRow("Tipo:", type_label)

        # Descripción
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Breve descripción de la aplicación web")
        self.description_input.setMinimumHeight(35)
        form_layout.addRow("Descripción:", self.description_input)

        layout.addWidget(form_widget)
        layout.addStretch()

        return widget

    def _create_step2(self) -> QWidget:
        """Paso 2: Editor de código HTML"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Instrucciones
        info_label = QLabel(
            "Ingrese el código HTML completo de su aplicación web estática.\n"
            "Puede incluir CSS (en <style>) y JavaScript (en <script>).\n\n"
            "⚠️ Límites: 100 KB recomendado, 500 KB máximo"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "background-color: #2d2d2d; "
            "padding: 15px; "
            "border-radius: 6px; "
            "border-left: 4px solid #FFA726;"
        )
        layout.addWidget(info_label)

        # Editor de código
        editor_label = QLabel("Código HTML:")
        editor_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(editor_label)

        self.html_editor = QPlainTextEdit()
        self.html_editor.setPlaceholderText(
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            "    <title>Mi App</title>\n"
            "    <style>\n"
            "        /* CSS aquí */\n"
            "        body {\n"
            "            font-family: Arial, sans-serif;\n"
            "            padding: 20px;\n"
            "        }\n"
            "    </style>\n"
            "</head>\n"
            "<body>\n"
            "    <h1>Mi Aplicación</h1>\n"
            "    <script>\n"
            "        // JavaScript aquí\n"
            "        console.log('Hola Mundo');\n"
            "    </script>\n"
            "</body>\n"
            "</html>"
        )
        self.html_editor.setFont(QFont("Consolas", 10))
        self.html_editor.setMinimumHeight(300)
        layout.addWidget(self.html_editor, stretch=1)

        # Barra de estado del validador
        self.validation_status = QLabel("⚪ Estado: Sin validar")
        self.validation_status.setStyleSheet(
            "padding: 8px; "
            "background-color: #2d2d2d; "
            "border-radius: 4px; "
            "font-weight: bold;"
        )
        layout.addWidget(self.validation_status)

        # Botón de validación
        validate_btn = QPushButton("🔍 Validar HTML")
        validate_btn.clicked.connect(self._validate_html)
        validate_btn.setMinimumHeight(40)
        validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #000000;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
        """)
        layout.addWidget(validate_btn)

        # Área de resultados de validación (oculta por defecto)
        self.validation_output = QTextEdit()
        self.validation_output.setReadOnly(True)
        self.validation_output.setMaximumHeight(150)
        self.validation_output.setVisible(False)
        self.validation_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #00d4ff;
            }
        """)
        layout.addWidget(self.validation_output)

        return widget

    def _load_categories(self):
        """Carga categorías disponibles en el combo"""
        categories = self.controller.config_manager.get_categories()

        for category in categories:
            self.category_combo.addItem(
                f"{category.icon} {category.name}",
                category.id
            )

    def _create_navigation_bar(self) -> QWidget:
        """Crea la barra de navegación con botones"""
        nav_widget = QWidget()
        nav_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-top: 1px solid #3d3d3d;
            }
        """)
        nav_widget.setFixedHeight(70)

        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(20, 15, 20, 15)

        # Botón Atrás
        self.back_btn = QPushButton("← Atrás")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setMinimumWidth(120)
        self.back_btn.setMinimumHeight(40)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        # Botón Cancelar
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.setMinimumHeight(40)
        nav_layout.addWidget(self.cancel_btn)

        # Botón Siguiente
        self.next_btn = QPushButton("Siguiente →")
        self.next_btn.clicked.connect(self._go_next)
        self.next_btn.setMinimumWidth(120)
        self.next_btn.setMinimumHeight(40)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #000000;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
        """)
        nav_layout.addWidget(self.next_btn)

        # Botón Crear
        self.create_btn = QPushButton("✓ Crear Item")
        self.create_btn.clicked.connect(self._create_item)
        self.create_btn.setMinimumWidth(140)
        self.create_btn.setMinimumHeight(40)
        self.create_btn.setVisible(False)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
        """)
        nav_layout.addWidget(self.create_btn)

        return nav_widget

    def _update_ui_state(self):
        """Actualiza el estado de la UI según el paso actual"""
        # Actualizar label de paso
        self.step_label.setText(f"Paso {self.current_step + 1} de {self.total_steps}")

        # Actualizar visibilidad de botones
        if self.current_step == 0:
            self.back_btn.setEnabled(False)
            self.next_btn.setVisible(True)
            self.create_btn.setVisible(False)
        else:
            self.back_btn.setEnabled(True)
            self.next_btn.setVisible(False)
            self.create_btn.setVisible(True)

        # Cambiar widget del stack
        self.stack.setCurrentIndex(self.current_step)

    def _go_next(self):
        """Avanza al siguiente paso"""
        if self.current_step == 0:
            # Validar paso 1
            if not self.label_input.text().strip():
                QMessageBox.warning(
                    self,
                    "Campo Requerido",
                    "El nombre del item es obligatorio."
                )
                return

            # Avanzar a paso 2
            self.current_step = 1
            self._update_ui_state()
            logger.info("Avanzado a paso 2 (editor HTML)")

    def _go_back(self):
        """Retrocede al paso anterior"""
        if self.current_step == 1:
            self.current_step = 0
            self._update_ui_state()
            logger.info("Retrocedido a paso 1 (configuración)")

    def _validate_html(self):
        """Valida el contenido HTML ingresado"""
        html_content = self.html_editor.toPlainText()

        if not html_content.strip():
            QMessageBox.warning(
                self,
                "Campo Vacío",
                "Ingrese código HTML para validar."
            )
            return

        # Ejecutar validación completa
        result = validate_web_static_content(html_content)

        # Mostrar resultados
        self.validation_output.setVisible(True)
        output_html = "<div style='padding: 10px;'>"
        output_html += "<h3 style='color: #00d4ff; margin-top: 0;'>Resultados de Validación</h3>"

        # Sintaxis
        if result['syntax_valid']:
            output_html += "<p style='color: #4CAF50; margin: 5px 0;'>✓ <b>Sintaxis HTML:</b> Válida</p>"
        else:
            output_html += "<p style='color: #f44336; margin: 5px 0;'>✗ <b>Sintaxis HTML:</b> Errores encontrados</p>"
            output_html += "<ul style='margin: 5px 0; padding-left: 20px;'>"
            for error in result['syntax_errors']:
                output_html += f"<li style='color: #f44336;'>{error}</li>"
            output_html += "</ul>"

        # Tamaño
        if result['size_level'] == 'ok':
            output_html += f"<p style='color: #4CAF50; margin: 5px 0;'>✓ <b>Tamaño:</b> {result['size_message']}</p>"
        elif result['size_level'] == 'warning':
            output_html += f"<p style='color: #FFA726; margin: 5px 0;'>⚠ <b>Tamaño:</b> {result['size_message']}</p>"
        else:
            output_html += f"<p style='color: #f44336; margin: 5px 0;'>✗ <b>Tamaño:</b> {result['size_message']}</p>"

        # Seguridad
        if result['security_safe']:
            output_html += "<p style='color: #4CAF50; margin: 5px 0;'>✓ <b>Seguridad:</b> Sin patrones sospechosos</p>"
        else:
            output_html += "<p style='color: #FFA726; margin: 5px 0;'>⚠ <b>Seguridad:</b> Patrones sospechosos detectados</p>"
            output_html += "<ul style='margin: 5px 0; padding-left: 20px;'>"
            for warning in result['security_warnings']:
                output_html += f"<li style='color: #FFA726;'>{warning}</li>"
            output_html += "</ul>"

        output_html += "</div>"
        self.validation_output.setHtml(output_html)

        # Actualizar estado
        if result['can_save']:
            if result['is_valid']:
                self.validation_status.setText("✓ Estado: Válido - Listo para guardar")
                self.validation_status.setStyleSheet(
                    "padding: 8px; "
                    "background-color: #4CAF50; "
                    "color: #000000; "
                    "border-radius: 4px; "
                    "font-weight: bold;"
                )
            else:
                self.validation_status.setText("⚠ Estado: Advertencias - Puede guardarse")
                self.validation_status.setStyleSheet(
                    "padding: 8px; "
                    "background-color: #FFA726; "
                    "color: #000000; "
                    "border-radius: 4px; "
                    "font-weight: bold;"
                )
        else:
            self.validation_status.setText("✗ Estado: Errores - No se puede guardar")
            self.validation_status.setStyleSheet(
                "padding: 8px; "
                "background-color: #f44336; "
                "color: #ffffff; "
                "border-radius: 4px; "
                "font-weight: bold;"
            )

        logger.info(f"HTML validado: can_save={result['can_save']}, is_valid={result['is_valid']}")

    def _create_item(self):
        """Crea el item WEB_STATIC"""
        html_content = self.html_editor.toPlainText()

        if not html_content.strip():
            QMessageBox.warning(
                self,
                "Campo Vacío",
                "Ingrese código HTML para crear el item."
            )
            return

        # Validar antes de guardar
        result = validate_web_static_content(html_content)

        if not result['can_save']:
            error_msg = "El HTML contiene errores que impiden guardarlo:\n\n"
            error_msg += "\n".join(result['syntax_errors'])
            QMessageBox.critical(
                self,
                "Error de Validación",
                error_msg
            )
            return

        # Confirmar si hay warnings
        if not result['is_valid']:
            warnings_text = ""

            if result['size_level'] == 'warning':
                warnings_text += f"• {result['size_message']}\n"

            if not result['security_safe']:
                warnings_text += "• Patrones de seguridad sospechosos detectados:\n"
                for warning in result['security_warnings'][:3]:  # Mostrar solo 3
                    warnings_text += f"  - {warning}\n"

            reply = QMessageBox.question(
                self,
                "Advertencias Detectadas",
                f"Se detectaron las siguientes advertencias:\n\n{warnings_text}\n¿Desea continuar de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Crear item
        category_id = self.category_combo.currentData()
        label = self.label_input.text().strip()
        description = self.description_input.text().strip()

        # Obtener tags
        tags = []
        if self.tag_selector and hasattr(self.tag_selector, 'get_selected_tags'):
            # ProjectTagSelector
            selected_ids = self.tag_selector.get_selected_tags()
            for tag_id in selected_ids:
                tag = self.global_tag_manager.get_tag(tag_id)
                if tag:
                    tags.append(tag.name)
        elif hasattr(self, 'tag_selector'):
            # QLineEdit fallback
            tags_text = self.tag_selector.text().strip()
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []

        try:
            # Crear item en base de datos (tags se pasan directamente como parámetro)
            item_id = self.controller.config_manager.db.add_item(
                category_id=category_id,
                label=label,
                content=html_content,
                item_type='WEB_STATIC',
                description=description if description else None,
                tags=tags  # Tags ya parseados como lista
            )

            logger.info(f"Item WEB_STATIC creado: id={item_id}, label='{label}'")

            QMessageBox.information(
                self,
                "Éxito",
                f"Item '{label}' creado exitosamente como WEB_STATIC.\n\n"
                f"Tamaño: {result['size_message']}"
            )

            # Emitir señal y cerrar
            self.item_created.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Error al crear item WEB_STATIC: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al crear el item:\n\n{str(e)}"
            )
