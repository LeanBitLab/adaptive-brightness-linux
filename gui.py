#!/usr/bin/env python3
"""
Adaptive Brightness GUI
A premium, dark-mode native desktop interface for adaptive-brightness-linux.
Built with PySide6 (Qt for Python).
"""

import os
import sys
import subprocess
import re
from datetime import datetime
import math

from PySide6.QtCore import (
    Qt, QTimer, QFileSystemWatcher, QTime, QPoint, QSize, QEvent, Slot
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QTabWidget, QLabel, QSlider, QSpinBox, QPushButton, 
    QTextEdit, QSystemTrayIcon, QMenu, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QIcon, QPainterPath, 
    QFont, QLinearGradient, QRadialGradient, QAction
)

# Base Paths
CONFIG_DIR = os.path.expanduser("~/.config/auto-brightness")
CONFIG_FILE = os.path.join(CONFIG_DIR, "profiles.conf")
STATE_FILE = os.path.expanduser("~/.local/state/auto-brightness.state")
LOG_FILE = os.path.expanduser("~/.local/state/auto-brightness.log")
SCRIPT_PATH = os.path.expanduser("~/.local/bin/auto-brightness.sh")

# Premium Slate-Dark stylesheet (QSS)
QSS = """
QMainWindow {
    background-color: #0f172a;
}
QWidget {
    color: #f1f5f9;
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 13px;
}
QTabWidget::panel {
    border: 1px solid #334155;
    background-color: #1e293b;
    border-radius: 12px;
}
QTabBar::tab {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-bottom: none;
    padding: 8px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    color: #94a3b8;
    font-weight: 600;
}
QTabBar::tab:selected, QTabBar::tab:hover {
    background-color: #1e293b;
    color: #3b82f6;
    border-color: #3b82f6;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #475569;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QFrame.Card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
}
QLabel.Title {
    font-size: 20px;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 4px;
}
QLabel.Subtitle {
    font-size: 12px;
    color: #64748b;
}
QLabel.HeaderLabel {
    font-size: 14px;
    font-weight: 700;
    color: #3b82f6;
}
QLabel.ValueLabel {
    font-size: 28px;
    font-weight: 900;
    color: #f1f5f9;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3b82f6;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #475569;
    color: #94a3b8;
}
QPushButton.Secondary {
    background-color: #334155;
    border: 1px solid #475569;
    color: #cbd5e1;
}
QPushButton.Secondary:hover {
    background-color: #475569;
}
QPushButton.Danger {
    background-color: #dc2626;
}
QPushButton.Danger:hover {
    background-color: #ef4444;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #334155;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #3b82f6;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #3b82f6;
}
QSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 8px;
    color: #f1f5f9;
    font-weight: 600;
}
QSpinBox:hover {
    border-color: #3b82f6;
}
QTextEdit.LogBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
"""

def create_sun_icon(size=32):
    """Generates a premium sun vector icon using QPainter."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    center = size / 2.0
    r_core = size * 0.20
    
    # Outer glow
    glow = QRadialGradient(center, center, size * 0.45)
    glow.setColorAt(0.0, QColor(234, 179, 8, 80)) # glowing yellow
    glow.setColorAt(0.6, QColor(234, 179, 8, 20))
    glow.setColorAt(1.0, QColor(234, 179, 8, 0))
    painter.setBrush(QBrush(glow))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    
    # Sun Core
    painter.setBrush(QColor("#eab308"))  # Premium Gold/Yellow
    painter.drawEllipse(QPoint(center, center), r_core, r_core)
    
    # Sun Rays
    pen = QPen(QColor("#eab308"), max(1.5, size * 0.05))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    
    num_rays = 8
    r_start = size * 0.28
    r_end = size * 0.38
    for i in range(num_rays):
        angle = (i * 2 * math.pi) / num_rays
        x1 = center + r_start * math.cos(angle)
        y1 = center + r_start * math.sin(angle)
        x2 = center + r_end * math.cos(angle)
        y2 = center + r_end * math.sin(angle)
        painter.drawLine(QPoint(x1, y1), QPoint(x2, y2))
        
    painter.end()
    return QIcon(pixmap)


class ProfileCurveWidget(QWidget):
    """
    Custom widget to display a beautiful spline of the 24-hour brightness profile
    with anti-aliasing, linear gradients, and a current-time indicator.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data = {}  # dict of time_val (int minutes) -> brightness_pct
        self.current_time_val = 0  # int minutes from midnight
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
    def set_profile_data(self, data):
        # Data format: dict of {"0830": 45, "1200": 80, ...}
        # Convert to dictionary of minutes from midnight -> value
        self.profile_data = {}
        for time_str, val in data.items():
            try:
                h = int(time_str[:2])
                m = int(time_str[2:])
                minutes = h * 60 + m
                self.profile_data[minutes] = val
            except Exception:
                pass
        self.update()
        
    def set_current_time(self, time_val):
        self.current_time_val = time_val
        self.update()
        
    def get_interpolated_value(self, minutes):
        """Calculates brightness target for any arbitrary minute using profile config step logic."""
        if not self.profile_data:
            return 15 # default fallback
        
        # Sort key times
        sorted_times = sorted(self.profile_data.keys())
        
        # Mimic the auto-brightness.sh search logic
        target_val = 15
        for t in sorted_times:
            if minutes >= t:
                target_val = self.profile_data[t]
        return target_val

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Set margins
        margin_left = 40
        margin_right = 20
        margin_top = 20
        margin_bottom = 25
        
        graph_w = width - margin_left - margin_right
        graph_h = height - margin_top - margin_bottom
        
        # 1. Background grid & labels
        painter.setPen(QPen(QColor("#1e293b"), 1, Qt.DashLine))
        font = QFont(self.font())
        font.setPointSize(9)
        painter.setFont(font)
        
        # Draw Y Grid & Labels (0%, 20%, 40%, 60%, 80%, 100%)
        for i in range(6):
            pct = i * 20
            y = margin_top + graph_h - (pct / 100.0 * graph_h)
            painter.drawLine(margin_left, y, width - margin_right, y)
            
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(5, y + 4, f"{pct}%")
            painter.setPen(QPen(QColor("#1e293b"), 1, Qt.DashLine))
            
        # Draw X Grid & Labels (Time intervals every 4 hours)
        for h in range(0, 25, 4):
            minutes = h * 60
            x = margin_left + (minutes / 1440.0 * graph_w)
            painter.drawLine(x, margin_top, x, height - margin_bottom)
            
            painter.setPen(QColor("#94a3b8"))
            time_label = f"{h:02d}:00"
            painter.drawText(x - 15, height - 8, time_label)
            painter.setPen(QPen(QColor("#1e293b"), 1, Qt.DashLine))
            
        # 2. Draw Profile Line and Gradient
        if not self.profile_data:
            painter.end()
            return
            
        # Create continuous path plotting every minute
        path = QPainterPath()
        started = False
        
        for m in range(0, 1441, 5):  # Sample every 5 minutes for performance
            val = self.get_interpolated_value(m)
            x = margin_left + (m / 1440.0 * graph_w)
            y = margin_top + graph_h - (val / 100.0 * graph_h)
            
            if not started:
                path.moveTo(x, y)
                started = True
            else:
                path.lineTo(x, y)
                
        # Close path at the end
        val_end = self.get_interpolated_value(1439)
        x_end = margin_left + graph_w
        y_end = margin_top + graph_h - (val_end / 100.0 * graph_h)
        path.lineTo(x_end, y_end)
        
        # Fill gradient under curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(x_end, margin_top + graph_h)
        fill_path.lineTo(margin_left, margin_top + graph_h)
        fill_path.close()
        
        gradient = QLinearGradient(0, margin_top, 0, margin_top + graph_h)
        gradient.setColorAt(0.0, QColor(59, 130, 246, 120))  # Slate Blue glow
        gradient.setColorAt(0.8, QColor(59, 130, 246, 20))
        gradient.setColorAt(1.0, QColor(59, 130, 246, 0))
        
        painter.fillPath(fill_path, QBrush(gradient))
        
        # Draw the curve line
        painter.setPen(QPen(QColor("#3b82f6"), 3, Qt.SolidLine))
        painter.drawPath(path)
        
        # 3. Current Time Indicator Marker
        current_val = self.get_interpolated_value(self.current_time_val)
        cur_x = margin_left + (self.current_time_val / 1440.0 * graph_w)
        cur_y = margin_top + graph_h - (current_val / 100.0 * graph_h)
        
        # Glow ring
        painter.setBrush(QColor(96, 165, 250, 80)) # Neon blue translucent
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(cur_x, cur_y), 9, 9)
        
        # Pulse Center
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#3b82f6"), 2))
        painter.drawEllipse(QPoint(cur_x, cur_y), 4, 4)
        
        painter.end()


class BrightnessGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Brightness Control")
        self.resize(750, 600)
        self.setStyleSheet(QSS)
        self.setWindowIcon(create_sun_icon(64))
        
        self.profiles = {}  # dict {"0600": 20, ...}
        self.current_brightness = 50
        
        # Create core widgets
        self.curve_widget = ProfileCurveWidget()
        
        # File Watcher for auto-updating logs
        self.watcher = QFileSystemWatcher(self)
        if os.path.exists(LOG_FILE):
            self.watcher.addPath(LOG_FILE)
        self.watcher.fileChanged.connect(self.load_logs)
        
        # Build UI layout
        self.setup_ui()
        
        # Initial Load
        self.load_profile_config()
        self.update_status()
        
        # Timer to tick system status every 10 seconds
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(10000) # 10 seconds
        
    def setup_ui(self):
        # Central widget container
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # HEADER BAR
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        
        title_label = QLabel("Adaptive Brightness")
        title_label.setObjectName("title_label")
        title_label.setProperty("class", "Title")
        
        subtitle_label = QLabel("Dynamic Time-of-Day Adaptive Backlight Controller")
        subtitle_label.setProperty("class", "Subtitle")
        
        header_text_layout.addWidget(title_label)
        header_text_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()
        
        # Dynamic active indicator
        self.active_badge = QLabel("TIMER ACTIVE")
        self.active_badge.setStyleSheet(
            "background-color: #065f46; color: #34d399; font-weight: 800; "
            "padding: 6px 12px; border-radius: 12px; font-size: 11px;"
        )
        header_layout.addWidget(self.active_badge)
        main_layout.addLayout(header_layout)
        
        # TAB CONTAINER
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Dashboard
        self.tab_dashboard = QWidget()
        self.setup_dashboard_tab()
        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        
        # Tab 2: Profile Editor
        self.tab_profile = QWidget()
        self.setup_profile_tab()
        self.tabs.addTab(self.tab_profile, "Profile Editor")
        
        # Tab 3: Logs
        self.tab_logs = QWidget()
        self.setup_logs_tab()
        self.tabs.addTab(self.tab_logs, "Activity Logs")
        
        # SYSTEM TRAY SETUP
        self.setup_system_tray()
        
    def setup_dashboard_tab(self):
        layout = QHBoxLayout(self.tab_dashboard)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Left Panel: Info Cards
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)
        
        # Card 1: Current Brightness Status
        card_bright = QFrame()
        card_bright.setProperty("class", "Card")
        cb_layout = QGridLayout(card_bright)
        cb_layout.setContentsMargins(16, 16, 16, 16)
        
        l1 = QLabel("Current Level")
        l1.setProperty("class", "HeaderLabel")
        self.lbl_current_brightness = QLabel("--%")
        self.lbl_current_brightness.setProperty("class", "ValueLabel")
        
        cb_layout.addWidget(l1, 0, 0)
        cb_layout.addWidget(self.lbl_current_brightness, 1, 0)
        left_panel.addWidget(card_bright)
        
        # Card 2: Current Active Target / Profile block
        card_profile = QFrame()
        card_profile.setProperty("class", "Card")
        cp_layout = QGridLayout(card_profile)
        cp_layout.setContentsMargins(16, 16, 16, 16)
        
        l2 = QLabel("Active Time Block")
        l2.setProperty("class", "HeaderLabel")
        self.lbl_active_block = QLabel("----")
        self.lbl_active_block.setProperty("class", "ValueLabel")
        self.lbl_profile_target = QLabel("Target: --%")
        self.lbl_profile_target.setStyleSheet("color: #94a3b8; font-weight: 600;")
        
        cp_layout.addWidget(l2, 0, 0)
        cp_layout.addWidget(self.lbl_active_block, 1, 0)
        cp_layout.addWidget(self.lbl_profile_target, 2, 0)
        left_panel.addWidget(card_profile)
        
        # Card 3: Daemon Control
        card_daemon = QFrame()
        card_daemon.setProperty("class", "Card")
        cd_layout = QVBoxLayout(card_daemon)
        cd_layout.setContentsMargins(16, 16, 16, 16)
        cd_layout.setSpacing(12)
        
        l3 = QLabel("Service Controls")
        l3.setProperty("class", "HeaderLabel")
        cd_layout.addWidget(l3)
        
        btn_layout = QHBoxLayout()
        self.btn_daemon_toggle = QPushButton("Disable Timer")
        self.btn_daemon_toggle.clicked.connect(self.toggle_daemon)
        
        self.btn_run_script = QPushButton("Adjust Now")
        self.btn_run_script.setProperty("class", "Secondary")
        self.btn_run_script.clicked.connect(self.trigger_script_adjust)
        
        btn_layout.addWidget(self.btn_daemon_toggle)
        btn_layout.addWidget(self.btn_run_script)
        cd_layout.addLayout(btn_layout)
        left_panel.addWidget(card_daemon)
        
        layout.addLayout(left_panel, 2)
        
        # Right Panel: Live Visualizer & Manual Override
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)
        
        # Visualizer
        vis_frame = QFrame()
        vis_frame.setProperty("class", "Card")
        vf_layout = QVBoxLayout(vis_frame)
        vf_layout.setContentsMargins(12, 12, 12, 12)
        
        vl = QLabel("Adaptive Brightness Profile Path")
        vl.setProperty("class", "HeaderLabel")
        vf_layout.addWidget(vl)
        vf_layout.addWidget(self.curve_widget)
        right_panel.addWidget(vis_frame, 3)
        
        # Manual Override Slider
        override_frame = QFrame()
        override_frame.setProperty("class", "Card")
        of_layout = QVBoxLayout(override_frame)
        of_layout.setContentsMargins(16, 16, 16, 16)
        
        ol = QLabel("Manual Override Slider")
        ol.setProperty("class", "HeaderLabel")
        of_layout.addWidget(ol)
        
        os_layout = QHBoxLayout()
        self.slider_override = QSlider(Qt.Horizontal)
        self.slider_override.setRange(5, 100)
        self.slider_override.setValue(50)
        
        self.spin_override = QSpinBox()
        self.spin_override.setRange(5, 100)
        self.spin_override.setValue(50)
        self.spin_override.setSuffix("%")
        
        self.slider_override.valueChanged.connect(self.spin_override.setValue)
        self.spin_override.valueChanged.connect(self.slider_override.setValue)
        self.slider_override.sliderReleased.connect(self.apply_manual_override)
        self.spin_override.editingFinished.connect(self.apply_manual_override)
        
        os_layout.addWidget(self.slider_override, 4)
        os_layout.addWidget(self.spin_override, 1)
        of_layout.addLayout(os_layout)
        
        # Learn preferences checklist
        self.lbl_learning_note = QLabel(
            "ℹ️ Moving the slider simulates a manual override. "
            "If within 20 mins, the algorithm learns this as your preferred brightness!"
        )
        self.lbl_learning_note.setStyleSheet("color: #eab308; font-size: 11px; font-weight: 500;")
        of_layout.addWidget(self.lbl_learning_note)
        
        right_panel.addWidget(override_frame, 2)
        layout.addLayout(right_panel, 3)

    def setup_profile_tab(self):
        tab_layout = QVBoxLayout(self.tab_profile)
        tab_layout.setContentsMargins(16, 16, 16, 16)
        tab_layout.setSpacing(12)
        
        lbl_info = QLabel("Customize Target Brightness for Time Blocks")
        lbl_info.setProperty("class", "HeaderLabel")
        tab_layout.addWidget(lbl_info)
        
        # Scroll Area for sliders
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.profile_grid = QGridLayout(scroll_content)
        self.profile_grid.setContentsMargins(12, 12, 12, 12)
        self.profile_grid.setSpacing(16)
        
        scroll.setWidget(scroll_content)
        tab_layout.addWidget(scroll)
        
        # Actions button bar
        action_layout = QHBoxLayout()
        
        self.btn_reset_profile = QPushButton("Reload Profile")
        self.btn_reset_profile.setProperty("class", "Secondary")
        self.btn_reset_profile.clicked.connect(self.load_profile_config)
        
        self.btn_save_profile = QPushButton("Save Profiles")
        self.btn_save_profile.clicked.connect(self.save_profile_config)
        
        action_layout.addWidget(self.btn_reset_profile)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_save_profile)
        tab_layout.addLayout(action_layout)
        
        self.profile_widgets = {}  # dict time -> (slider, spin)
        
    def setup_logs_tab(self):
        layout = QVBoxLayout(self.tab_logs)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header = QHBoxLayout()
        lbl_logs = QLabel("Real-time Service Operation Logs")
        lbl_logs.setProperty("class", "HeaderLabel")
        
        btn_clear = QPushButton("Clear Logs")
        btn_clear.setProperty("class", "Secondary")
        btn_clear.clicked.connect(self.clear_logs)
        
        header.addWidget(lbl_logs)
        header.addStretch()
        header.addWidget(btn_clear)
        layout.addLayout(header)
        
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setProperty("class", "LogBox")
        layout.addWidget(self.txt_logs)
        
        self.load_logs()
        
    def setup_system_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(create_sun_icon(32))
        self.tray.setToolTip("Adaptive Brightness Control")
        
        tray_menu = QMenu()
        
        act_open = QAction("Open Control Panel", self)
        act_open.triggered.connect(self.show_normal)
        tray_menu.addAction(act_open)
        
        act_adjust = QAction("Force Adjust Brightness", self)
        act_adjust.triggered.connect(self.trigger_script_adjust)
        tray_menu.addAction(act_adjust)
        
        tray_menu.addSeparator()
        
        act_quit = QAction("Exit App", self)
        act_quit.triggered.connect(self.quit_app)
        tray_menu.addAction(act_quit)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()
            
    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Intercept close event to minimize to system tray."""
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "Adaptive Brightness",
                "GUI minimized to system tray. Access it from the taskbar icon.",
                QSystemTrayIcon.Information,
                3000
            )
            event.ignore()
        else:
            event.accept()
            
    def quit_app(self):
        self.tray.hide()
        QApplication.quit()

    # --- Profile parsing and saving ---
    def load_profile_config(self):
        """Loads and parses the profile configuration file."""
        if not os.path.exists(CONFIG_FILE):
            return
            
        profiles = {}
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^(\d{4})=(\d+)", line)
                if match:
                    profiles[match.group(1)] = int(match.group(2))
                    
        self.profiles = profiles
        self.curve_widget.set_profile_data(profiles)
        self.rebuild_profile_editor()
        
    def rebuild_profile_editor(self):
        """Fills the Profile Editor tab with neat sliders."""
        # Clear old items
        for i in reversed(range(self.profile_grid.count())):
            self.profile_grid.itemAt(i).widget().setParent(None)
            
        self.profile_widgets = {}
        
        # Sort profile keys
        sorted_times = sorted(self.profiles.keys())
        
        row = 0
        for t in sorted_times:
            # Format time beautifully e.g. "0830" -> "08:30"
            formatted_time = f"{t[:2]}:{t[2:]}"
            
            lbl_time = QLabel(formatted_time)
            lbl_time.setStyleSheet("font-weight: 700; font-size: 14px; color: #f1f5f9;")
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(5, 100)
            slider.setValue(self.profiles[t])
            slider.setFixedHeight(24)
            
            spin = QSpinBox()
            spin.setRange(5, 100)
            spin.setValue(self.profiles[t])
            spin.setSuffix("%")
            spin.setFixedWidth(70)
            
            # Tie them together
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            
            self.profile_grid.addWidget(lbl_time, row, 0)
            self.profile_grid.addWidget(slider, row, 1)
            self.profile_grid.addWidget(spin, row, 2)
            
            self.profile_widgets[t] = (slider, spin)
            row += 1
            
    def save_profile_config(self):
        """Saves current state of GUI sliders back to config file, preserving comments."""
        if not os.path.exists(CONFIG_FILE):
            return
            
        # Collect new values
        new_values = {}
        for t, (slider, _) in self.profile_widgets.items():
            new_values[t] = slider.value()
            
        # Update profiles dict and curve
        self.profiles.update(new_values)
        self.curve_widget.set_profile_data(self.profiles)
        
        # Rewrite the config file preserving comments
        lines = []
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    lines.append(line)
                    continue
                match = re.match(r"^(\d{4})=(\d+)", stripped)
                if match:
                    t = match.group(1)
                    if t in new_values:
                        lines.append(f"{t}={new_values[t]}\n")
                    else:
                        lines.append(line)
                else:
                    lines.append(line)
                    
        with open(CONFIG_FILE, "w") as f:
            f.writelines(lines)
            
        # Trigger background daemon adjustment instantly
        self.trigger_script_adjust()

    # --- System operation methods ---
    def update_status(self):
        """Reads hardware backlight and systemd state to update GUI."""
        # 1. Check systemd timer
        timer_active = False
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-active", "auto-brightness.timer"],
                capture_output=True, text=True
            )
            timer_active = (res.stdout.strip() == "active")
        except Exception:
            pass
            
        if timer_active:
            self.active_badge.setText("TIMER ACTIVE")
            self.active_badge.setStyleSheet(
                "background-color: #065f46; color: #34d399; font-weight: 800; "
                "padding: 6px 12px; border-radius: 12px; font-size: 11px;"
            )
            self.btn_daemon_toggle.setText("Disable Timer")
            self.btn_daemon_toggle.setProperty("class", "Secondary")
        else:
            self.active_badge.setText("TIMER DISABLED")
            self.active_badge.setStyleSheet(
                "background-color: #991b1b; color: #fca5a5; font-weight: 800; "
                "padding: 6px 12px; border-radius: 12px; font-size: 11px;"
            )
            self.btn_daemon_toggle.setText("Enable Timer")
            self.btn_daemon_toggle.setProperty("class", "Primary")
            
        self.btn_daemon_toggle.style().unpolish(self.btn_daemon_toggle)
        self.btn_daemon_toggle.style().polish(self.btn_daemon_toggle)
        
        # 2. Get current hardware brightness percentage
        try:
            res = subprocess.run(["brightnessctl", "-m"], capture_output=True, text=True)
            if res.returncode == 0:
                fields = res.stdout.strip().split(",")
                if len(fields) >= 4:
                    pct_str = fields[3].replace("%", "")
                    self.current_brightness = int(pct_str)
                    self.lbl_current_brightness.setText(f"{self.current_brightness}%")
                    
                    # Block signals briefly to avoid triggering a feedback manual loop
                    self.slider_override.blockSignals(True)
                    self.spin_override.blockSignals(True)
                    self.slider_override.setValue(self.current_brightness)
                    self.spin_override.setValue(self.current_brightness)
                    self.slider_override.blockSignals(False)
                    self.spin_override.blockSignals(False)
        except Exception:
            pass
            
        # 3. Get active target and active block
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        self.curve_widget.set_current_time(cur_min)
        
        # Find active block
        sorted_times = sorted(self.profiles.keys())
        active_time_str = "0000"
        target_val = 15
        
        for t in sorted_times:
            try:
                h = int(t[:2])
                m = int(t[2:])
                min_val = h * 60 + m
                if cur_min >= min_val:
                    active_time_str = t
                    target_val = self.profiles[t]
            except Exception:
                pass
                
        self.lbl_active_block.setText(f"{active_time_str[:2]}:{active_time_str[2:]}")
        self.lbl_profile_target.setText(f"Target: {target_val}%")
        
    def toggle_daemon(self):
        """Enables or disables the auto-brightness systemd timer."""
        is_active = (self.active_badge.text() == "TIMER ACTIVE")
        action = "stop" if is_active else "start"
        enable_action = "disable" if is_active else "enable"
        
        try:
            # Change systemd state
            subprocess.run(["systemctl", "--user", enable_action, "auto-brightness.timer"])
            subprocess.run(["systemctl", "--user", action, "auto-brightness.timer"])
        except Exception as e:
            print(f"Error toggling systemd service: {e}")
            
        self.update_status()
        
    def trigger_script_adjust(self):
        """Forces manual execution of background brightness adjuster."""
        if os.path.exists(SCRIPT_PATH):
            subprocess.Popen(["bash", SCRIPT_PATH])
            # Delay status update by 250ms to let script run and write state
            QTimer.singleShot(250, self.update_status)
            
    def apply_manual_override(self):
        """Applies custom override to laptop backlight immediately via script state trigger."""
        val = self.slider_override.value()
        
        # 1. Update state file to make script treat it as recent
        now_epoch = int(datetime.now().timestamp())
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                f.write(f"{val} {now_epoch}\n")
        except Exception:
            pass
            
        # 2. Write to system brightness directly
        try:
            # Try to run auto-brightness.sh which handles learning boundaries and D-Bus sync!
            if os.path.exists(SCRIPT_PATH):
                # Call brightnessctl first to apply immediately
                subprocess.run(["brightnessctl", "-q", "set", f"{val}%"])
                # Then trigger the script so it immediately detects the manual change and learns it!
                subprocess.Popen(["bash", SCRIPT_PATH])
        except Exception:
            # Fallback direct
            subprocess.run(["brightnessctl", "-q", "set", f"{val}%"])
            
        QTimer.singleShot(250, self.update_status)

    # --- Logs management ---
    @Slot(str)
    def load_logs(self):
        """Loads operational logs and formats with elegant HTML styling."""
        if not os.path.exists(LOG_FILE):
            self.txt_logs.setHtml("<span style='color: #64748b;'>No operation log files found yet.</span>")
            return
            
        try:
            with open(LOG_FILE, "r") as f:
                # Read last 80 lines for safety
                lines = f.readlines()[-80:]
                
            formatted_html = []
            for line in lines:
                line_str = line.strip()
                if "Learned new manual preference" in line_str:
                    colorized = f"<span style='color: #10b981; font-weight: bold;'>{line_str}</span>"
                elif "Laptop:" in line_str:
                    colorized = f"<span style='color: #3b82f6;'>{line_str}</span>"
                else:
                    colorized = f"<span style='color: #94a3b8;'>{line_str}</span>"
                formatted_html.append(colorized)
                
            self.txt_logs.setHtml("<br>".join(formatted_html))
            
            # Scroll to bottom
            scrollbar = self.txt_logs.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self.txt_logs.setHtml(f"<span style='color: #ef4444;'>Failed reading logs: {e}</span>")
            
    def clear_logs(self):
        """Truncates log file."""
        try:
            with open(LOG_FILE, "w") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Log cleared from Control Panel.\n")
        except Exception:
            pass
        self.load_logs()


def main():
    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
    
    gui = BrightnessGUI()
    gui.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
