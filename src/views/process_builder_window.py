"""
Process Builder Window - Ventana maximizada para crear y editar procesos

Layout de 3 paneles:
- Panel izquierdo (25%): Filtros de items
- Panel central (35%): Items y listas disponibles
- Panel derecho (40%): Constructor del proceso
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTextEdit, QScrollArea,
                             QSplitter, QFrame, QComboBox, QSpinBox, QMessageBox,
                             QColorDialog, QDialog, QTabWidget, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QCursor, QColor
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.process import Process, ProcessStep
from models.category import Category
from views.widgets.process_step_widget import ProcessStepWidget
from views.widgets.item_widget import ItemButton
from views.widgets.search_bar import SearchBar

logger = logging.getLogger(__name__)


class ProcessBuilderWindow(QWidget):
    """Ventana para crear y editar procesos"""

    # Signals
    process_saved = pyqtSignal(int)  # process_id
    window_closed = pyqtSignal()

    def __init__(self, config_manager=None, process_controller=None,
                 process_id=None, list_controller=None, component_manager=None, parent=None):
        """
        Initialize ProcessBuilderWindow

        Args:
            config_manager: ConfigManager instance
            process_controller: ProcessController instance
            process_id: ID of process to edit (None for new process)
            list_controller: ListController instance (optional)
            component_manager: ComponentManager instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.process_controller = process_controller
        self.process_id = process_id
        self.editing_mode = process_id is not None
        self.list_controller = list_controller
        self.component_manager = component_manager

        # Current process being built/edited
        self.current_process = None

        # Available items for adding to process
        self.available_items = []
        self.filtered_items = []

        # Available lists (grouped items)
        self.available_lists = []
        self.filtered_lists = []

        # Available components
        self.available_components = []

        # Step widgets in constructor
        self.step_widgets = []

        # Edit mode state
        self.edit_mode_active = False
        self.process_being_edited = None  # ID of process being edited

        # Tags filter state
        self.tag_checkboxes = {}  # tag_name -> QCheckBox
        self.selected_tags = set()  # Selected tag names
        self.updating_tags_panel = False  # Flag to prevent recursion

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize UI"""
        # Window properties
        self.setWindowTitle("Crear Proceso" if not self.editing_mode else "Editar Proceso")
        self.setWindowFlags(Qt.WindowType.Window)

        # Calculate window size (maximized with margin for sidebar)
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            # Leave 70px margin on right for sidebar
            window_width = screen_geom.width() - 80  # 70px sidebar + 10px gap
            window_height = int(screen_geom.height() * 0.9)
            self.resize(window_width, window_height)
            # Position at left edge
            self.move(0, int(screen_geom.height() * 0.05))

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === HEADER ===
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)

        # === PROCESS INFO ===
        info_layout = self.create_process_info_section()
        main_layout.addLayout(info_layout)

        # === 4-PANEL LAYOUT ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel 1: Filters (20%)
        filter_panel = self.create_filter_panel()
        splitter.addWidget(filter_panel)

        # Panel 2: Available Items (30%)
        items_panel = self.create_items_panel()
        splitter.addWidget(items_panel)

        # Panel 3: Process Constructor (30%)
        constructor_panel = self.create_constructor_panel()
        splitter.addWidget(constructor_panel)

        # Panel 4: Saved Processes List (20%)
        processes_list_panel = self.create_processes_list_panel()
        splitter.addWidget(processes_list_panel)

        # Set initial sizes
        total_width = self.width()
        splitter.setSizes([
            int(total_width * 0.20),
            int(total_width * 0.30),
            int(total_width * 0.30),
            int(total_width * 0.20)
        ])

        main_layout.addWidget(splitter, stretch=1)

        # === FOOTER BUTTONS ===
        footer_layout = self.create_footer()
        main_layout.addLayout(footer_layout)

        # Apply global styles
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #007acc;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QScrollArea {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
        """)

    def create_header(self) -> QHBoxLayout:
        """Create header with title and close button"""
        layout = QHBoxLayout()

        # Title
        title = QLabel("Crear Proceso" if not self.editing_mode else "Editar Proceso")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18pt;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("✕ Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #e4475b;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return layout

    def create_process_info_section(self) -> QHBoxLayout:
        """Create process information section"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Process name
        name_label = QLabel("Nombre:")
        name_label.setFixedWidth(80)
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre del proceso...")
        layout.addWidget(self.name_input, stretch=2)

        # Description
        desc_label = QLabel("Descripcion:")
        desc_label.setFixedWidth(80)
        layout.addWidget(desc_label)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Descripcion opcional...")
        layout.addWidget(self.description_input, stretch=2)

        # Icon
        icon_label = QLabel("Icono:")
        icon_label.setFixedWidth(60)
        layout.addWidget(icon_label)

        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("Emoji")
        self.icon_input.setMaxLength(2)
        self.icon_input.setFixedWidth(60)
        layout.addWidget(self.icon_input)

        # Color picker
        self.color_button = QPushButton("Color")
        self.color_button.setFixedWidth(80)
        self.color_button.clicked.connect(self.pick_color)
        self.selected_color = None
        layout.addWidget(self.color_button)

        return layout

    def create_filter_panel(self) -> QWidget:
        """Create filter panel (left panel) with tabs"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # Tab widget
        tabs = QTabWidget()

        # ===== TAB 1: Filtros =====
        filters_tab = QWidget()
        filters_layout = QVBoxLayout(filters_tab)
        filters_layout.setContentsMargins(10, 10, 10, 10)
        filters_layout.setSpacing(10)

        # Category filter
        cat_label = QLabel("Categoria:")
        filters_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas las categorias", None)
        self.category_combo.currentIndexChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.category_combo)

        # Type filter
        type_label = QLabel("Tipo:")
        filters_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Todos los tipos", None)
        self.type_combo.addItem("CODE", "CODE")
        self.type_combo.addItem("URL", "URL")
        self.type_combo.addItem("PATH", "PATH")
        self.type_combo.addItem("TEXT", "TEXT")
        self.type_combo.currentIndexChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.type_combo)

        filters_layout.addStretch()

        # ===== TAB 2: Tags =====
        tags_tab = QWidget()
        tags_layout = QVBoxLayout(tags_tab)
        tags_layout.setContentsMargins(10, 10, 10, 10)
        tags_layout.setSpacing(10)

        # Tag count label
        self.tag_count_label = QLabel("(0 tags)")
        self.tag_count_label.setStyleSheet("color: #888888; font-size: 10pt;")
        tags_layout.addWidget(self.tag_count_label)

        # Scroll area for tags
        tags_scroll = QScrollArea()
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
        """)

        # Container for tag checkboxes
        self.tags_container = QWidget()
        self.tags_container_layout = QVBoxLayout(self.tags_container)
        self.tags_container_layout.setContentsMargins(0, 5, 0, 5)
        self.tags_container_layout.setSpacing(6)
        self.tags_container_layout.addStretch()

        tags_scroll.setWidget(self.tags_container)
        tags_layout.addWidget(tags_scroll, 1)

        # Action buttons for tags
        tag_buttons_layout = QVBoxLayout()
        tag_buttons_layout.setSpacing(6)

        # Select all button
        self.select_all_tags_btn = QPushButton("✓ Seleccionar Todos")
        self.select_all_tags_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #007acc;
            }
        """)
        self.select_all_tags_btn.clicked.connect(self.select_all_tags)
        tag_buttons_layout.addWidget(self.select_all_tags_btn)

        # Deselect all button
        self.deselect_all_tags_btn = QPushButton("✗ Deseleccionar Todos")
        self.deselect_all_tags_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #007acc;
            }
        """)
        self.deselect_all_tags_btn.clicked.connect(self.deselect_all_tags)
        tag_buttons_layout.addWidget(self.deselect_all_tags_btn)

        tags_layout.addLayout(tag_buttons_layout)

        # Add tabs
        tabs.addTab(filters_tab, "Filtros")
        tabs.addTab(tags_tab, "Tags")

        layout.addWidget(tabs)

        return panel

    def create_items_panel(self) -> QWidget:
        """Create available items panel (center panel)"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("Items Disponibles")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #007acc;")
        title_layout.addWidget(title)

        self.items_count_label = QLabel("(0)")
        self.items_count_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(self.items_count_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Search bar
        self.items_search = SearchBar()
        self.items_search.search_changed.connect(self.on_search_changed)
        layout.addWidget(self.items_search)

        # Scroll area for items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container for items
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(2)
        self.items_layout.addStretch()

        scroll.setWidget(self.items_container)
        layout.addWidget(scroll)

        # === Components section ===
        if self.component_manager:
            # Separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("background-color: #3d3d3d; max-height: 2px;")
            layout.addWidget(separator)

            # Components title with manage button
            components_title_layout = QHBoxLayout()
            components_title = QLabel("Componentes Visuales")
            components_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #ff6b6b;")
            components_title_layout.addWidget(components_title)
            components_title_layout.addStretch()

            manage_components_btn = QPushButton("⚙️")
            manage_components_btn.setFixedSize(24, 24)
            manage_components_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            manage_components_btn.setToolTip("Gestionar Componentes")
            manage_components_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #007acc;
                    border-color: #007acc;
                }
            """)
            manage_components_btn.clicked.connect(self.on_manage_components)
            components_title_layout.addWidget(manage_components_btn)

            layout.addLayout(components_title_layout)

            # Components container
            self.components_container = QWidget()
            self.components_layout = QHBoxLayout(self.components_container)
            self.components_layout.setContentsMargins(0, 5, 0, 5)
            self.components_layout.setSpacing(5)
            self.components_layout.addStretch()

            layout.addWidget(self.components_container)

        return panel

    def create_constructor_panel(self) -> QWidget:
        """Create process constructor panel (right panel)"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("Constructor del Proceso")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #00ff88;")
        title_layout.addWidget(title)

        self.steps_count_label = QLabel("(0 steps)")
        self.steps_count_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(self.steps_count_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Info label
        info_label = QLabel("Haz doble clic en un item de la izquierda para agregarlo")
        info_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 9pt;
                font-style: italic;
                padding: 5px;
            }
        """)
        layout.addWidget(info_label)

        # Scroll area for steps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Container for steps
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(5)
        self.steps_layout.addStretch()

        scroll.setWidget(self.steps_container)
        layout.addWidget(scroll)

        # Configuration section
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)

        config_title = QLabel("Configuracion de Ejecucion")
        config_title.setStyleSheet("font-weight: bold; color: #007acc;")
        config_layout.addWidget(config_title)

        # Delay between steps
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay entre steps (ms):"))
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 10000)
        self.delay_spinbox.setValue(500)
        self.delay_spinbox.setSingleStep(100)
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()
        config_layout.addLayout(delay_layout)

        layout.addWidget(config_frame)

        return panel

    def create_processes_list_panel(self) -> QWidget:
        """Create saved processes list panel (fourth column)"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("Procesos Guardados")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ff6b00;")
        title_layout.addWidget(title)

        self.processes_count_label = QLabel("(0)")
        self.processes_count_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(self.processes_count_label)
        title_layout.addStretch()

        # Edit mode button
        self.edit_mode_btn = QPushButton("✏️ Modo Edición")
        self.edit_mode_btn.setFixedSize(120, 30)
        self.edit_mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 4px;
                font-size: 9pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                border-color: #ff6b00;
            }
            QPushButton:checked {
                background-color: #ff6b00;
                border-color: #ff6b00;
                color: #000000;
            }
            QPushButton:checked:hover {
                background-color: #ff8c00;
                border-color: #ff8c00;
            }
        """)
        self.edit_mode_btn.clicked.connect(self.on_edit_mode_toggled)
        title_layout.addWidget(self.edit_mode_btn)

        layout.addLayout(title_layout)

        # Info label
        self.processes_info_label = QLabel("Click en checkbox para activar/desactivar")
        self.processes_info_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 9pt;
                font-style: italic;
                padding: 5px;
            }
        """)
        layout.addWidget(self.processes_info_label)

        # Scroll area for processes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #ff6b00;
            }
        """)

        # Container for process items
        self.processes_list_container = QWidget()
        self.processes_list_layout = QVBoxLayout(self.processes_list_container)
        self.processes_list_layout.setContentsMargins(0, 0, 0, 0)
        self.processes_list_layout.setSpacing(5)
        self.processes_list_layout.addStretch()

        scroll.setWidget(self.processes_list_container)
        layout.addWidget(scroll)

        return panel

    def create_footer(self) -> QHBoxLayout:
        """Create footer with action buttons"""
        layout = QHBoxLayout()

        layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        cancel_btn.clicked.connect(self.close)
        layout.addWidget(cancel_btn)

        # Save/Update button
        self.save_btn = QPushButton("💾 Guardar Proceso")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ff88;
                color: #000000;
                font-size: 11pt;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #00cc70;
            }
        """)
        self.save_btn.clicked.connect(self.on_save_clicked)
        layout.addWidget(self.save_btn)

        return layout

    # ==================== DATA LOADING ====================

    def load_data(self):
        """Load data (items, categories, process if editing)"""
        if not self.config_manager:
            logger.warning("No config_manager available")
            return

        # Load categories for filter
        categories = self.config_manager.get_categories()
        for category in categories:
            self.category_combo.addItem(category.name, category.id)

        # Load all items
        self.load_all_items()

        # Load available components
        if self.component_manager:
            self.load_available_components()

        # Load saved processes list
        self.load_saved_processes()

        # If editing, load process data
        if self.editing_mode and self.process_id:
            self.load_process_for_editing()

    def load_all_items(self):
        """Load all items and lists from all categories"""
        if not self.config_manager:
            return

        self.available_items = []
        self.available_lists = []

        categories = self.config_manager.get_categories()

        for category in categories:
            # Separate regular items from list items
            for item in category.items:
                if not item.is_list_item():
                    # Regular item - add category_id dynamically
                    item.category_id = category.id
                    self.available_items.append(item)

            # Get lists for this category
            if self.list_controller:
                try:
                    lists = self.list_controller.get_lists(category.id)
                    # Add category info to each list
                    for list_data in lists:
                        list_data['category_id'] = category.id
                        list_data['category_name'] = category.name
                    self.available_lists.extend(lists)
                except Exception as e:
                    logger.error(f"Error loading lists for category {category.id}: {e}")

        logger.info(f"Loaded {len(self.available_items)} items and {len(self.available_lists)} lists")
        self.filtered_items = self.available_items.copy()
        self.filtered_lists = self.available_lists.copy()

        # Load tags
        self.load_available_tags()

        self.display_items_and_lists()

    def load_process_for_editing(self):
        """Load existing process data for editing"""
        if not self.process_controller:
            logger.error("No process_controller available")
            return

        try:
            # Get process from process_manager
            process_manager = self.process_controller.process_manager
            process = process_manager.get_process(self.process_id)

            if not process:
                logger.error(f"Process {self.process_id} not found")
                QMessageBox.warning(self, "Error", "Proceso no encontrado")
                self.close()
                return

            self.current_process = process

            # Fill form fields
            self.name_input.setText(process.name)
            self.description_input.setText(process.description or "")
            self.icon_input.setText(process.icon or "")
            self.delay_spinbox.setValue(process.delay_between_steps)

            if process.color:
                self.selected_color = process.color
                self.update_color_button()

            # Load steps
            for step in process.steps:
                self.add_step_to_constructor(step)

            logger.info(f"Loaded process for editing: {process.name} with {len(process.steps)} steps")

        except Exception as e:
            logger.error(f"Error loading process for editing: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar proceso: {str(e)}")

    def load_saved_processes(self):
        """Load all saved processes into the fourth column"""
        if not self.process_controller:
            logger.warning("No process_controller available")
            return

        try:
            # Get ALL processes (including inactive and archived)
            processes = self.process_controller.process_manager.get_all_processes(
                include_archived=True,
                include_inactive=True
            )

            # Clear existing widgets
            while self.processes_list_layout.count() > 1:  # Keep stretch
                item = self.processes_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add process items
            for process in processes:
                process_item = self.create_process_list_item(process)
                self.processes_list_layout.insertWidget(
                    self.processes_list_layout.count() - 1,  # Before stretch
                    process_item
                )

            # Update count
            self.processes_count_label.setText(f"({len(processes)})")

            logger.info(f"Loaded {len(processes)} saved processes")

        except Exception as e:
            logger.error(f"Error loading saved processes: {e}")

    def create_process_list_item(self, process) -> QWidget:
        """Create a widget for a single process in the list"""
        from PyQt6.QtWidgets import QCheckBox

        container = QWidget()
        container.setProperty("process_id", process.id)  # Store process ID
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(8)

        # Checkbox for active/inactive
        checkbox = QCheckBox("✓" if process.is_active else "")
        checkbox.setChecked(process.is_active)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 3px;
                color: #000000;
                font-size: 14pt;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #555555;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #00ff88;
                background-color: #353535;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff88;
                border-color: #00ff88;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00dd77;
                border-color: #00dd77;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border-color: #666666;
            }
        """)

        # Update checkbox text on state change
        def update_checkbox_text(state):
            if state == 2:  # Checked
                checkbox.setText("✓")
            else:  # Unchecked
                checkbox.setText("")
            self.on_process_toggle(process.id, state)

        checkbox.stateChanged.connect(update_checkbox_text)
        container_layout.addWidget(checkbox)

        # Process name label
        name_label = QLabel(process.name)
        name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 10pt;
            }
        """)
        name_label.setWordWrap(True)
        container_layout.addWidget(name_label, stretch=1)

        # Styling
        container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QWidget:hover {
                background-color: #353535;
                border-color: #ff6b00;
            }
        """)

        # Make clickable in edit mode
        container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        container.mousePressEvent = lambda event: self.on_process_item_clicked(process.id)

        return container

    def on_process_toggle(self, process_id: int, state: int):
        """Handle process active/inactive toggle"""
        is_active = (state == 2)  # Qt.CheckState.Checked = 2

        try:
            # Get process
            process = self.process_controller.get_process(process_id)
            if not process:
                logger.error(f"Process {process_id} not found")
                return

            # Update is_active
            process.is_active = is_active

            # Save to database
            success, msg = self.process_controller.save_process(process)

            if success:
                logger.info(f"Process {process_id} {'activated' if is_active else 'deactivated'}")
            else:
                logger.error(f"Failed to toggle process: {msg}")
                QMessageBox.warning(self, "Error", f"No se pudo actualizar el proceso: {msg}")

        except Exception as e:
            logger.error(f"Error toggling process: {e}")
            QMessageBox.critical(self, "Error", f"Error al actualizar proceso: {str(e)}")

    # ==================== ITEM DISPLAY ====================

    def display_items_and_lists(self):
        """Display filtered items and lists in separate sections"""
        # Clear existing items
        while self.items_layout.count() > 1:  # Keep stretch
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # === SECCIÓN DE ITEMS ===
        if self.filtered_items:
            # Section header
            items_header = QLabel(f"━━━ Items ({len(self.filtered_items)}) ━━━")
            items_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            items_header.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 8px;
                    background-color: transparent;
                }
            """)
            self.items_layout.insertWidget(self.items_layout.count() - 1, items_header)

            # Add filtered items
            for item in self.filtered_items:
                item_btn = ItemButton(item)
                item_btn.setMaximumHeight(60)

                # Double-click to add to process
                item_btn.mouseDoubleClickEvent = lambda event, i=item: self.on_item_double_clicked(i)

                self.items_layout.insertWidget(self.items_layout.count() - 1, item_btn)

        # === SECCIÓN DE LISTAS ===
        if self.filtered_lists:
            # Spacer entre secciones
            if self.filtered_items:
                spacer_label = QLabel("")
                spacer_label.setFixedHeight(10)
                spacer_label.setStyleSheet("background-color: transparent;")
                self.items_layout.insertWidget(self.items_layout.count() - 1, spacer_label)

            # Section header
            lists_header = QLabel(f"━━━ Listas ({len(self.filtered_lists)}) ━━━")
            lists_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lists_header.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 8px;
                    background-color: transparent;
                }
            """)
            self.items_layout.insertWidget(self.items_layout.count() - 1, lists_header)

            # Add filtered lists
            for list_data in self.filtered_lists:
                list_widget = self.create_simple_list_widget(list_data)
                self.items_layout.insertWidget(self.items_layout.count() - 1, list_widget)

        # Update total count
        total_count = len(self.filtered_items) + len(self.filtered_lists)
        self.items_count_label.setText(f"({total_count})")

    def on_search_changed(self, query: str):
        """Handle search query change"""
        self.apply_filters()

    def on_filter_changed(self):
        """Handle filter change"""
        self.apply_filters()

    def apply_filters(self):
        """Apply all active filters to items and lists"""
        filtered_items = self.available_items.copy()
        filtered_lists = self.available_lists.copy()

        # Get filter values
        selected_category_id = self.category_combo.currentData()
        selected_type = self.type_combo.currentData()
        search_query = self.items_search.search_input.text().strip().lower()

        # Apply category filter to items
        if selected_category_id is not None:
            filtered_items = [item for item in filtered_items if item.category_id == selected_category_id]
            filtered_lists = [lst for lst in filtered_lists if lst.get('category_id') == selected_category_id]

        # Apply type filter to items (lists don't have type)
        if selected_type is not None:
            # item.type is an ItemType enum, need to compare with .value
            filtered_items = [item for item in filtered_items
                           if item.type.value.upper() == selected_type.upper()]

        # Apply search filter
        if search_query:
            # Filter items by label or content
            filtered_items = [item for item in filtered_items
                           if search_query in item.label.lower() or
                              search_query in (item.content or "").lower()]

            # Filter lists by list_group name
            filtered_lists = [lst for lst in filtered_lists
                           if search_query in lst.get('list_group', '').lower()]

        # Update tags panel with tags from currently filtered items
        # This happens BEFORE applying tag filter
        self.update_tags_panel(filtered_items)

        # Apply tags filter
        if self.selected_tags:
            # Filter items that have at least one of the selected tags
            filtered_items = [
                item for item in filtered_items
                if hasattr(item, 'tags') and item.tags and
                any(tag in self.selected_tags for tag in item.tags)
            ]

        self.filtered_items = filtered_items
        self.filtered_lists = filtered_lists
        self.display_items_and_lists()

    def create_simple_list_widget(self, list_data: dict):
        """Create a simple collapsible widget for a list"""
        from PyQt6.QtWidgets import QFrame, QPushButton
        from PyQt6.QtGui import QFont

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: #4a9eff;
                background-color: #303030;
            }
        """)
        container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel("📝")
        icon_label.setFixedWidth(20)
        icon_font = QFont()
        icon_font.setPointSize(12)
        icon_label.setFont(icon_font)
        layout.addWidget(icon_label)

        # List name
        name_label = QLabel(list_data.get('list_group', 'Lista'))
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(10)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(name_label, stretch=1)

        # Item count
        count_label = QLabel(f"{list_data.get('item_count', 0)} pasos")
        count_label.setStyleSheet("color: #888888; font-size: 9pt;")
        layout.addWidget(count_label)

        # Double-click to add all items to process
        container.mouseDoubleClickEvent = lambda event: self.on_list_double_clicked(list_data)

        return container

    def on_item_double_clicked(self, item):
        """Handle double-click on item to add to process"""
        logger.info(f"Adding item to process: {item.label}")

        # Create ProcessStep from item
        step = ProcessStep(
            item_id=item.id,
            step_order=len(self.step_widgets) + 1,
            item_label=item.label,
            item_content=item.content,
            item_type=item.type,
            item_icon=item.icon,
            item_is_sensitive=item.is_sensitive,
            is_component=getattr(item, 'is_component', False),
            name_component=getattr(item, 'name_component', None),
            component_config=getattr(item, 'component_config', {}),
            is_enabled=True
        )

        self.add_step_to_constructor(step)

    def on_list_double_clicked(self, list_data: dict):
        """Handle double-click on list to add all items to process"""
        list_group = list_data.get('list_group')
        category_id = list_data.get('category_id')

        logger.info(f"Adding list to process: {list_group}")

        if not self.list_controller:
            logger.error("ListController not available")
            return

        try:
            # Get all items in the list
            list_items = self.list_controller.get_list_items(category_id, list_group)

            if not list_items:
                logger.warning(f"No items found in list {list_group}")
                return

            # Add each item as a step
            for item_data in list_items:
                step = ProcessStep(
                    item_id=item_data.get('id'),
                    step_order=len(self.step_widgets) + 1,
                    item_label=item_data.get('label', 'Sin nombre'),
                    item_content=item_data.get('content', ''),
                    item_type=item_data.get('type', 'TEXT'),
                    item_icon=item_data.get('icon', ''),
                    item_is_sensitive=item_data.get('is_sensitive', False),
                    is_enabled=True
                )
                self.add_step_to_constructor(step)

            logger.info(f"Added {len(list_items)} items from list {list_group} to process")

        except Exception as e:
            logger.error(f"Error adding list to process: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error al agregar lista: {str(e)}")

    # ==================== STEP MANAGEMENT ====================

    def add_step_to_constructor(self, step: ProcessStep):
        """Add a step to the constructor panel"""
        is_first = len(self.step_widgets) == 0
        is_last = True  # Always last when adding

        # Create widget
        step_widget = ProcessStepWidget(step, is_first, is_last)

        # Connect signals
        step_widget.step_edited.connect(self.on_step_edit_requested)
        step_widget.step_deleted.connect(self.on_step_delete_requested)
        step_widget.step_moved_up.connect(self.on_step_move_up)
        step_widget.step_moved_down.connect(self.on_step_move_down)

        # Add to layout
        self.steps_layout.insertWidget(len(self.step_widgets), step_widget)
        self.step_widgets.append(step_widget)

        # Update all step widgets
        self.update_step_widgets()

        logger.debug(f"Step added: {step.get_display_label()}")

    def update_step_widgets(self):
        """Update order and button states for all step widgets"""
        for i, widget in enumerate(self.step_widgets):
            is_first = (i == 0)
            is_last = (i == len(self.step_widgets) - 1)
            widget.update_order(i + 1, is_first, is_last)

        # Update count
        self.steps_count_label.setText(f"({len(self.step_widgets)} steps)")

    def on_step_edit_requested(self, step: ProcessStep):
        """Handle step edit request"""
        logger.info(f"Edit requested for step: {step.get_display_label()}")

        try:
            # Import dialog
            from views.dialogs.process_step_config_dialog import ProcessStepConfigDialog

            # Create and show dialog
            dialog = ProcessStepConfigDialog(step, parent=self)
            dialog.config_saved.connect(lambda s: self.on_step_config_saved(s))

            # Show dialog (modal)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                logger.info(f"Step configuration updated: {step.get_display_label()}")

        except Exception as e:
            logger.error(f"Error opening step config dialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir configuracion: {str(e)}")

    def on_step_delete_requested(self, step: ProcessStep):
        """Handle step delete request"""
        reply = QMessageBox.question(
            self,
            "Eliminar Step",
            f"Eliminar step '{step.get_display_label()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Find and remove widget
            for i, widget in enumerate(self.step_widgets):
                if widget.get_step() == step:
                    self.steps_layout.removeWidget(widget)
                    widget.deleteLater()
                    self.step_widgets.pop(i)
                    break

            self.update_step_widgets()
            logger.info(f"Step deleted: {step.get_display_label()}")

    def on_step_config_saved(self, step: ProcessStep):
        """Handle step configuration saved - update widget display"""
        try:
            # Find the widget for this step and update it
            for widget in self.step_widgets:
                if widget.get_step() == step:
                    widget.update_step_data(step)
                    logger.info(f"Widget updated for step: {step.get_display_label()}")
                    break

        except Exception as e:
            logger.error(f"Error updating step widget: {e}", exc_info=True)

    def on_step_move_up(self, step: ProcessStep):
        """Move step up in order"""
        for i, widget in enumerate(self.step_widgets):
            if widget.get_step() == step and i > 0:
                # Swap with previous
                self.step_widgets[i], self.step_widgets[i-1] = self.step_widgets[i-1], self.step_widgets[i]

                # Re-add to layout in new order
                self.rebuild_steps_layout()
                self.update_step_widgets()
                break

    def on_step_move_down(self, step: ProcessStep):
        """Move step down in order"""
        for i, widget in enumerate(self.step_widgets):
            if widget.get_step() == step and i < len(self.step_widgets) - 1:
                # Swap with next
                self.step_widgets[i], self.step_widgets[i+1] = self.step_widgets[i+1], self.step_widgets[i]

                # Re-add to layout in new order
                self.rebuild_steps_layout()
                self.update_step_widgets()
                break

    def rebuild_steps_layout(self):
        """Rebuild steps layout after reordering"""
        # Remove all widgets from layout
        while self.steps_layout.count() > 1:
            item = self.steps_layout.takeAt(0)

        # Re-add in new order
        for widget in self.step_widgets:
            self.steps_layout.insertWidget(self.steps_layout.count() - 1, widget)

    # ==================== COLOR PICKER ====================

    def pick_color(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_button()

    def update_color_button(self):
        """Update color button appearance"""
        if self.selected_color:
            self.color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.selected_color};
                    color: white;
                    border: 2px solid #ffffff;
                }}
            """)
        else:
            # Reset to default style
            self.color_button.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
            """)

    # ==================== SAVE ====================

    def on_save_clicked(self):
        """Handle save button click"""
        # Validate
        if not self.validate_process():
            return

        # Build Process object
        process = self.build_process()

        if not process:
            QMessageBox.warning(self, "Error", "Error al construir proceso")
            return

        # Save via controller
        if not self.process_controller:
            QMessageBox.critical(self, "Error", "ProcessController no disponible")
            return

        try:
            # Check if we're in edit mode
            is_updating = self.process_being_edited is not None

            if is_updating:
                # Update existing process (from edit mode)
                success, message = self.process_controller.save_process(process)
            elif self.editing_mode:
                # Update existing process (original editing mode)
                success, message = self.process_controller.save_process(process)
            else:
                # Create new process
                success, message, process_id = self.process_controller.create_process(process)
                if success:
                    self.process_id = process_id

            if success:
                action = "actualizado" if (is_updating or self.editing_mode) else "creado"
                QMessageBox.information(self, "Éxito", f"Proceso {action} exitosamente")

                # Emit signal with correct process ID
                emit_id = self.process_id if self.process_id else self.process_being_edited
                self.process_saved.emit(emit_id)

                # If in edit mode, clear it and reload process list
                if is_updating:
                    self.clear_edit_mode()
                    self.edit_mode_btn.setChecked(False)
                    self.load_saved_processes()
                else:
                    self.close()
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            logger.error(f"Error saving process: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")

    def validate_process(self) -> bool:
        """Validate process data"""
        # Check name
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validacion", "El nombre del proceso es requerido")
            self.name_input.setFocus()
            return False

        # Check steps
        if len(self.step_widgets) == 0:
            QMessageBox.warning(self, "Validacion",
                               "El proceso debe tener al menos 1 step")
            return False

        return True

    def build_process(self) -> Process:
        """Build Process object from form data"""
        try:
            # Determine process ID
            process_id = None
            if self.process_being_edited:
                process_id = self.process_being_edited
            elif self.editing_mode:
                process_id = self.process_id

            # Create Process
            process = Process(
                id=process_id,
                name=self.name_input.text().strip(),
                description=self.description_input.text().strip() or None,
                icon=self.icon_input.text().strip() or "⚙️",
                color=self.selected_color,
                execution_mode="sequential",
                delay_between_steps=self.delay_spinbox.value()
            )

            # Add steps
            for widget in self.step_widgets:
                step = widget.get_step()
                process.add_step(step)

            return process

        except Exception as e:
            logger.error(f"Error building process: {e}", exc_info=True)
            return None

    # ==================== CLOSE ====================

    def closeEvent(self, event):
        """Handle window close"""
        # Check if there are unsaved changes
        if len(self.step_widgets) > 0:
            reply = QMessageBox.question(
                self,
                "Cerrar",
                "Hay cambios sin guardar. Cerrar de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self.window_closed.emit()
        event.accept()

    # ==================== TAGS FILTER METHODS ====================

    def load_available_tags(self):
        """Load all available tags from ALL items and create checkboxes (initial load)"""
        self.update_tags_panel(self.available_items)

    def update_tags_panel(self, items_to_analyze):
        """Update tags panel based on provided items (dynamic update)"""
        # Set flag to prevent recursion
        self.updating_tags_panel = True

        # Store current selections before clearing
        previously_selected = self.selected_tags.copy()

        # Clear existing checkboxes
        while self.tags_container_layout.count() > 1:  # Keep stretch
            item = self.tags_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Collect all unique tags from provided items
        all_tags = set()
        for item in items_to_analyze:
            if hasattr(item, 'tags') and item.tags:
                all_tags.update(item.tags)

        # Sort tags alphabetically
        sorted_tags = sorted(all_tags)

        # Recreate tag_checkboxes dict
        self.tag_checkboxes.clear()

        # Create checkbox for each tag
        for tag in sorted_tags:
            checkbox = QCheckBox(f"🏷️ {tag}")
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    font-size: 10pt;
                    padding: 4px;
                    spacing: 6px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #555555;
                    border-radius: 3px;
                    background-color: #2d2d2d;
                }
                QCheckBox::indicator:hover {
                    border-color: #007acc;
                    background-color: #353535;
                }
                QCheckBox::indicator:checked {
                    background-color: #007acc;
                    border-color: #007acc;
                    image: url(none);
                }
                QCheckBox:hover {
                    background-color: #2a2a2a;
                    border-radius: 4px;
                }
            """)

            # Restore previous selection if this tag was selected AND tag still exists
            if tag in previously_selected:
                checkbox.setChecked(True)

            # Connect signal
            checkbox.stateChanged.connect(self.on_tag_selection_changed)

            self.tags_container_layout.insertWidget(
                self.tags_container_layout.count() - 1,  # Before stretch
                checkbox
            )
            self.tag_checkboxes[tag] = checkbox

        # Update count label
        self.tag_count_label.setText(f"({len(sorted_tags)} tags)")

        # Update selected_tags to only include tags that still exist
        self.selected_tags = previously_selected.intersection(all_tags)

        # Clear flag
        self.updating_tags_panel = False

        logger.debug(f"Updated tags panel with {len(sorted_tags)} tags from {len(items_to_analyze)} items")

    def on_tag_selection_changed(self, state):
        """Handle tag checkbox state change"""
        # Ignore if we're currently updating the tags panel (prevents recursion)
        if self.updating_tags_panel:
            return

        # Update selected tags set
        self.selected_tags.clear()
        for tag, checkbox in self.tag_checkboxes.items():
            if checkbox.isChecked():
                self.selected_tags.add(tag)

        # Apply filters
        self.apply_filters()

    def select_all_tags(self):
        """Select all tag checkboxes"""
        for checkbox in self.tag_checkboxes.values():
            checkbox.setChecked(True)

    def deselect_all_tags(self):
        """Deselect all tag checkboxes"""
        for checkbox in self.tag_checkboxes.values():
            checkbox.setChecked(False)

    # ==================== Component Methods ====================

    def load_available_components(self):
        """Load available component types and create buttons"""
        if not self.component_manager:
            return

        try:
            # Clear existing component buttons
            while self.components_layout.count() > 1:  # Keep the stretch
                item = self.components_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Get all active component types
            component_types = self.component_manager.get_all_component_types(active_only=True)
            self.available_components = component_types

            # Create button for each component type
            for comp_type in component_types:
                button = self.create_component_button(comp_type)
                self.components_layout.insertWidget(self.components_layout.count() - 1, button)

            logger.info(f"Loaded {len(component_types)} component types")

        except Exception as e:
            logger.error(f"Error loading components: {e}")

    def create_component_button(self, component_type):
        """Create a button for a component type"""
        icon = self.component_manager.get_component_icon(component_type.name)

        button = QPushButton(f"{icon}\n{component_type.name}")
        button.setFixedSize(80, 60)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setToolTip(f"{component_type.description}\n\nClick para insertar")
        button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                border-color: #ff6b6b;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #e4475b;
                border-color: #e4475b;
            }
        """)

        # Connect to insertion handler
        button.clicked.connect(lambda: self.on_component_button_clicked(component_type))

        return button

    def on_component_button_clicked(self, component_type):
        """Handle component button click - insert component into process"""
        try:
            # Create component item using ComponentManager
            component_item = self.component_manager.create_component_item(
                component_name=component_type.name,
                label=f"{component_type.description}",
                content=""  # Components don't need content
            )

            if not component_item:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo crear el componente '{component_type.name}'"
                )
                return

            # Save component item to database first (needed for process_steps foreign key)
            component_item_id = self.config_manager.db.add_item(
                category_id=self.component_manager.get_components_category_id(),
                label=component_item.label,
                content=component_item.content,
                item_type=component_item.type.value.upper(),
                is_component=True,
                name_component=component_item.name_component,
                component_config=component_item.component_config
            )

            # Update the item ID
            component_item.id = component_item_id

            # Add component to process
            self.on_item_double_clicked(component_item)

            logger.info(f"Added component '{component_type.name}' to process (item_id: {component_item_id})")

        except Exception as e:
            logger.error(f"Error adding component: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al agregar componente:\n{e}"
            )

    def on_manage_components(self):
        """Open component manager dialog"""
        try:
            from views.dialogs.component_manager_dialog import ComponentManagerDialog

            dialog = ComponentManagerDialog(
                component_manager=self.component_manager,
                parent=self
            )
            dialog.component_types_changed.connect(self.on_components_changed)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error opening component manager: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir gestor de componentes:\n{e}"
            )

    def on_components_changed(self):
        """Handle changes in component types"""
        # Reload component buttons
        self.load_available_components()

    # ==================== EDIT MODE ====================

    def on_edit_mode_toggled(self, checked: bool):
        """Handle edit mode button toggle"""
        self.edit_mode_active = checked

        if checked:
            # Entering edit mode
            self.processes_info_label.setText("🔄 Haz click en un proceso para editarlo")
            self.processes_info_label.setStyleSheet("""
                QLabel {
                    color: #ff6b00;
                    font-size: 9pt;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
            logger.info("Edit mode activated")
        else:
            # Exiting edit mode
            self.clear_edit_mode()
            self.processes_info_label.setText("Click en checkbox para activar/desactivar")
            self.processes_info_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 9pt;
                    font-style: italic;
                    padding: 5px;
                }
            """)
            logger.info("Edit mode deactivated")

    def on_process_item_clicked(self, process_id: int):
        """Handle click on process item"""
        # Only respond if edit mode is active
        if not self.edit_mode_active:
            return

        logger.info(f"Process item clicked in edit mode: {process_id}")
        self.load_process_for_edit_mode(process_id)

    def load_process_for_edit_mode(self, process_id: int):
        """Load a process into the constructor for editing"""
        if not self.process_controller:
            logger.error("No process_controller available")
            return

        try:
            # Get process from process_manager
            process_manager = self.process_controller.process_manager
            process = process_manager.get_process(process_id)

            if not process:
                logger.error(f"Process {process_id} not found")
                QMessageBox.warning(self, "Error", "Proceso no encontrado")
                return

            # Clear current constructor
            self.clear_constructor()

            # Set as being edited
            self.process_being_edited = process_id

            # Fill form fields
            self.name_input.setText(process.name)
            self.description_input.setText(process.description or "")
            self.icon_input.setText(process.icon or "")
            self.delay_spinbox.setValue(process.delay_between_steps)

            if process.color:
                self.selected_color = process.color
                self.update_color_button()

            # Load steps into constructor
            for step in process.steps:
                self.add_step_to_constructor(step)

            # Update button text
            self.save_btn.setText("🔄 Actualizar Proceso")
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b00;
                    color: #000000;
                    font-size: 11pt;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #ff8c00;
                }
            """)

            # Highlight the selected process
            self.highlight_selected_process(process_id)

            logger.info(f"Loaded process '{process.name}' for editing with {len(process.steps)} steps")

        except Exception as e:
            logger.error(f"Error loading process for edit mode: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar proceso: {str(e)}")

    def clear_edit_mode(self):
        """Clear edit mode state"""
        self.process_being_edited = None
        self.clear_constructor()
        self.clear_form()
        self.remove_process_highlights()

        # Reset button
        self.save_btn.setText("💾 Guardar Proceso")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ff88;
                color: #000000;
                font-size: 11pt;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #00cc70;
            }
        """)

    def clear_constructor(self):
        """Clear all steps from constructor"""
        # Remove all step widgets
        while self.step_widgets:
            widget = self.step_widgets.pop()
            self.steps_layout.removeWidget(widget)
            widget.deleteLater()

        self.update_step_widgets()
        logger.debug("Constructor cleared")

    def clear_form(self):
        """Clear form fields"""
        self.name_input.clear()
        self.description_input.clear()
        self.icon_input.clear()
        self.delay_spinbox.setValue(500)
        self.selected_color = None
        self.update_color_button()

    def highlight_selected_process(self, process_id: int):
        """Highlight the selected process in the list"""
        # Remove previous highlights
        self.remove_process_highlights()

        # Find and highlight the selected process
        for i in range(self.processes_list_layout.count() - 1):  # -1 for stretch
            item = self.processes_list_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.property("process_id") == process_id:
                    widget.setStyleSheet("""
                        QWidget {
                            background-color: #ff6b00;
                            border: 2px solid #ff8c00;
                            border-radius: 4px;
                        }
                    """)
                    break

    def remove_process_highlights(self):
        """Remove highlights from all processes"""
        for i in range(self.processes_list_layout.count() - 1):  # -1 for stretch
            item = self.processes_list_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget.setStyleSheet("""
                    QWidget {
                        background-color: #2d2d2d;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                    }
                    QWidget:hover {
                        background-color: #353535;
                        border-color: #ff6b00;
                    }
                """)

