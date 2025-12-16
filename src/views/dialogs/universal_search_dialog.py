"""
Universal Search Dialog - Ventana de búsqueda universal
Permite buscar items y tags en toda la aplicación mostrando sus relaciones
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QWidget, QSplitter, QFrame, QScrollArea,
    QButtonGroup, QRadioButton, QMenu, QMessageBox, QFileDialog,
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QCursor, QColor, QFont, QAction
import logging
import csv
import json
import re
from datetime import datetime

from src.core.universal_search_engine import UniversalSearchEngine, SearchResultType

logger = logging.getLogger(__name__)


class UniversalSearchDialog(QDialog):
    """Ventana de búsqueda universal con filtros y resultados"""

    # Señales
    item_selected = pyqtSignal(int)  # item_id
    item_copied = pyqtSignal(int)  # item_id
    edit_item_requested = pyqtSignal(int)  # item_id
    delete_item_requested = pyqtSignal(int)  # item_id
    toggle_favorite_requested = pyqtSignal(int)  # item_id
    navigate_to_category_requested = pyqtSignal(int)  # category_id
    navigate_to_project_requested = pyqtSignal(int)  # project_id
    navigate_to_area_requested = pyqtSignal(int)  # area_id

    def __init__(self, db_manager, parent=None):
        """
        Args:
            db_manager: Instancia de DBManager
            parent: Widget padre
        """
        super().__init__(parent)

        self.db = db_manager
        self.search_engine = UniversalSearchEngine(db_manager)
        self.current_results = []
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        # Paginación
        self.current_page = 1
        self.page_size = 100
        self.total_items = 0

        # Optimización de filtros
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filters_debounced)
        self.last_entity_filters = None
        self.last_tag_filters = None

        # Historial de búsquedas
        self.search_history = []
        self.max_history = 20  # Máximo de búsquedas en historial

        self.init_ui()
        self.apply_styles()
        self.load_initial_data()

    def init_ui(self):
        """Inicializa la interfaz"""
        self.setWindowTitle("BÚSQUEDA UNIVERSAL")
        self.setMinimumSize(1400, 800)

        # Configurar botones de la ventana (minimizar, maximizar, cerrar)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header con pestañas
        header = self.create_header()
        main_layout.addWidget(header)

        # Splitter para panel lateral y contenido principal
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel lateral izquierdo (Filtro por Tags)
        self.tag_filter_panel = self.create_tag_filter_panel()
        splitter.addWidget(self.tag_filter_panel)

        # Panel principal (derecha)
        main_panel = QWidget()
        main_panel_layout = QVBoxLayout(main_panel)
        main_panel_layout.setContentsMargins(10, 10, 10, 10)
        main_panel_layout.setSpacing(10)

        # Barra de búsqueda
        search_bar = self.create_search_bar()
        main_panel_layout.addWidget(search_bar)

        # Filtros de tipo de entidad
        entity_filters = self.create_entity_filters()
        main_panel_layout.addWidget(entity_filters)

        # Botones de selección
        selection_buttons = self.create_selection_buttons()
        main_panel_layout.addWidget(selection_buttons)

        # Tabla de resultados
        self.results_table = self.create_results_table()
        main_panel_layout.addWidget(self.results_table)

        # Splitter secundario para tabla + preview
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(main_panel)

        # Panel de preview/detalles (derecha)
        self.preview_panel = self.create_preview_panel()
        main_splitter.addWidget(self.preview_panel)

        # Configurar proporciones del splitter secundario
        main_splitter.setSizes([800, 350])  # Tabla: 800px, Preview: 350px
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        splitter.addWidget(main_splitter)

        # Configurar proporciones del splitter principal
        splitter.setSizes([250, 1150])  # Panel tags: 250px, Main: 1150px
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        # Barra de estado
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

    def create_header(self):
        """Crea el header con pestañas"""
        header = QFrame()
        header.setFixedHeight(50)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Pestañas
        self.tab_buttons = {}

        tabs = [
            ("refrescar", "🔄 Refrescar"),
            ("mas_usados", "🔥 Más Usados"),
            ("con_tags", "🏷️ Con Tags"),
            ("recientes", "🕐 Recientes"),
            ("items", "📦 -Items")
        ]

        self.tab_group = QButtonGroup()
        for tab_id, tab_text in tabs:
            btn = QPushButton(tab_text)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, tid=tab_id: self.on_tab_clicked(tid))
            self.tab_buttons[tab_id] = btn
            self.tab_group.addButton(btn)
            layout.addWidget(btn)

        # Seleccionar "items" por defecto
        self.tab_buttons["items"].setChecked(True)

        layout.addStretch()

        # Botones de exportación
        export_csv_btn = QPushButton("📊 Exportar CSV")
        export_csv_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        export_csv_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(export_csv_btn)

        export_json_btn = QPushButton("📄 Exportar JSON")
        export_json_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        export_json_btn.clicked.connect(self.export_to_json)
        layout.addWidget(export_json_btn)

        return header

    def create_search_bar(self):
        """Crea la barra de búsqueda"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Icono de búsqueda
        icon_label = QLabel("🔍")
        icon_label.setFixedSize(30, 30)
        layout.addWidget(icon_label)

        # Input de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setFixedHeight(35)
        layout.addWidget(self.search_input)

        # Botón de historial
        self.history_btn = QPushButton("📜")
        self.history_btn.setFixedSize(35, 35)
        self.history_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.history_btn.setToolTip("Historial de búsquedas")
        self.history_btn.clicked.connect(self.show_search_history)
        self.history_btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e42;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #4e4e52;
            }
        """)
        layout.addWidget(self.history_btn)

        # Botón de ayuda para operadores
        self.help_btn = QPushButton("?")
        self.help_btn.setFixedSize(35, 35)
        self.help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.help_btn.setToolTip("Ayuda de búsqueda")
        self.help_btn.clicked.connect(self.show_search_help)
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e42;
                color: #00ff88;
                border: 1px solid #555555;
                border-radius: 3px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4e4e52;
            }
        """)
        layout.addWidget(self.help_btn)

        # Indicador de carga
        self.loading_label = QLabel("⏳ Buscando...")
        self.loading_label.setStyleSheet("color: #FFA500; font-style: italic;")
        self.loading_label.setVisible(False)  # Oculto por defecto
        layout.addWidget(self.loading_label)

        return container

    def create_entity_filters(self):
        """Crea los checkboxes de filtro por entidad"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.entity_checkboxes = {}

        entities = [
            ("proyectos", "☐ Proyectos"),
            ("areas", "☐ Areas"),
            ("procesos", "☐ Procesos"),
            ("tablas", "☐ Tablas"),
            ("categorias", "☐ Categorias")
        ]

        for entity_id, entity_text in entities:
            cb = QCheckBox(entity_text)
            cb.setChecked(True)  # Todos marcados por defecto
            cb.stateChanged.connect(self.on_filter_changed)
            self.entity_checkboxes[entity_id] = cb
            layout.addWidget(cb)

        layout.addStretch()

        return container

    def create_selection_buttons(self):
        """Crea los botones de selección rápida"""
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Selección rápida:")
        label.setStyleSheet("font-weight: bold; color: #cccccc;")
        layout.addWidget(label)

        # Botones
        btn_select_all = QPushButton("✓ Seleccionar Todo")
        btn_select_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_select_all.clicked.connect(self.select_all_results)
        layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("✗ Deseleccionar Todo")
        btn_deselect_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_deselect_all.clicked.connect(self.deselect_all_results)
        layout.addWidget(btn_deselect_all)

        btn_invert = QPushButton("⇄ Invertir Selección")
        btn_invert.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_invert.clicked.connect(self.invert_selection)
        layout.addWidget(btn_invert)

        layout.addStretch()

        # Acciones en lote
        label_actions = QLabel("Acciones:")
        label_actions.setStyleSheet("font-weight: bold; color: #cccccc;")
        layout.addWidget(label_actions)

        btn_copy_selected = QPushButton("📋 Copiar Seleccionados")
        btn_copy_selected.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy_selected.clicked.connect(self.copy_selected_batch)
        layout.addWidget(btn_copy_selected)

        btn_favorite_selected = QPushButton("⭐ Marcar Favoritos")
        btn_favorite_selected.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_favorite_selected.clicked.connect(self.mark_selected_as_favorite)
        layout.addWidget(btn_favorite_selected)

        btn_delete_selected = QPushButton("🗑️ Eliminar Seleccionados")
        btn_delete_selected.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_delete_selected.clicked.connect(self.delete_selected_batch)
        layout.addWidget(btn_delete_selected)

        return container

    def create_results_table(self):
        """Crea la tabla de resultados"""
        table = QTableWidget()
        table.setColumnCount(8)

        headers = ["☐", "Nombre", "PROYECTO", "AREA", "TABLA", "PROCESO", "CATEGORIA", "LISTA"]
        table.setHorizontalHeaderLabels(headers)

        # Configurar header
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre
        for i in range(2, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        table.setColumnWidth(0, 40)  # Checkbox

        # Configurar tabla
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.setSortingEnabled(True)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Eventos
        table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        table.customContextMenuRequested.connect(self.show_context_menu)
        table.itemSelectionChanged.connect(self.on_selection_changed)

        return table

    def create_tag_filter_panel(self):
        """Crea el panel lateral de filtro por tags"""
        panel = QFrame()
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("🏷️ Filtro por Tags")
        header.setStyleSheet("""
            QLabel {
                font-size: 12pt;
                font-weight: bold;
                color: #00ff88;
                padding: 5px;
            }
        """)
        layout.addWidget(header)

        # Contador de tags
        self.tag_count_label = QLabel("[0 tags]")
        self.tag_count_label.setStyleSheet("color: #888888; padding: 5px;")
        layout.addWidget(self.tag_count_label)

        # Área de scroll para tags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.tag_list_widget = QWidget()
        self.tag_list_layout = QVBoxLayout(self.tag_list_widget)
        self.tag_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Mensaje inicial
        self.no_tags_label = QLabel("No hay tags disponibles\n\nLos tags aparecerán\nautomáticamente al\nbuscar items")
        self.no_tags_label.setStyleSheet("color: #666666; padding: 20px;")
        self.no_tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tag_list_layout.addWidget(self.no_tags_label)

        scroll.setWidget(self.tag_list_widget)
        layout.addWidget(scroll)

        # Botón limpiar
        btn_clear = QPushButton("Limpiar")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self.clear_tag_filters)
        layout.addWidget(btn_clear)

        return panel

    def create_preview_panel(self):
        """Crea el panel de preview/detalles"""
        panel = QFrame()
        panel.setFixedWidth(350)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header = QLabel("📋 Vista Previa")
        header.setStyleSheet("""
            QLabel {
                font-size: 12pt;
                font-weight: bold;
                color: #00ff88;
                padding: 5px;
            }
        """)
        layout.addWidget(header)

        # Scroll area para el contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Widget contenedor del preview
        self.preview_content = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_content)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.preview_layout.setSpacing(10)

        # Mensaje inicial
        self.no_preview_label = QLabel(
            "Selecciona un item\npara ver sus detalles"
        )
        self.no_preview_label.setStyleSheet("""
            QLabel {
                color: #666666;
                padding: 40px 20px;
                font-size: 11pt;
            }
        """)
        self.no_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addWidget(self.no_preview_label)

        scroll.setWidget(self.preview_content)
        layout.addWidget(scroll)

        return panel

    def create_status_bar(self):
        """Crea la barra de estado inferior con paginación"""
        status_bar = QFrame()
        status_bar.setFixedHeight(30)
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(10, 5, 10, 5)

        self.status_label = QLabel("📊 0 Items | 0 tags")
        self.status_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Controles de paginación
        self.pagination_label = QLabel("Página 1 de 1")
        self.pagination_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.pagination_label)

        self.btn_prev_page = QPushButton("◀ Anterior")
        self.btn_prev_page.setFixedSize(100, 25)
        self.btn_prev_page.clicked.connect(self.go_to_prev_page)
        self.btn_prev_page.setEnabled(False)
        layout.addWidget(self.btn_prev_page)

        self.btn_next_page = QPushButton("Siguiente ▶")
        self.btn_next_page.setFixedSize(100, 25)
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        self.btn_next_page.setEnabled(False)
        layout.addWidget(self.btn_next_page)

        return status_bar

    def on_search_text_changed(self, text):
        """Handler cuando cambia el texto de búsqueda"""
        # Resetear paginación al cambiar búsqueda
        self.reset_pagination()
        # Debounce: esperar 300ms después del último cambio
        self.search_timer.stop()
        self.search_timer.start(300)

    def perform_search(self):
        """Realiza la búsqueda con paginación y operadores"""
        query = self.search_input.text().strip()

        if not query:
            # Si no hay query, mostrar items recientes
            self.load_recent_items()
            return

        try:
            # Mostrar indicador de carga
            self.show_loading()

            # Agregar al historial
            self.add_to_history(query)

            # Parsear query para detectar operadores
            parsed_query = self.parse_search_query(query)

            # Usar la query base para la búsqueda
            search_query = parsed_query['base_query']

            logger.info(f"Buscando con query: '{search_query}'")

            # Obtener conteo total
            self.total_items = self.db.universal_search_items_count(search_query)
            logger.info(f"Total items encontrados: {self.total_items}")

            # Calcular offset
            offset = (self.current_page - 1) * self.page_size

            # Buscar items con paginación
            results = self.search_engine.search_items(search_query, limit=self.page_size, offset=offset)
            logger.info(f"Resultados obtenidos: {len(results)}")

            # Aplicar operadores de búsqueda solo si hay operadores
            if parsed_query['has_operators']:
                logger.info("Aplicando operadores de búsqueda...")
                results = self.apply_search_operators(results, parsed_query)
                logger.info(f"Resultados después de operadores: {len(results)}")

            self.current_results = results
            self.update_results_table(results)
            self.update_tag_filter_panel(results)
            self.update_status_bar()
            self.update_pagination_controls()

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error en búsqueda:\n{str(e)}")
        finally:
            # Ocultar indicador de carga
            self.hide_loading()
            # Mantener el foco en el campo de búsqueda
            self.search_input.setFocus()

    def load_initial_data(self):
        """Carga datos iniciales (items recientes)"""
        self.load_recent_items()

    def load_recent_items(self):
        """Carga items recientes"""
        try:
            self.show_loading()
            results = self.search_engine.get_recent_items(limit=100)
            self.current_results = results
            self.update_results_table(results)
            self.update_tag_filter_panel(results)
            self.update_status_bar()
        except Exception as e:
            logger.error(f"Error cargando items recientes: {e}", exc_info=True)
        finally:
            self.hide_loading()
            # Mantener el foco en el campo de búsqueda
            self.search_input.setFocus()

    def update_results_table(self, results):
        """Actualiza la tabla con los resultados"""
        self.results_table.setRowCount(0)
        self.results_table.setSortingEnabled(False)

        for row, result in enumerate(results):
            self.results_table.insertRow(row)

            # Checkbox
            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.results_table.setCellWidget(row, 0, cb_widget)

            # Nombre con icono
            icon = result.icon if result.icon else "📄"
            name_text = f"{icon} {result.name}"
            name_item = QTableWidgetItem(name_text)
            self.results_table.setItem(row, 1, name_item)

            # Proyectos
            proyectos_text = ", ".join(result.proyectos) if result.proyectos else ""
            self.results_table.setItem(row, 2, QTableWidgetItem(proyectos_text))

            # Areas
            areas_text = ", ".join(result.areas) if result.areas else ""
            self.results_table.setItem(row, 3, QTableWidgetItem(areas_text))

            # Tabla
            tabla_text = result.tabla if result.tabla else ""
            self.results_table.setItem(row, 4, QTableWidgetItem(tabla_text))

            # Proceso
            procesos_text = ", ".join(result.procesos) if result.procesos else ""
            self.results_table.setItem(row, 5, QTableWidgetItem(procesos_text))

            # Categoría
            categoria_text = result.categoria if result.categoria else ""
            self.results_table.setItem(row, 6, QTableWidgetItem(categoria_text))

            # Lista
            lista_text = result.lista if result.lista else ""
            self.results_table.setItem(row, 7, QTableWidgetItem(lista_text))

        self.results_table.setSortingEnabled(True)

    def update_tag_filter_panel(self, results):
        """Actualiza el panel de filtro por tags"""
        # Limpiar tags anteriores
        while self.tag_list_layout.count():
            item = self.tag_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Extraer tags únicos
        unique_tags = self.search_engine.extract_unique_tags(results)

        if not unique_tags:
            # Mostrar mensaje si no hay tags
            self.no_tags_label = QLabel("No hay tags disponibles\n\nLos tags aparecerán\nautomáticamente al\nbuscar items")
            self.no_tags_label.setStyleSheet("color: #666666; padding: 20px;")
            self.no_tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tag_list_layout.addWidget(self.no_tags_label)
            self.tag_count_label.setText("[0 tags]")
        else:
            # Agregar checkboxes para cada tag
            for tag_name, count in unique_tags[:50]:  # Limitar a 50 tags
                cb = QCheckBox(f"{tag_name} ({count})")
                cb.stateChanged.connect(self.on_filter_changed)
                self.tag_list_layout.addWidget(cb)

            self.tag_count_label.setText(f"[{len(unique_tags)} tags]")

    def update_status_bar(self):
        """Actualiza la barra de estado"""
        stats = self.search_engine.get_statistics(self.current_results)

        status_parts = []
        status_parts.append(f"📊 {stats['total']} Items")

        if stats['with_proyectos'] > 0:
            status_parts.append(f"Proyectos: {stats['with_proyectos']}")
        if stats['with_areas'] > 0:
            status_parts.append(f"Areas: {stats['with_areas']}")
        if stats['with_tablas'] > 0:
            status_parts.append(f"Tablas: {stats['with_tablas']}")
        if stats['unique_tags'] > 0:
            status_parts.append(f"{stats['unique_tags']} tags")
        if stats['with_procesos'] > 0:
            status_parts.append(f"Procesos: {stats['with_procesos']}")

        self.status_label.setText(" | ".join(status_parts))

    def update_pagination_controls(self):
        """Actualiza los controles de paginación"""
        if self.total_items == 0:
            self.pagination_label.setText("Página 0 de 0")
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            return

        total_pages = (self.total_items + self.page_size - 1) // self.page_size
        start_item = (self.current_page - 1) * self.page_size + 1
        end_item = min(self.current_page * self.page_size, self.total_items)

        self.pagination_label.setText(
            f"Página {self.current_page} de {total_pages} ({start_item}-{end_item} de {self.total_items})"
        )

        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < total_pages)

    def go_to_prev_page(self):
        """Ir a la página anterior"""
        if self.current_page > 1:
            self.current_page -= 1
            self.perform_search()

    def go_to_next_page(self):
        """Ir a la página siguiente"""
        total_pages = (self.total_items + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self.perform_search()

    def reset_pagination(self):
        """Reinicia la paginación a la primera página"""
        self.current_page = 1
        self.total_items = 0

    def on_tab_clicked(self, tab_id):
        """Handler cuando se hace clic en una pestaña"""
        if tab_id == "refrescar":
            self.perform_search()
        elif tab_id == "mas_usados":
            self.load_most_used()
        elif tab_id == "con_tags":
            self.load_items_with_tags()
        elif tab_id == "recientes":
            self.load_recent_items()
        elif tab_id == "items":
            # Vista por defecto
            if self.search_input.text().strip():
                self.perform_search()
            else:
                self.load_recent_items()

    def load_most_used(self):
        """Carga items más usados"""
        try:
            self.show_loading()
            results = self.search_engine.get_most_used(limit=100)
            self.current_results = results
            self.update_results_table(results)
            self.update_tag_filter_panel(results)
            self.update_status_bar()
        except Exception as e:
            logger.error(f"Error cargando items más usados: {e}", exc_info=True)
        finally:
            self.hide_loading()
            # Mantener el foco en el campo de búsqueda
            self.search_input.setFocus()

    def load_items_with_tags(self):
        """Carga items con tags"""
        try:
            self.show_loading()
            results = self.search_engine.get_items_with_tags(limit=1000)
            self.current_results = results
            self.update_results_table(results)
            self.update_tag_filter_panel(results)
            self.update_status_bar()
        except Exception as e:
            logger.error(f"Error cargando items con tags: {e}", exc_info=True)
        finally:
            self.hide_loading()
            # Mantener el foco en el campo de búsqueda
            self.search_input.setFocus()

    def on_filter_changed(self):
        """Handler cuando cambian los filtros - con debouncing"""
        # Detener timer previo y reiniciar (debouncing de 200ms)
        self.filter_timer.stop()
        self.filter_timer.start(200)

    def apply_filters_debounced(self):
        """Aplica filtros con debouncing y caché"""
        if not self.current_results:
            return

        # Obtener filtros de entidad
        entity_filters = {
            'proyectos': self.entity_checkboxes['proyectos'].isChecked(),
            'areas': self.entity_checkboxes['areas'].isChecked(),
            'categorias': self.entity_checkboxes['categorias'].isChecked(),
            'tablas': self.entity_checkboxes['tablas'].isChecked(),
            'procesos': self.entity_checkboxes['procesos'].isChecked()
        }

        # Obtener filtros de tags
        tag_filters = []
        for i in range(self.tag_list_layout.count()):
            widget = self.tag_list_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                # Extraer nombre del tag (antes del paréntesis)
                tag_text = widget.text()
                tag_name = tag_text.split('(')[0].strip()
                tag_filters.append(tag_name)

        # Verificar si los filtros han cambiado (caché)
        if (self.last_entity_filters == entity_filters and
            self.last_tag_filters == tag_filters):
            return  # No hay cambios, evitar recálculo

        # Guardar filtros actuales en caché
        self.last_entity_filters = entity_filters.copy()
        self.last_tag_filters = tag_filters.copy()

        # Aplicar filtros
        filtered_results = self.search_engine.apply_filters(
            self.current_results,
            entity_filters,
            tag_filters
        )

        self.update_results_table(filtered_results)
        self.update_status_bar()

    def select_all_results(self):
        """Selecciona todos los resultados"""
        for row in range(self.results_table.rowCount()):
            cb_widget = self.results_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def deselect_all_results(self):
        """Deselecciona todos los resultados"""
        for row in range(self.results_table.rowCount()):
            cb_widget = self.results_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def invert_selection(self):
        """Invierte la selección"""
        for row in range(self.results_table.rowCount()):
            cb_widget = self.results_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(not cb.isChecked())

    def clear_tag_filters(self):
        """Limpia los filtros de tags"""
        for i in range(self.tag_list_layout.count()):
            widget = self.tag_list_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def on_selection_changed(self):
        """Handler cuando cambia la selección en la tabla"""
        selected_rows = self.results_table.selectedItems()
        if not selected_rows:
            self.clear_preview()
            return

        # Obtener la fila seleccionada
        row = self.results_table.currentRow()
        if row >= 0 and row < len(self.current_results):
            result = self.current_results[row]
            self.update_preview(result)

    def update_preview(self, result):
        """Actualiza el panel de preview con los detalles del item"""
        # Limpiar contenido anterior
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Título con icono
        title = QLabel(f"{result.icon} {result.name}")
        title.setStyleSheet("""
            QLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #ffffff;
                padding: 5px;
                background-color: #2d2d30;
                border-radius: 4px;
            }
        """)
        title.setWordWrap(True)
        self.preview_layout.addWidget(title)

        # Tipo de resultado
        type_label = QLabel(f"Tipo: {result.result_type.value}")
        type_label.setStyleSheet("color: #888888; font-size: 9pt;")
        self.preview_layout.addWidget(type_label)

        # Separador
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background-color: #3e3e42;")
        self.preview_layout.addWidget(sep1)

        # Contenido
        if result.content:
            content_label = QLabel("📄 Contenido:")
            content_label.setStyleSheet("font-weight: bold; color: #cccccc;")
            self.preview_layout.addWidget(content_label)

            content_text = QTextEdit()
            content_text.setPlainText(result.content)
            content_text.setReadOnly(True)
            content_text.setMaximumHeight(150)
            content_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                    border-radius: 3px;
                    padding: 5px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 9pt;
                }
            """)
            self.preview_layout.addWidget(content_text)

        # Descripción
        if result.description:
            desc_label = QLabel("📝 Descripción:")
            desc_label.setStyleSheet("font-weight: bold; color: #cccccc;")
            self.preview_layout.addWidget(desc_label)

            desc_text = QLabel(result.description)
            desc_text.setWordWrap(True)
            desc_text.setStyleSheet("color: #d4d4d4; padding: 5px;")
            self.preview_layout.addWidget(desc_text)

        # Tags
        if result.tags:
            tags_label = QLabel("🏷️ Tags:")
            tags_label.setStyleSheet("font-weight: bold; color: #cccccc;")
            self.preview_layout.addWidget(tags_label)

            tags_container = QWidget()
            tags_layout = QHBoxLayout(tags_container)
            tags_layout.setContentsMargins(0, 0, 0, 0)
            tags_layout.setSpacing(5)
            tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for tag in result.tags[:10]:  # Limitar a 10 tags
                tag_btn = QPushButton(tag)
                tag_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007acc;
                        color: #ffffff;
                        border: none;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 8pt;
                    }
                """)
                tag_btn.setFixedHeight(22)
                tags_layout.addWidget(tag_btn)

            if len(result.tags) > 10:
                more_label = QLabel(f"+{len(result.tags) - 10} más")
                more_label.setStyleSheet("color: #888888; font-size: 8pt;")
                tags_layout.addWidget(more_label)

            self.preview_layout.addWidget(tags_container)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background-color: #3e3e42;")
        self.preview_layout.addWidget(sep2)

        # Relaciones
        relations_label = QLabel("🔗 Relaciones:")
        relations_label.setStyleSheet("font-weight: bold; color: #cccccc;")
        self.preview_layout.addWidget(relations_label)

        if result.proyectos:
            proj_label = QLabel(f"📁 Proyectos: {', '.join(result.proyectos)}")
            proj_label.setWordWrap(True)
            proj_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(proj_label)

        if result.areas:
            area_label = QLabel(f"🏢 Áreas: {', '.join(result.areas)}")
            area_label.setWordWrap(True)
            area_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(area_label)

        if result.categoria:
            cat_label = QLabel(f"📂 Categoría: {result.categoria}")
            cat_label.setWordWrap(True)
            cat_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(cat_label)

        if result.tabla:
            tabla_label = QLabel(f"📊 Tabla: {result.tabla}")
            tabla_label.setWordWrap(True)
            tabla_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(tabla_label)

        if result.lista:
            lista_label = QLabel(f"📋 Lista: {result.lista}")
            lista_label.setWordWrap(True)
            lista_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(lista_label)

        if result.procesos:
            proc_label = QLabel(f"⚙️ Procesos: {', '.join(result.procesos)}")
            proc_label.setWordWrap(True)
            proc_label.setStyleSheet("color: #d4d4d4; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(proc_label)

        # Separador
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("background-color: #3e3e42;")
        self.preview_layout.addWidget(sep3)

        # Metadata
        meta_label = QLabel("ℹ️ Información:")
        meta_label.setStyleSheet("font-weight: bold; color: #cccccc;")
        self.preview_layout.addWidget(meta_label)

        if result.is_favorite:
            fav_label = QLabel("⭐ Favorito")
            fav_label.setStyleSheet("color: #FFD700; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(fav_label)

        if result.is_sensitive:
            sens_label = QLabel("🔒 Sensible (cifrado)")
            sens_label.setStyleSheet("color: #ff6b6b; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(sens_label)

        usage_label = QLabel(f"📈 Usado {result.use_count} veces")
        usage_label.setStyleSheet("color: #888888; font-size: 9pt; padding-left: 10px;")
        self.preview_layout.addWidget(usage_label)

        if result.last_used:
            last_used_label = QLabel(f"🕐 Último uso: {result.last_used}")
            last_used_label.setStyleSheet("color: #888888; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(last_used_label)

        if result.created_at:
            created_label = QLabel(f"📅 Creado: {result.created_at}")
            created_label.setStyleSheet("color: #888888; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(created_label)

        if result.updated_at:
            updated_label = QLabel(f"🔄 Actualizado: {result.updated_at}")
            updated_label.setStyleSheet("color: #888888; font-size: 9pt; padding-left: 10px;")
            self.preview_layout.addWidget(updated_label)

        # Separador
        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.HLine)
        sep4.setStyleSheet("background-color: #3e3e42;")
        self.preview_layout.addWidget(sep4)

        # Botones de acción
        actions_label = QLabel("⚡ Acciones:")
        actions_label.setStyleSheet("font-weight: bold; color: #cccccc;")
        self.preview_layout.addWidget(actions_label)

        # Botón copiar
        copy_btn = QPushButton("📋 Copiar Contenido")
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_btn.clicked.connect(lambda: self.copy_item_content(result))
        self.preview_layout.addWidget(copy_btn)

        # Botón favorito
        fav_text = "⭐ Quitar de Favoritos" if result.is_favorite else "⭐ Agregar a Favoritos"
        fav_btn = QPushButton(fav_text)
        fav_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        fav_btn.clicked.connect(lambda: self.toggle_favorite(result))
        self.preview_layout.addWidget(fav_btn)

        # Botón editar
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.clicked.connect(lambda: self.edit_item(result))
        self.preview_layout.addWidget(edit_btn)

        # Botón eliminar
        delete_btn = QPushButton("🗑️ Eliminar")
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #c41e3a;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #e4475b;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_item(result))
        self.preview_layout.addWidget(delete_btn)

        # Spacer al final
        self.preview_layout.addStretch()

    def clear_preview(self):
        """Limpia el panel de preview"""
        # Limpiar contenido anterior
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Restaurar mensaje inicial
        self.no_preview_label = QLabel(
            "Selecciona un item\npara ver sus detalles"
        )
        self.no_preview_label.setStyleSheet("""
            QLabel {
                color: #666666;
                padding: 40px 20px;
                font-size: 11pt;
            }
        """)
        self.no_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addWidget(self.no_preview_label)

    def on_cell_double_clicked(self, row, column):
        """Handler cuando se hace doble clic en una celda"""
        if row >= 0 and row < len(self.current_results):
            result = self.current_results[row]
            if result.result_type == SearchResultType.ITEM:
                # Copiar contenido al portapapeles
                try:
                    import pyperclip
                    pyperclip.copy(result.content)
                    logger.info(f"Item copiado: {result.name}")
                    self.item_copied.emit(result.id)
                except Exception as e:
                    logger.error(f"Error copiando item: {e}")

    def show_loading(self):
        """Muestra el indicador de carga"""
        self.loading_label.setVisible(True)
        self.search_input.setEnabled(False)
        self.results_table.setEnabled(False)

    def hide_loading(self):
        """Oculta el indicador de carga"""
        self.loading_label.setVisible(False)
        self.search_input.setEnabled(True)
        self.results_table.setEnabled(True)

    def focus_search_bar(self):
        """Pone el foco en la barra de búsqueda"""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def parse_search_query(self, query):
        """
        Parsea la query de búsqueda extrayendo operadores y términos

        Returns:
            dict con:
                - 'base_query': query limpia para el motor de búsqueda
                - 'and_terms': términos que DEBEN estar (AND, +)
                - 'or_terms': términos de los que AL MENOS UNO debe estar (OR, |)
                - 'not_terms': términos que NO deben estar (NOT, -)
                - 'exact_phrases': frases exactas entre comillas
                - 'has_operators': True si se detectaron operadores
        """
        parsed = {
            'base_query': query,
            'and_terms': [],
            'or_terms': [],
            'not_terms': [],
            'exact_phrases': [],
            'has_operators': False
        }

        # Extraer frases exactas (entre comillas)
        exact_phrases = re.findall(r'"([^"]+)"', query)
        if exact_phrases:
            parsed['exact_phrases'] = exact_phrases
            parsed['has_operators'] = True

        # Remover frases exactas de la query para procesar el resto
        query_without_phrases = re.sub(r'"[^"]+"', '', query)

        # Detectar términos NOT (- o NOT seguido de palabra)
        not_terms = re.findall(r'(?:NOT\s+|-)(\w+)', query_without_phrases, re.IGNORECASE)
        if not_terms:
            parsed['not_terms'] = not_terms
            parsed['has_operators'] = True
            query_without_phrases = re.sub(r'(?:NOT\s+|-)(\w+)', '', query_without_phrases, re.IGNORECASE)

        # Detectar términos con AND explícito (AND o +)
        and_terms = re.findall(r'(?:AND\s+|\+)(\w+)', query_without_phrases, re.IGNORECASE)
        if and_terms:
            parsed['and_terms'] = and_terms
            parsed['has_operators'] = True
            query_without_phrases = re.sub(r'(?:AND\s+|\+)(\w+)', '', query_without_phrases, re.IGNORECASE)

        # Detectar términos con OR explícito (OR o |)
        or_terms = re.findall(r'(?:OR\s+|\|)(\w+)', query_without_phrases, re.IGNORECASE)
        if or_terms:
            parsed['or_terms'] = or_terms
            parsed['has_operators'] = True
            query_without_phrases = re.sub(r'(?:OR\s+|\|)(\w+)', '', query_without_phrases, re.IGNORECASE)

        # Los términos restantes se consideran términos base (búsqueda normal)
        remaining_terms = [t for t in query_without_phrases.strip().split() if t]

        # Crear query base limpia para el motor de búsqueda
        # Si HAY operadores, combinar todos los términos
        # Si NO hay operadores, usar la query original
        if parsed['has_operators']:
            all_search_terms = remaining_terms + and_terms + or_terms
            parsed['base_query'] = ' '.join(all_search_terms + exact_phrases)
        else:
            # No hay operadores, usar la query original
            parsed['base_query'] = query

        logger.info(f"Query parseada: base='{parsed['base_query']}', operadores={parsed['has_operators']}")
        return parsed

    def apply_search_operators(self, results, parsed_query):
        """
        Aplica los operadores de búsqueda a los resultados

        Args:
            results: Lista de SearchResult
            parsed_query: Diccionario retornado por parse_search_query

        Returns:
            Lista filtrada de SearchResult
        """
        if not results:
            return results

        filtered_results = []

        for result in results:
            # Crear texto combinado para buscar (nombre + contenido + descripción + tags)
            search_text = f"{result.name} {result.content} {result.description or ''}"
            if result.tags:
                search_text += " " + " ".join(result.tags)
            search_text = search_text.lower()

            # Verificar términos NOT (deben NO estar)
            has_not_term = False
            for not_term in parsed_query['not_terms']:
                if not_term.lower() in search_text:
                    has_not_term = True
                    break

            if has_not_term:
                continue  # Saltar este resultado

            # Verificar términos AND (TODOS deben estar)
            all_and_present = True
            for and_term in parsed_query['and_terms']:
                if and_term.lower() not in search_text:
                    all_and_present = False
                    break

            if not all_and_present:
                continue  # Saltar este resultado

            # Verificar frases exactas (deben estar exactamente)
            all_phrases_present = True
            for phrase in parsed_query['exact_phrases']:
                if phrase.lower() not in search_text:
                    all_phrases_present = False
                    break

            if not all_phrases_present:
                continue  # Saltar este resultado

            # Verificar términos OR (al menos UNO debe estar)
            if parsed_query['or_terms']:
                any_or_present = False
                for or_term in parsed_query['or_terms']:
                    if or_term.lower() in search_text:
                        any_or_present = True
                        break

                if not any_or_present:
                    continue  # Saltar este resultado

            # Si llegamos aquí, el resultado cumple todos los criterios
            filtered_results.append(result)

        logger.info(f"Operadores aplicados: {len(results)} -> {len(filtered_results)} resultados")
        return filtered_results

    def add_to_history(self, query):
        """Agrega una búsqueda al historial"""
        if not query or len(query) < 2:
            return

        # Remover si ya existe (para evitar duplicados)
        if query in self.search_history:
            self.search_history.remove(query)

        # Agregar al inicio de la lista
        self.search_history.insert(0, query)

        # Limitar tamaño del historial
        if len(self.search_history) > self.max_history:
            self.search_history = self.search_history[:self.max_history]

        logger.info(f"Búsqueda agregada al historial: {query}")

    def show_search_history(self):
        """Muestra el menú con el historial de búsquedas"""
        if not self.search_history:
            QMessageBox.information(
                self,
                "Historial Vacío",
                "No hay búsquedas en el historial.\n\nRealiza una búsqueda para que aparezca aquí."
            )
            return

        # Crear menú contextual
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d30;
                color: #cccccc;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
        """)

        # Agregar búsquedas recientes
        for i, query in enumerate(self.search_history[:15]):  # Mostrar últimas 15
            action = QAction(f"🔍 {query}", self)
            action.triggered.connect(lambda checked, q=query: self.load_from_history(q))
            menu.addAction(action)

        # Separador
        menu.addSeparator()

        # Opción para limpiar historial
        clear_action = QAction("🗑️ Limpiar Historial", self)
        clear_action.triggered.connect(self.clear_search_history)
        menu.addAction(clear_action)

        # Mostrar menú debajo del botón
        button_pos = self.history_btn.mapToGlobal(self.history_btn.rect().bottomLeft())
        menu.exec(button_pos)

    def load_from_history(self, query):
        """Carga una búsqueda desde el historial"""
        logger.info(f"Cargando búsqueda desde historial: {query}")
        self.search_input.setText(query)
        # perform_search se llamará automáticamente por el signal textChanged

    def clear_search_history(self):
        """Limpia el historial de búsquedas"""
        reply = QMessageBox.question(
            self,
            "Limpiar Historial",
            "¿Estás seguro de limpiar todo el historial de búsquedas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.search_history.clear()
            logger.info("Historial de búsquedas limpiado")
            QMessageBox.information(self, "Historial Limpiado", "Se limpió el historial de búsquedas")

    def show_search_help(self):
        """Muestra ayuda sobre operadores de búsqueda"""
        help_text = """
<h2 style='color: #00ff88;'>🔍 Ayuda de Búsqueda Avanzada</h2>

<h3 style='color: #cccccc;'>📋 Operadores Disponibles:</h3>

<p style='color: #d4d4d4; margin-left: 20px;'>
<b style='color: #00ff88;'>AND (+)</b><br>
Busca items que contengan TODOS los términos.<br>
<i>Ejemplo:</i> <code>python AND flask</code> o <code>python +flask</code><br>
<i>Resultado:</i> Items que contengan "python" Y "flask"
</p>

<p style='color: #d4d4d4; margin-left: 20px;'>
<b style='color: #00ff88;'>OR (|)</b><br>
Busca items que contengan AL MENOS UNO de los términos.<br>
<i>Ejemplo:</i> <code>python OR javascript</code> o <code>python | javascript</code><br>
<i>Resultado:</i> Items que contengan "python" O "javascript"
</p>

<p style='color: #d4d4d4; margin-left: 20px;'>
<b style='color: #00ff88;'>NOT (-)</b><br>
Excluye items que contengan el término.<br>
<i>Ejemplo:</i> <code>python NOT django</code> o <code>python -django</code><br>
<i>Resultado:</i> Items con "python" pero SIN "django"
</p>

<p style='color: #d4d4d4; margin-left: 20px;'>
<b style='color: #00ff88;'>Comillas ""</b><br>
Busca la frase exacta.<br>
<i>Ejemplo:</i> <code>"hello world"</code><br>
<i>Resultado:</i> Items que contengan exactamente "hello world"
</p>

<h3 style='color: #cccccc;'>💡 Ejemplos Combinados:</h3>

<p style='color: #d4d4d4; margin-left: 20px;'>
• <code>python AND "machine learning" NOT tensorflow</code><br>
• <code>react | vue | angular</code><br>
• <code>"data science" +python -R</code>
</p>

<h3 style='color: #cccccc;'>ℹ️ Notas:</h3>

<p style='color: #888888; margin-left: 20px;'>
• Si no usas operadores, la búsqueda encuentra items que contengan cualquiera de las palabras<br>
• Los operadores NO son sensibles a mayúsculas/minúsculas<br>
• Puedes combinar múltiples operadores en una misma búsqueda
</p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Ayuda de Búsqueda")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #cccccc;
                min-width: 500px;
            }
            QPushButton {
                background-color: #3e3e42;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4e4e52;
            }
        """)
        msg.exec()

    def show_context_menu(self, position: QPoint):
        """Muestra el menú contextual en la tabla"""
        # Obtener la fila clickeada
        row = self.results_table.rowAt(position.y())
        if row < 0 or row >= len(self.current_results):
            return

        result = self.current_results[row]

        # Crear menú
        menu = QMenu(self)

        # Acción: Copiar contenido
        copy_action = QAction("📋 Copiar contenido", self)
        copy_action.triggered.connect(lambda: self.copy_item_content(result))
        menu.addAction(copy_action)

        # Acción: Copiar seleccionados
        selected_count = self.get_selected_count()
        if selected_count > 1:
            copy_selected_action = QAction(f"📋 Copiar {selected_count} items seleccionados", self)
            copy_selected_action.triggered.connect(self.copy_selected_items)
            menu.addAction(copy_selected_action)

        menu.addSeparator()

        # Acción: Editar
        edit_action = QAction("✏️ Editar", self)
        edit_action.triggered.connect(lambda: self.edit_item(result))
        menu.addAction(edit_action)

        # Acción: Eliminar
        delete_action = QAction("🗑️ Eliminar", self)
        delete_action.triggered.connect(lambda: self.delete_item(result))
        menu.addAction(delete_action)

        menu.addSeparator()

        # Acción: Agregar/Quitar de favoritos
        fav_text = "⭐ Quitar de favoritos" if result.is_favorite else "⭐ Agregar a favoritos"
        fav_action = QAction(fav_text, self)
        fav_action.triggered.connect(lambda: self.toggle_favorite(result))
        menu.addAction(fav_action)

        menu.addSeparator()

        # Navegación
        if result.categoria:
            nav_cat_action = QAction(f"📂 Ir a categoría: {result.categoria}", self)
            nav_cat_action.triggered.connect(lambda: self.navigate_to_category(result))
            menu.addAction(nav_cat_action)

        if result.proyectos:
            for proyecto in result.proyectos:
                nav_proj_action = QAction(f"📁 Ir a proyecto: {proyecto}", self)
                nav_proj_action.triggered.connect(lambda checked, p=proyecto: self.navigate_to_project(p))
                menu.addAction(nav_proj_action)

        if result.areas:
            for area in result.areas:
                nav_area_action = QAction(f"🏢 Ir a área: {area}", self)
                nav_area_action.triggered.connect(lambda checked, a=area: self.navigate_to_area(a))
                menu.addAction(nav_area_action)

        # Mostrar menú
        menu.exec(self.results_table.viewport().mapToGlobal(position))

    def get_selected_count(self):
        """Obtiene el número de items seleccionados"""
        count = 0
        for row in range(self.results_table.rowCount()):
            cb_widget = self.results_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    count += 1
        return count

    def copy_item_content(self, result):
        """Copia el contenido de un item"""
        try:
            import pyperclip
            pyperclip.copy(result.content)
            logger.info(f"Item copiado: {result.name}")
            self.item_copied.emit(result.id)
        except Exception as e:
            logger.error(f"Error copiando item: {e}")
            QMessageBox.warning(self, "Error", f"Error al copiar: {e}")

    def copy_selected_items(self):
        """Copia el contenido de todos los items seleccionados"""
        try:
            import pyperclip
            selected_contents = []

            for row in range(self.results_table.rowCount()):
                cb_widget = self.results_table.cellWidget(row, 0)
                if cb_widget:
                    cb = cb_widget.findChild(QCheckBox)
                    if cb and cb.isChecked() and row < len(self.current_results):
                        result = self.current_results[row]
                        selected_contents.append(result.content)

            if selected_contents:
                combined_content = "\n".join(selected_contents)
                pyperclip.copy(combined_content)
                logger.info(f"{len(selected_contents)} items copiados")
                QMessageBox.information(
                    self,
                    "Copiado",
                    f"Se copiaron {len(selected_contents)} items al portapapeles"
                )
        except Exception as e:
            logger.error(f"Error copiando items: {e}")
            QMessageBox.warning(self, "Error", f"Error al copiar: {e}")

    def edit_item(self, result):
        """Edita un item"""
        logger.info(f"Editando item: {result.name}")
        self.edit_item_requested.emit(result.id)

    def delete_item(self, result):
        """Elimina un item"""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar '{result.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"Eliminando item: {result.name}")
            self.delete_item_requested.emit(result.id)
            # Recargar resultados
            self.perform_search()

    def toggle_favorite(self, result):
        """Agrega o quita de favoritos"""
        logger.info(f"Toggle favorite: {result.name}")
        self.toggle_favorite_requested.emit(result.id)
        # Actualizar visualmente
        self.perform_search()

    def navigate_to_category(self, result):
        """Navega a la categoría del item"""
        # Obtener category_id del resultado
        if hasattr(result, 'categoria') and result.categoria:
            # Necesitamos buscar el ID de la categoría
            try:
                categories = self.db.get_categories()
                for cat in categories:
                    if cat['name'] == result.categoria:
                        logger.info(f"Navegando a categoría: {result.categoria}")
                        self.navigate_to_category_requested.emit(cat['id'])
                        self.close()
                        break
            except Exception as e:
                logger.error(f"Error navegando a categoría: {e}")

    def navigate_to_project(self, project_name):
        """Navega a un proyecto"""
        try:
            projects = self.db.get_all_projects()
            for proj in projects:
                if proj['name'] == project_name:
                    logger.info(f"Navegando a proyecto: {project_name}")
                    self.navigate_to_project_requested.emit(proj['id'])
                    self.close()
                    break
        except Exception as e:
            logger.error(f"Error navegando a proyecto: {e}")

    def navigate_to_area(self, area_name):
        """Navega a un área"""
        try:
            areas = self.db.get_all_areas()
            for area in areas:
                if area['name'] == area_name:
                    logger.info(f"Navegando a área: {area_name}")
                    self.navigate_to_area_requested.emit(area['id'])
                    self.close()
                    break
        except Exception as e:
            logger.error(f"Error navegando a área: {e}")

    def export_to_csv(self):
        """Exporta los resultados actuales a CSV"""
        try:
            if not self.current_results:
                QMessageBox.information(self, "Exportar CSV", "No hay resultados para exportar")
                return

            # Diálogo para seleccionar ubicación
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"busqueda_universal_{timestamp}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar a CSV",
                default_name,
                "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return  # Usuario canceló

            # Escribir CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow([
                    'ID', 'Nombre', 'Tipo', 'Proyectos', 'Áreas', 'Categoría',
                    'Tabla', 'Lista', 'Procesos', 'Tags', 'Descripción',
                    'Favorito', 'Uso', 'Última Vez', 'Creado', 'Actualizado'
                ])

                # Datos
                for result in self.current_results:
                    writer.writerow([
                        result.id,
                        result.name,
                        result.result_type.value,
                        ', '.join(result.proyectos) if result.proyectos else '',
                        ', '.join(result.areas) if result.areas else '',
                        result.categoria or '',
                        result.tabla or '',
                        result.lista or '',
                        ', '.join(result.procesos) if result.procesos else '',
                        ', '.join(result.tags) if result.tags else '',
                        result.description or '',
                        'Sí' if result.is_favorite else 'No',
                        result.use_count,
                        result.last_used or '',
                        result.created_at or '',
                        result.updated_at or ''
                    ])

            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Se exportaron {len(self.current_results)} resultados a:\n{file_path}"
            )
            logger.info(f"Exported {len(self.current_results)} results to CSV: {file_path}")

        except Exception as e:
            logger.error(f"Error exportando a CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar a CSV:\n{str(e)}")

    def export_to_json(self):
        """Exporta los resultados actuales a JSON"""
        try:
            if not self.current_results:
                QMessageBox.information(self, "Exportar JSON", "No hay resultados para exportar")
                return

            # Diálogo para seleccionar ubicación
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"busqueda_universal_{timestamp}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar a JSON",
                default_name,
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                return  # Usuario canceló

            # Convertir resultados a diccionarios
            results_data = []
            for result in self.current_results:
                result_dict = {
                    'id': result.id,
                    'name': result.name,
                    'type': result.result_type.value,
                    'content': result.content,
                    'icon': result.icon,
                    'color': result.color,
                    'description': result.description,
                    'proyectos': result.proyectos,
                    'areas': result.areas,
                    'categoria': result.categoria,
                    'tabla': result.tabla,
                    'lista': result.lista,
                    'procesos': result.procesos,
                    'tags': result.tags,
                    'is_favorite': result.is_favorite,
                    'is_sensitive': result.is_sensitive,
                    'use_count': result.use_count,
                    'last_used': result.last_used,
                    'created_at': result.created_at,
                    'updated_at': result.updated_at
                }
                results_data.append(result_dict)

            # Crear estructura con metadata
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'total_results': len(self.current_results),
                    'query': self.search_input.text(),
                    'page': self.current_page,
                    'page_size': self.page_size
                },
                'results': results_data
            }

            # Escribir JSON
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"Se exportaron {len(self.current_results)} resultados a:\n{file_path}"
            )
            logger.info(f"Exported {len(self.current_results)} results to JSON: {file_path}")

        except Exception as e:
            logger.error(f"Error exportando a JSON: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar a JSON:\n{str(e)}")

    def copy_selected_batch(self):
        """Copia el contenido de los items seleccionados (acción en lote)"""
        # Reusar el método existente
        self.copy_selected_items()

    def mark_selected_as_favorite(self):
        """Marca los items seleccionados como favoritos (acción en lote)"""
        try:
            selected_ids = []

            # Obtener IDs de items seleccionados
            for row in range(self.results_table.rowCount()):
                cb_widget = self.results_table.cellWidget(row, 0)
                if cb_widget:
                    cb = cb_widget.findChild(QCheckBox)
                    if cb and cb.isChecked() and row < len(self.current_results):
                        result = self.current_results[row]
                        selected_ids.append(result.id)

            if not selected_ids:
                QMessageBox.information(self, "Marcar Favoritos", "No hay items seleccionados")
                return

            # Confirmar acción
            reply = QMessageBox.question(
                self,
                "Marcar Favoritos",
                f"¿Marcar {len(selected_ids)} items como favoritos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Marcar cada item como favorito
                for item_id in selected_ids:
                    self.db.update_item(item_id, is_favorite=True)

                logger.info(f"Marcados {len(selected_ids)} items como favoritos")
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Se marcaron {len(selected_ids)} items como favoritos"
                )

                # Refrescar vista
                self.perform_search()

        except Exception as e:
            logger.error(f"Error marcando favoritos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al marcar favoritos:\n{str(e)}")

    def delete_selected_batch(self):
        """Elimina los items seleccionados (acción en lote)"""
        try:
            selected_ids = []
            selected_names = []

            # Obtener IDs y nombres de items seleccionados
            for row in range(self.results_table.rowCount()):
                cb_widget = self.results_table.cellWidget(row, 0)
                if cb_widget:
                    cb = cb_widget.findChild(QCheckBox)
                    if cb and cb.isChecked() and row < len(self.current_results):
                        result = self.current_results[row]
                        selected_ids.append(result.id)
                        selected_names.append(result.name)

            if not selected_ids:
                QMessageBox.information(self, "Eliminar Items", "No hay items seleccionados")
                return

            # Confirmar eliminación
            names_preview = ", ".join(selected_names[:5])
            if len(selected_names) > 5:
                names_preview += f"... y {len(selected_names) - 5} más"

            reply = QMessageBox.question(
                self,
                "Confirmar Eliminación",
                f"¿Estás seguro de eliminar {len(selected_ids)} items?\n\n{names_preview}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Eliminar cada item
                deleted_count = 0
                for item_id in selected_ids:
                    try:
                        self.db.delete_item(item_id)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error eliminando item {item_id}: {e}")

                logger.info(f"Eliminados {deleted_count}/{len(selected_ids)} items")
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Se eliminaron {deleted_count} items correctamente"
                )

                # Refrescar vista
                self.perform_search()

        except Exception as e:
            logger.error(f"Error eliminando items: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al eliminar items:\n{str(e)}")

    def apply_styles(self):
        """Aplica estilos al diálogo"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }

            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
            }

            QPushButton {
                background-color: #3e3e42;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px 10px;
                border-radius: 3px;
            }

            QPushButton:hover {
                background-color: #4e4e52;
            }

            QPushButton:pressed {
                background-color: #2e2e32;
            }

            QPushButton:checked {
                background-color: #007acc;
                color: #ffffff;
            }

            QLineEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
            }

            QLineEdit:focus {
                border: 1px solid #007acc;
            }

            QTableWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                gridline-color: #3e3e42;
                border: 1px solid #3e3e42;
            }

            QTableWidget::item {
                padding: 5px;
            }

            QTableWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }

            QTableWidget::item:alternate {
                background-color: #252526;
            }

            QHeaderView::section {
                background-color: #2d2d30;
                color: #cccccc;
                padding: 5px;
                border: 1px solid #3e3e42;
                font-weight: bold;
            }

            QCheckBox {
                color: #cccccc;
                spacing: 5px;
            }

            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #3c3c3c;
            }

            QCheckBox::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }

            QScrollArea {
                border: none;
                background-color: transparent;
            }

            QScrollBar:vertical {
                background-color: #2d2d30;
                width: 12px;
            }

            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
        """)
