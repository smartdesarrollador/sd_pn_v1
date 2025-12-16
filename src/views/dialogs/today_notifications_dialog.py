"""
Today's Notifications Dialog
Shows events and alerts for the current day
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TodayNotificationsDialog(QDialog):
    """
    Dialog showing today's events and alerts
    Appears when clicking the notification badge
    """

    # Signal emitted when user wants to open full calendar
    open_calendar_requested = pyqtSignal()

    def __init__(self, events, alerts, parent=None):
        """
        Initialize dialog

        Args:
            events: List of today's events
            alerts: List of today's alerts
            parent: Parent widget
        """
        super().__init__(parent)
        self.events = events or []
        self.alerts = alerts or []

        self.setup_window()
        self.setup_ui()
        self.apply_styles()
        self.position_dialog()

    def setup_window(self):
        """Configure window properties"""
        self.setWindowTitle("Notificaciones de Hoy")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(500, 600)

        # Frameless window that stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

    def setup_ui(self):
        """Setup user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(10)

        # Summary
        total = len(self.events) + len(self.alerts)
        summary = QLabel(f"📅 {len(self.events)} eventos  •  🔔 {len(self.alerts)} alertas  •  Total: {total}")
        summary.setObjectName("summary")
        content_layout.addWidget(summary)

        # Events section
        if self.events:
            events_label = QLabel("📅 EVENTOS DE HOY")
            events_label.setObjectName("sectionTitle")
            content_layout.addWidget(events_label)

            for event in self.events:
                event_widget = self.create_event_widget(event)
                content_layout.addWidget(event_widget)

        # Alerts section
        if self.alerts:
            alerts_label = QLabel("🔔 ALERTAS DE HOY")
            alerts_label.setObjectName("sectionTitle")
            content_layout.addWidget(alerts_label)

            for alert in self.alerts:
                alert_widget = self.create_alert_widget(alert)
                content_layout.addWidget(alert_widget)

        # Empty state
        if not self.events and not self.alerts:
            empty_label = QLabel("✓ No hay eventos ni alertas programados para hoy")
            empty_label.setObjectName("emptyState")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(empty_label)

        content_layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Footer with button
        footer = self.create_footer()
        main_layout.addWidget(footer)

    def create_header(self):
        """Create header with title and close button"""
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(50)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(15, 0, 10, 0)

        # Title
        today = datetime.now()
        title = QLabel(f"📌 Hoy: {today.strftime('%d de %B, %Y')}")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return header

    def create_event_widget(self, event):
        """Create widget for a single event"""
        widget = QFrame()
        widget.setObjectName("itemWidget")
        widget.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Time and title
        time_str = event.get('event_datetime', '')[11:16] if event.get('event_datetime') else ''
        title_text = event.get('title') or event.get('item_label') or 'Sin título'
        title = QLabel(f"⏰ {time_str} - {title_text}")
        title.setObjectName("itemTitle")
        layout.addWidget(title)

        # Description
        description = event.get('description') or event.get('item_content')
        if description:
            desc = QLabel(description)
            desc.setObjectName("itemDesc")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        # Priority and status
        info_layout = QHBoxLayout()

        priority = event.get('priority', 'medium')
        priority_colors = {
            'high': '#ff5252',
            'medium': '#ffc107',
            'low': '#4caf50'
        }
        priority_text = {'high': 'Alta', 'medium': 'Media', 'low': 'Baja'}.get(priority, 'Media')

        priority_label = QLabel(f"🎯 {priority_text}")
        priority_label.setStyleSheet(f"color: {priority_colors.get(priority, '#ffc107')};")
        info_layout.addWidget(priority_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        return widget

    def create_alert_widget(self, alert):
        """Create widget for a single alert"""
        widget = QFrame()
        widget.setObjectName("itemWidget")
        widget.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Time and title
        time_str = alert.get('alert_datetime', '')[11:16] if alert.get('alert_datetime') else ''
        title_text = alert.get('alert_title') or alert.get('item_label') or 'Sin título'
        title = QLabel(f"⏰ {time_str} - {title_text}")
        title.setObjectName("itemTitle")
        layout.addWidget(title)

        # Message
        message = alert.get('alert_message') or alert.get('item_content')
        if message:
            msg = QLabel(message)
            msg.setObjectName("itemDesc")
            msg.setWordWrap(True)
            layout.addWidget(msg)

        # Priority
        info_layout = QHBoxLayout()

        priority = alert.get('priority', 'medium')
        priority_colors = {
            'high': '#ff5252',
            'medium': '#ffc107',
            'low': '#4caf50'
        }
        priority_text = {'high': 'Alta', 'medium': 'Media', 'low': 'Baja'}.get(priority, 'Media')

        priority_label = QLabel(f"🎯 {priority_text}")
        priority_label.setStyleSheet(f"color: {priority_colors.get(priority, '#ffc107')};")
        info_layout.addWidget(priority_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        return widget

    def create_footer(self):
        """Create footer with action button"""
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setFixedHeight(60)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(15, 10, 15, 10)

        # Open calendar button
        open_btn = QPushButton("📅 Abrir Calendario Completo")
        open_btn.setObjectName("actionButton")
        open_btn.clicked.connect(self.on_open_calendar)
        layout.addWidget(open_btn)

        return footer

    def on_open_calendar(self):
        """Handle open calendar button click"""
        self.open_calendar_requested.emit()
        self.close()

    def position_dialog(self):
        """Position dialog near the calendar button (top-right area)"""
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Position in top-right corner with some margin
        x = screen_geometry.right() - self.width() - 100
        y = screen_geometry.top() + 80

        self.move(x, y)

    def apply_styles(self):
        """Apply dark theme styles"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #007acc;
                border-radius: 8px;
            }

            #header {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3d3d3d;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            #header QLabel {
                color: #ffffff;
            }

            #closeButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                border-radius: 3px;
                font-size: 18pt;
                font-weight: bold;
            }

            #closeButton:hover {
                background-color: #e81123;
                color: #ffffff;
            }

            #summary {
                color: #cccccc;
                font-size: 10pt;
                padding: 5px;
                background-color: #1e1e1e;
                border-radius: 4px;
            }

            #sectionTitle {
                color: #007acc;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 0px 4px 0px;
            }

            #itemWidget {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin: 2px 0px;
            }

            #itemWidget:hover {
                background-color: #2d2d2d;
                border-color: #007acc;
            }

            #itemTitle {
                color: #ffffff;
                font-size: 10pt;
                font-weight: bold;
            }

            #itemDesc {
                color: #aaaaaa;
                font-size: 9pt;
            }

            #emptyState {
                color: #888888;
                font-size: 11pt;
                padding: 40px;
            }

            #footer {
                background-color: #1e1e1e;
                border-top: 1px solid #3d3d3d;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }

            #actionButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 10pt;
                font-weight: bold;
            }

            #actionButton:hover {
                background-color: #005a9e;
            }

            #actionButton:pressed {
                background-color: #004578;
            }

            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #007acc;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
