"""
Save URL Dialog - Dialog para guardar la URL actual del navegador como item
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from views.widgets.project_tag_selector import ProjectTagSelector
from core.global_tag_manager import GlobalTagManager
from database.db_manager import DBManager

logger = logging.getLogger(__name__)


class SaveUrlDialog(QDialog):
    """
    Dialog para guardar URL actual del navegador como item.

    Permite seleccionar:
    - Categoría destino
    - Label del item (auto: título de página)
    - Descripción (opcional)
    - Tags (opcional)
    """

    def __init__(self, current_url: str, page_title: str, categories: list, db_path: str = None, parent=None):
        """
        Inicializa el dialog.

        Args:
            current_url: URL actual del navegador
            page_title: Título de la página actual
            categories: Lista de categorías disponibles
            db_path: Path a la base de datos para GlobalTagManager
            parent: Widget padre
        """
        super().__init__(parent)
        self.current_url = current_url
        self.page_title = page_title
        self.categories = categories
        self.db_path = db_path
        self.selected_category_id = None

        # Initialize GlobalTagManager
        self.global_tag_manager = None
        if self.db_path:
            try:
                db = DBManager(self.db_path)
                self.global_tag_manager = GlobalTagManager(db)
            except Exception as e:
                logger.error(f"Could not initialize GlobalTagManager: {e}")

        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz del dialog."""
        self.setWindowTitle("Guardar URL")
        self.setModal(True)
        self.setMinimumWidth(500)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === URL (solo lectura) ===
        url_label = QLabel("URL:")
        url_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(url_label)

        self.url_display = QLineEdit()
        self.url_display.setText(self.current_url)
        self.url_display.setReadOnly(True)
        self.url_display.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #888888;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.url_display)

        # === Categoría ===
        category_label = QLabel("Categoría: *")
        category_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 1px solid #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
        """)

        # Agregar categorías al combo
        for category in self.categories:
            display_text = f"{category.icon} {category.name}" if hasattr(category, 'icon') else category.name
            self.category_combo.addItem(display_text, category.id)

        layout.addWidget(self.category_combo)

        # === Label (auto-completado con título) ===
        label_label = QLabel("Nombre del Item: *")
        label_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(label_label)

        self.label_input = QLineEdit()
        # Auto-completar con título de página (primeros 50 chars)
        auto_label = self.page_title[:50] if self.page_title else "Nueva URL"
        self.label_input.setText(auto_label)
        self.label_input.setPlaceholderText("Ej: Documentación React")
        self.label_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
            }
        """)
        layout.addWidget(self.label_input)

        # === Descripción (opcional) ===
        desc_label = QLabel("Descripción: (opcional)")
        desc_label.setStyleSheet("font-weight: bold; color: #888888;")
        layout.addWidget(desc_label)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Agrega una descripción opcional...")
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                font-size: 10pt;
            }
            QTextEdit:focus {
                border: 1px solid #00d4ff;
            }
        """)
        layout.addWidget(self.description_input)

        # === Tags con ProjectTagSelector ===
        tags_label = QLabel("Tags:")
        tags_label.setStyleSheet("font-weight: bold; color: #888888;")
        layout.addWidget(tags_label)

        if self.global_tag_manager:
            self.tag_selector = ProjectTagSelector(self.global_tag_manager)
            self.tag_selector.setMinimumHeight(150)
            layout.addWidget(self.tag_selector)
        else:
            # Fallback if no manager available
            self.tag_selector = QLineEdit()
            self.tag_selector.setPlaceholderText("tag1, tag2, tag3 (separados por comas)")
            self.tag_selector.setStyleSheet("""
                QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    padding: 8px;
                    font-size: 10pt;
                }
                QLineEdit:focus {
                    border: 1px solid #00d4ff;
                }
            """)
            layout.addWidget(self.tag_selector)

        # === Botones ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 10px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar")
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #000000;
                border: none;
                border-radius: 3px;
                padding: 10px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b8d4;
            }
        """)
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        # Aplicar estilo general al dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
        """)

    def validate_and_accept(self):
        """Valida los campos antes de aceptar."""
        # Validar que haya categoría seleccionada
        if self.category_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Error", "Debes seleccionar una categoría")
            return

        # Validar que haya label
        if not self.label_input.text().strip():
            QMessageBox.warning(self, "Error", "Debes ingresar un nombre para el item")
            return

        self.accept()

    def get_data(self):
        """
        Obtiene los datos ingresados en el dialog.

        Returns:
            dict: Diccionario con los datos del item a crear
        """
        # Obtener category_id del combo
        category_id = self.category_combo.currentData()

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

        return {
            'category_id': category_id,
            'label': self.label_input.text().strip(),
            'content': self.current_url,
            'description': self.description_input.toPlainText().strip() or None,
            'tags': tags,
            'type': 'URL'
        }
