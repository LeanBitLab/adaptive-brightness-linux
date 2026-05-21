#!/usr/bin/env python3
"""
Adaptive Brightness GUI
A premium, Nothing OS monochrome signature desktop interface for adaptive-brightness-linux.
Built with PySide6 (Qt for Python).
"""

import os
import sys
import subprocess
import re
from datetime import datetime
import math

from PySide6.QtCore import (
    Qt, QTimer, QFileSystemWatcher, QTime, QPoint, QSize, QEvent, Slot, QRect
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QTabWidget, QLabel, QSlider, QSpinBox, QPushButton, 
    QTextEdit, QSystemTrayIcon, QMenu, QScrollArea, QFrame, QSizePolicy, QCheckBox,
    QComboBox, QProxyStyle, QStyle, QStyledItemDelegate, QTimeEdit
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
PAUSE_FILE = os.path.expanduser("~/.local/state/auto-brightness.paused")

# Premium dark theme with warm amber accent
QSS = """
QMainWindow {
    background-color: #0d0d14;
}
QWidget {
    color: #ececee;
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 14px;
}
QTabWidget::pane {
    border: 1px solid #28283a;
    background-color: #16161e;
    border-radius: 12px;
    top: -1px;
}
#tab_dashboard, #tab_profile, #tab_logs {
    background-color: #16161e;
}
QTabBar::tab {
    background-color: #0d0d14;
    border: 1px solid #28283a;
    border-bottom: none;
    padding: 10px 20px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 4px;
    color: #88889a;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
}
QTabBar::tab:selected {
    background-color: #16161e;
    color: #ececee;
    border-color: #28283a;
    border-bottom-color: #16161e;
    margin-bottom: -2px;
    padding-bottom: 12px;
}
QTabBar::tab:hover:!selected {
    background-color: #1e1e2a;
    color: #ececee;
    border-color: #3a3a4e;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: #0d0d14;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #28283a;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #f0a820;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QFrame[class="Card"] {
    background-color: #16161e;
    border: 1px solid #28283a;
    border-radius: 14px;
}
QFrame[class="Card"]:hover {
    border-color: #3a3a4e;
}
QFrame[class="CardElevated"] {
    background-color: #1e1e2a;
    border: 1px solid #28283a;
    border-radius: 14px;
}
QComboBox {
    background-color: #16161e;
    color: #ececee;
    border: 2px solid #28283a;
    border-radius: 10px;
    padding: 8px 14px;
    padding-right: 36px;
    font-weight: 600;
    font-size: 14px;
    min-width: 180px;
}
QComboBox:hover {
    border-color: #f0a820;
    background-color: #1e1e2a;
}
QComboBox:focus, QComboBox:on {
    border-color: #f0a820;
    background-color: #1e1e2a;
}
QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 36px;
}
QComboBox::down-arrow {
    image: url('/home/arjun/.config/auto-brightness/down_arrow.svg');
    width: 18px;
    height: 18px;
    margin-right: 4px;
}
QComboBox QAbstractItemView, QComboBox QListView {
    background-color: #28283a;
    color: #ececee;
    border: 2px solid #3a3a4e;
    border-radius: 10px;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 8px 14px;
    border-radius: 8px;
    color: #ececee;
    background-color: transparent;
}
QComboBox QAbstractItemView::item:hover {
    background-color: rgba(240, 168, 32, 0.15);
    color: #f0a820;
}
QComboBox QAbstractItemView::item:selected {
    background-color: rgba(240, 168, 32, 0.15);
    color: #f0a820;
}
QLabel[class="Title"] {
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 24px;
    font-weight: 900;
    color: #ececee;
    background-color: #16161e;
    border: 1px solid #28283a;
    border-radius: 8px;
    padding: 4px 12px;
    letter-spacing: 1px;
}
QLabel[class="Subtitle"] {
    font-size: 14px;
    color: #88889a;
}
QLabel[class="HeaderLabel"] {
    font-size: 12px;
    font-weight: 700;
    color: #88889a;
    text-transform: uppercase;
    letter-spacing: 2px;
}
QLabel[class="ValueLabel"] {
    font-size: 32px;
    font-weight: 900;
    color: #ececee;
}
QLabel[class="InfoNote"] {
    color: #5c5c6e;
    font-size: 12px;
    font-weight: 500;
}
QPushButton {
    background-color: #f0a820;
    color: #0d0d14;
    border: none;
    padding: 10px 24px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #f2b840;
}
QPushButton:pressed {
    background-color: #d4921a;
}
QPushButton:disabled {
    background-color: #16161e;
    color: #5c5c6e;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #28283a;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #f0a820;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ececee;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #f0a820;
}
QSpinBox {
    background-color: #0d0d14;
    border: 1px solid #28283a;
    border-radius: 10px;
    padding: 6px 12px;
    color: #ececee;
    font-weight: 700;
}
QSpinBox:hover {
    border-color: #f0a820;
}
QCheckBox {
    color: #ececee;
    font-weight: 600;
    spacing: 8px;
}
#chk_ambient, #chk_autostart, #chk_autostart_minimized {
    color: #88889a;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #28283a;
    border-radius: 4px;
    background-color: #0d0d14;
}
QCheckBox::indicator:hover {
    border-color: #f0a820;
}
QCheckBox::indicator:checked {
    background-color: #f0a820;
    border-color: #f0a820;
    image: url('/home/arjun/.config/auto-brightness/checkbox_check.svg');
}
QTextEdit[class="LogBox"] {
    background-color: #0d0d14;
    border: 1px solid #28283a;
    border-radius: 10px;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QToolTip {
    background-color: #16161e;
    color: #ececee;
    border: 1px solid #28283a;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 500;
    max-width: 350px;
}
"""

BTN_SECONDARY = (
    "QPushButton { background-color: transparent; border: 1px solid #28283a; color: #ececee; "
    "padding: 10px 24px; border-radius: 10px; font-weight: 700; font-size: 13px; }"
    "QPushButton:hover { background-color: rgba(240, 168, 32, 0.1); border-color: #f0a820; }"
    "QPushButton:pressed { background-color: rgba(240, 168, 32, 0.2); }"
    "QPushButton:disabled { background-color: transparent; border-color: #28283a; color: #5c5c6e; }"
)

BTN_DANGER = (
    "QPushButton { background-color: transparent; border: 1px solid #e84848; color: #e84848; "
    "padding: 10px 24px; border-radius: 10px; font-weight: 700; font-size: 13px; }"
    "QPushButton:hover { background-color: rgba(232, 72, 72, 0.15); }"
    "QPushButton:pressed { background-color: rgba(232, 72, 72, 0.25); }"
)

BTN_DANGER_ICON = (
    "QPushButton { background-color: transparent; border: 1px solid #e84848; color: #e84848; "
    "padding: 0px; border-radius: 8px; font-weight: 700; font-size: 14px; }"
    "QPushButton:hover { background-color: rgba(232, 72, 72, 0.15); }"
    "QPushButton:pressed { background-color: rgba(232, 72, 72, 0.25); }"
)

BTN_PRIMARY = (
    "QPushButton { background-color: #f0a820; color: #0d0d14; border: none; "
    "padding: 10px 24px; border-radius: 10px; font-weight: 700; font-size: 13px; }"
    "QPushButton:hover { background-color: #f2b840; }"
    "QPushButton:pressed { background-color: #d4921a; }"
    "QPushButton:disabled { background-color: #16161e; color: #5c5c6e; }"
)

def style_secondary(btn):
    btn.setStyleSheet(BTN_SECONDARY)

def style_danger(btn):
    btn.setStyleSheet(BTN_DANGER)

def style_danger_icon(btn):
    btn.setStyleSheet(BTN_DANGER_ICON)

def style_primary(btn):
    btn.setStyleSheet(BTN_PRIMARY)

def create_sun_icon(size=32):
    """Generates a brightness-themed sun/rays icon using QPainter."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    center = size / 2.0
    r_core = size * 0.16
    r_ray_inner = size * 0.26
    r_ray_outer = size * 0.40
    
    # Draw 8 rays
    painter.setPen(QPen(QColor("#ffffff"), 1.5, Qt.SolidLine, Qt.RoundCap))
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = center + r_ray_inner * math.cos(angle)
        y1 = center - r_ray_inner * math.sin(angle)
        x2 = center + r_ray_outer * math.cos(angle)
        y2 = center - r_ray_outer * math.sin(angle)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    # Sun core - warm amber accent
    painter.setBrush(QColor("#f0a820"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPoint(int(center), int(center)), int(r_core), int(r_core))
    
    painter.end()
    return QIcon(pixmap)


def get_backlight_devices():
    """Scans and retrieves active backlight/display device names."""
    devices = []
    # 1. Try kscreen-doctor first (perfect for KDE)
    try:
        res = subprocess.run(["kscreen-doctor", "-o"], capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                # Clean ANSI escape sequences
                clean_line = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line).strip()
                if clean_line.startswith("Output:"):
                    parts = clean_line.split()
                    if len(parts) >= 3:
                        devices.append(parts[2])
    except Exception:
        pass

    # 2. Try sysfs /sys/class/backlight fallback if empty
    if not devices:
        try:
            if os.path.exists("/sys/class/backlight"):
                devices = sorted(os.listdir("/sys/class/backlight"))
        except Exception:
            pass

    if not devices:
        devices = ["default"]
    return devices


def get_device_brightness(dev):
    """Retrieves current brightness percentage for display using kscreen-doctor or brightnessctl."""
    # 1. Try kscreen-doctor first
    try:
        res = subprocess.run(["kscreen-doctor", "-o"], capture_output=True, text=True)
        if res.returncode == 0:
            current_dev = None
            for line in res.stdout.splitlines():
                clean_line = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line).strip()
                if clean_line.startswith("Output:"):
                    parts = clean_line.split()
                    if len(parts) >= 3:
                        current_dev = parts[2]
                elif current_dev == dev and "Brightness control:" in clean_line:
                    match = re.search(r"set to (\d+)%", clean_line)
                    if match:
                        return int(match.group(1))
    except Exception:
        pass

    # 2. Try brightnessctl fallback
    try:
        if dev == "default":
            res = subprocess.run(["brightnessctl", "-m"], capture_output=True, text=True)
        else:
            res = subprocess.run(["brightnessctl", "-d", dev, "-m"], capture_output=True, text=True)
        if res.returncode == 0:
            fields = res.stdout.strip().split(",")
            if len(fields) >= 4:
                pct_str = fields[3].replace("%", "")
                return int(pct_str)
    except Exception:
        pass
    return None


class NoWheelSlider(QSlider):
    """QSlider that ignores mouse wheel events to prevent accidental changes when scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class CircularBrightnessDisplay(QWidget):
    """Custom-drawn circular progress ring in Nothing OS signature styling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 50
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def setValue(self, val):
        self.value = val
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        side = min(width, height)
        
        cx = width // 2
        cy = height // 2
        r = (side - 30) // 2
        
        rect = QRect(cx - r, cy - r, r * 2, r * 2)
        
        # 1. Draw minimal track circle (dark grey)
        pen_track = QPen(QColor("#1e1e2a"), 6)
        pen_track.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_track)
        painter.drawEllipse(rect)
        
        # 2. Draw warm amber progress arc
        start_angle = 90 * 16
        span_angle = -int((self.value / 100.0) * 360) * 16
        
        pen_prog = QPen(QColor("#f0a820"), 6)
        pen_prog.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_prog)
        painter.drawArc(rect, start_angle, span_angle)
        
        # 3. Draw amber accent dot at the end of the arc
        theta = 90 - (self.value / 100.0) * 360
        rad = math.radians(theta)
        dot_x = cx + r * math.cos(rad)
        dot_y = cy - r * math.sin(rad)
        
        painter.setBrush(QColor("#f0a820"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)
        
        # 4. Center text: crisp percentage
        font_val = QFont(self.font())
        font_val.setFamily("'Consolas', 'Courier New', monospace")
        font_val.setPointSize(36)
        font_val.setBold(True)
        painter.setFont(font_val)
        painter.setPen(QColor("#ececee"))
        
        val_str = f"{self.value:02d}"
        fm_val = painter.fontMetrics()
        val_w = fm_val.horizontalAdvance(val_str)
        val_h = fm_val.height()
        
        painter.drawText(cx - val_w // 2, cy + val_h // 4 - 8, val_str)
        
        # Sub-text: "PERCENT"
        font_lbl = QFont(self.font())
        font_lbl.setPointSize(8)
        font_lbl.setBold(True)
        painter.setFont(font_lbl)
        painter.setPen(QColor("#88889a"))
        
        lbl_str = "PERCENT"
        fm_lbl = painter.fontMetrics()
        lbl_w = fm_lbl.horizontalAdvance(lbl_str)
        
        painter.drawText(cx - lbl_w // 2, cy + val_h // 2 + 10, lbl_str)
        painter.end()


class ProfileCurveWidget(QWidget):
    """
    Custom widget to display a beautiful spline of the 24-hour brightness profile
    with anti-aliasing, linear gradients, current-time indicator, and interactive dragging.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data = {}  # dict of time_val (int minutes) -> brightness_pct
        self.current_time_val = 0  # int minutes from midnight
        self.dragged_point = None  # key of the point being dragged
        self.point_dragged_callback = None  # callback during dragging
        self.drag_finished_callback = None  # callback on mouse release
        
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMouseTracking(True)
        
    def set_profile_data(self, data):
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
        """Calculates brightness target using Linear Interpolation (mirrors auto-brightness.sh)"""
        if not self.profile_data:
            return 15
        
        sorted_times = sorted(self.profile_data.keys())
        num_pts = len(sorted_times)
        
        if num_pts == 0:
            return 15
        elif num_pts == 1:
            return self.profile_data[sorted_times[0]]

        if minutes < sorted_times[0]:
            L_min = sorted_times[-1] - 1440
            L_pct = self.profile_data[sorted_times[-1]]
            U_min = sorted_times[0]
            U_pct = self.profile_data[sorted_times[0]]
        elif minutes > sorted_times[-1]:
            L_min = sorted_times[-1]
            L_pct = self.profile_data[sorted_times[-1]]
            U_min = sorted_times[0] + 1440
            U_pct = self.profile_data[sorted_times[0]]
        else:
            L_min, L_pct, U_min, U_pct = None, None, None, None
            for i in range(num_pts - 1):
                if sorted_times[i] <= minutes <= sorted_times[i+1]:
                    L_min = sorted_times[i]
                    L_pct = self.profile_data[sorted_times[i]]
                    U_min = sorted_times[i+1]
                    U_pct = self.profile_data[sorted_times[i+1]]
                    break
            if L_min is None:
                return 15
                
        denom = U_min - L_min
        if denom == 0:
            return L_pct
        else:
            return L_pct + (minutes - L_min) * (U_pct - L_pct) // denom

    def get_point_coords(self):
        """Returns physical coordinates (x, y) of profile config points."""
        coords = {}
        if not self.profile_data:
            return coords
            
        width = self.width()
        height = self.height()
        
        margin_left = 40
        margin_right = 20
        margin_top = 20
        margin_bottom = 25
        
        graph_w = width - margin_left - margin_right
        graph_h = height - margin_top - margin_bottom
        
        for m, val in self.profile_data.items():
            x = margin_left + (m / 1440.0 * graph_w)
            y = margin_top + graph_h - (val / 100.0 * graph_h)
            coords[m] = (x, y)
        return coords

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            coords = self.get_point_coords()
            for m, (x, y) in coords.items():
                dist = math.hypot(pos.x() - x, pos.y() - y)
                if dist <= 12:  # 12px hit radius
                    self.dragged_point = m
                    self.setCursor(Qt.ClosedHandCursor)
                    self.update()
                    break

    def mouseMoveEvent(self, event):
        pos = event.pos()
        # Cursor hover changes
        if self.dragged_point is None:
            coords = self.get_point_coords()
            hovering = False
            for m, (x, y) in coords.items():
                dist = math.hypot(pos.x() - x, pos.y() - y)
                if dist <= 12:
                    self.setCursor(Qt.PointingHandCursor)
                    hovering = True
                    break
            if not hovering:
                self.setCursor(Qt.ArrowCursor)
                
        # Dragging logic
        if self.dragged_point is not None:
            margin_top = 20
            margin_bottom = 25
            graph_h = self.height() - margin_top - margin_bottom
            if graph_h > 0:
                y = pos.y()
                val = 100.0 - ((y - margin_top) / graph_h * 100.0)
                val = max(5, min(100, int(val)))
                self.profile_data[self.dragged_point] = val
                if self.point_dragged_callback:
                    self.point_dragged_callback(self.dragged_point, val)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragged_point is not None:
            self.dragged_point = None
            self.setCursor(Qt.ArrowCursor)
            if self.drag_finished_callback:
                self.drag_finished_callback()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        margin_left = 40
        margin_right = 20
        margin_top = 20
        margin_bottom = 25
        
        graph_w = width - margin_left - margin_right
        graph_h = height - margin_top - margin_bottom
        
        # 1. Background grid & Y labels
        painter.setPen(QPen(QColor("#16161e"), 1, Qt.SolidLine))
        font = QFont(self.font())
        font.setPointSize(9)
        painter.setFont(font)
        
        for i in range(6):
            pct = i * 20
            y = margin_top + graph_h - (pct / 100.0 * graph_h)
            painter.drawLine(margin_left, y, width - margin_right, y)
            
            painter.setPen(QColor("#88889a"))
            painter.drawText(5, y + 4, f"{pct}%")
            painter.setPen(QPen(QColor("#16161e"), 1, Qt.SolidLine))
            
        # Draw X Grid & Labels
        for h in range(0, 25, 4):
            minutes = h * 60
            x = margin_left + (minutes / 1440.0 * graph_w)
            painter.drawLine(x, margin_top, x, height - margin_bottom)
            
            painter.setPen(QColor("#88889a"))
            time_label = f"{h:02d}:00"
            painter.drawText(x - 15, height - 8, time_label)
            painter.setPen(QPen(QColor("#16161e"), 1, Qt.SolidLine))
            
        # 2. Draw Continuous Interpolated Path
        if not self.profile_data:
            painter.end()
            return
            
        path = QPainterPath()
        started = False
        
        for m in range(0, 1441, 5):  # Sample every 5 mins
            val = self.get_interpolated_value(m)
            x = margin_left + (m / 1440.0 * graph_w)
            y = margin_top + graph_h - (val / 100.0 * graph_h)
            
            if not started:
                path.moveTo(x, y)
                started = True
            else:
                path.lineTo(x, y)
                
        val_end = self.get_interpolated_value(1439)
        x_end = margin_left + graph_w
        y_end = margin_top + graph_h - (val_end / 100.0 * graph_h)
        path.lineTo(x_end, y_end)
        
        # Fill minimal gradient
        fill_path = QPainterPath(path)
        fill_path.lineTo(x_end, margin_top + graph_h)
        fill_path.lineTo(margin_left, margin_top + graph_h)
        fill_path.closeSubpath()
        
        gradient = QLinearGradient(0, margin_top, 0, margin_top + graph_h)
        gradient.setColorAt(0.0, QColor(240, 168, 32, 30))
        gradient.setColorAt(1.0, QColor(240, 168, 32, 0))
        painter.fillPath(fill_path, QBrush(gradient))
        
        # Draw spline line
        painter.setPen(QPen(QColor("#f0a820"), 2, Qt.SolidLine))
        painter.drawPath(path)
        
        # 3. Draw Profile Key Points (Draggable nodes)
        coords = self.get_point_coords()
        for m, (x, y) in coords.items():
            if self.dragged_point == m:
                # Amber drag marker
                painter.setBrush(QColor(240, 168, 32, 80))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPoint(x, y), 8, 8)
                painter.setBrush(QColor("#f0a820"))
                painter.drawEllipse(QPoint(x, y), 4, 4)
                
                # Floating tooltip badge
                h = m // 60
                mn = m % 60
                val = self.profile_data[m]
                badge_text = f"{h:02d}:{mn:02d} ({val}%)"
                
                font_badge = QFont(self.font())
                font_badge.setPointSize(8)
                font_badge.setBold(True)
                painter.setFont(font_badge)
                
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(badge_text)
                th = fm.height()
                
                bx = x - tw // 2 - 6
                by = y - 32
                
                painter.setBrush(QColor("#0d0d14"))
                painter.setPen(QPen(QColor("#f0a820"), 1))
                painter.drawRoundedRect(bx, by, tw + 12, th + 6, 4, 4)
                
                painter.setPen(QColor("#ececee"))
                painter.drawText(bx + 6, by + th, badge_text)
            else:
                # Crisp white circle node
                painter.setBrush(QColor("#0d0d14"))
                painter.setPen(QPen(QColor("#ececee"), 1.5))
                painter.drawEllipse(QPoint(x, y), 4, 4)
        
        # 4. Current Time Marker (amber glow)
        current_val = self.get_interpolated_value(self.current_time_val)
        cur_x = margin_left + (self.current_time_val / 1440.0 * graph_w)
        cur_y = margin_top + graph_h - (current_val / 100.0 * graph_h)
        
        painter.setBrush(QColor(240, 168, 32, 80))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(cur_x, cur_y), 8, 8)
        
        painter.setBrush(QColor("#ececee"))
        painter.setPen(QPen(QColor("#f0a820"), 1.5))
        painter.drawEllipse(QPoint(cur_x, cur_y), 3.5, 3.5)
        
        painter.end()


class BrightnessGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Ensure custom UI SVGs exist for custom QSS loading
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            arrow_path = os.path.join(CONFIG_DIR, "down_arrow.svg")
            with open(arrow_path, "w") as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18"><path fill="#f0a820" d="M7 10l5 5 5-5z"/></svg>')
                
            check_path = os.path.join(CONFIG_DIR, "checkbox_check.svg")
            with open(check_path, "w") as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="12" height="12"><path fill="black" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>')
        except Exception:
            pass
            
        self.setWindowTitle("Adaptive Brightness")
        self.resize(880, 680)
        
        # Dynamically evaluate QSS home folder path
        real_qss = QSS.replace("/home/arjun", os.path.expanduser("~"))
        self.setStyleSheet(real_qss)
        self.setWindowIcon(create_sun_icon(64))
        
        self.profiles = {}
        self.current_brightness = 50
        self.is_paused = False
        self.pause_remaining = ""
        self.ambient_sensor_enabled = False
        self.disabled_displays_list = []
        
        self.circular_display = CircularBrightnessDisplay()
        self.curve_widget = ProfileCurveWidget()
        
        # Link graph drag interactions
        self.curve_widget.point_dragged_callback = self.on_curve_point_dragged
        self.curve_widget.drag_finished_callback = self.save_profile_config
        
        # File Watcher for logs
        self.watcher = QFileSystemWatcher(self)
        if os.path.exists(LOG_FILE):
            self.watcher.addPath(LOG_FILE)
        self.watcher.fileChanged.connect(self.load_logs)
        
        self.setup_ui()
        self.load_profile_config()
        self.rebuild_display_controllers()
        self.update_status()
        
        # Ticking timer (ticks status every 5 seconds for responsive clock/countdown)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # HEADER BAR
        header_layout = QHBoxLayout()
        header_text_layout = QHBoxLayout()
        header_text_layout.setSpacing(16)
        header_text_layout.setAlignment(Qt.AlignVCenter)
        
        title_label = QLabel("LeanBitLab")
        title_label.setProperty("class", "Title")
        
        header_text_layout.addWidget(title_label)
        header_text_layout.addStretch()
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()
        
        self.active_badge = QLabel()
        self.active_badge.setText("☀ BRIGHTNESS ACTIVE")
        self.active_badge.setStyleSheet(
            "background-color: #16161e; color: #88889a; font-weight: 700; "
            "border: 1px solid #28283a; padding: 4px 10px; border-radius: 10px; font-size: 10px; letter-spacing: 1.5px;"
        )
        header_layout.addWidget(self.active_badge)
        main_layout.addLayout(header_layout)
        
        # TAB CONTAINER
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Dashboard
        self.tab_dashboard = QWidget()
        self.tab_dashboard.setObjectName("tab_dashboard")
        self.setup_dashboard_tab()
        self.tabs.addTab(self.tab_dashboard, "DASHBOARD")
        
        # Tab 2: Profile Editor
        self.tab_profile = QWidget()
        self.tab_profile.setObjectName("tab_profile")
        self.setup_profile_tab()
        self.tabs.addTab(self.tab_profile, "PROFILE EDITOR")
        
        # Tab 3: Logs
        self.tab_logs = QWidget()
        self.tab_logs.setObjectName("tab_logs")
        self.setup_logs_tab()
        self.tabs.addTab(self.tab_logs, "ACTIVITY LOGS")
        
        self.setup_system_tray()
        
    def setup_dashboard_tab(self):
        layout = QHBoxLayout(self.tab_dashboard)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # LEFT PANEL: Selector dropdown, dial and Controls
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        # Display Dropdown Selector Card
        selector_card = QFrame()
        selector_card.setProperty("class", "Card")
        sel_layout = QHBoxLayout(selector_card)
        sel_layout.setContentsMargins(16, 12, 16, 12)
        
        lbl_sel = QLabel("ACTIVE SCREEN")
        lbl_sel.setProperty("class", "HeaderLabel")
        lbl_sel.setStyleSheet("background: transparent;")
        
        self.combo_active_display = QComboBox()
        self.combo_active_display.setItemDelegate(QStyledItemDelegate())
        self.combo_active_display.setToolTip("Select which display to view and edit.\nClick the dropdown arrow to switch between screens.")
        self.combo_active_display.currentIndexChanged.connect(self.on_active_display_changed)
        
        sel_layout.addWidget(lbl_sel)
        sel_layout.addStretch()
        sel_layout.addWidget(self.combo_active_display)
        left_panel.addWidget(selector_card)
        
        # Card 1: compact dial
        dial_card = QFrame()
        dial_card.setProperty("class", "Card")
        dial_layout = QVBoxLayout(dial_card)
        dial_layout.setContentsMargins(12, 12, 12, 12)
        dial_layout.setAlignment(Qt.AlignCenter)
        dial_layout.addWidget(self.circular_display)
        left_panel.addWidget(dial_card, 2)
        
        # Card 2: System Control Panel (Timer + Pause)
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(16, 16, 16, 16)
        ctrl_layout.setSpacing(12)
        
        l_ctrl = QLabel("System Controls")
        l_ctrl.setProperty("class", "HeaderLabel")
        ctrl_layout.addWidget(l_ctrl)
        
        timer_btn_layout = QHBoxLayout()
        timer_btn_layout.setSpacing(8)
        self.btn_daemon_toggle = QPushButton("Disable Timer")
        self.btn_daemon_toggle.setToolTip("Permanently stops the background systemd timer\nfrom checking and adjusting brightness levels.")
        self.btn_daemon_toggle.clicked.connect(self.toggle_daemon)
        
        self.btn_run_script = QPushButton("Adjust Now")
        style_secondary(self.btn_run_script)
        self.btn_run_script.setToolTip("Force-run the brightness script immediately\nto snap to the current profile target.")
        self.btn_run_script.clicked.connect(self.trigger_script_adjust)
        
        timer_btn_layout.addWidget(self.btn_daemon_toggle)
        timer_btn_layout.addWidget(self.btn_run_script)
        ctrl_layout.addLayout(timer_btn_layout)
        
        # System control extra actions row
        timer_btn_layout2 = QHBoxLayout()
        timer_btn_layout2.setSpacing(8)
        
        self.btn_restart_service = QPushButton("Restart Daemon")
        style_secondary(self.btn_restart_service)
        self.btn_restart_service.setToolTip("Restart the background systemd timer and service\nto apply profiles fresh.")
        self.btn_restart_service.clicked.connect(self.restart_systemd_service)
        
        self.btn_clear_overrides = QPushButton("Reset Overrides")
        style_secondary(self.btn_clear_overrides)
        self.btn_clear_overrides.setToolTip("Remove all temporary manual overrides so screens\nsnap back to profile scheduled level.")
        self.btn_clear_overrides.clicked.connect(self.clear_state_overrides)
        
        timer_btn_layout2.addWidget(self.btn_restart_service)
        timer_btn_layout2.addWidget(self.btn_clear_overrides)
        ctrl_layout.addLayout(timer_btn_layout2)
        
        # System control extra actions row 2
        timer_btn_layout3 = QHBoxLayout()
        timer_btn_layout3.setSpacing(8)
        
        self.btn_force_learn = QPushButton("Force Learn")
        style_secondary(self.btn_force_learn)
        self.btn_force_learn.setToolTip("Immediately teach the system your current manual brightness\nas the preferred level for the active time block.")
        self.btn_force_learn.clicked.connect(self.force_learn_now)
        
        self.btn_restore_defaults = QPushButton("Restore Defaults")
        style_danger(self.btn_restore_defaults)
        self.btn_restore_defaults.setToolTip("Reset the selected display's brightness curve back\nto the factory 24-hour defaults. This cannot be undone.")
        self.btn_restore_defaults.clicked.connect(self.restore_default_profile)
        
        timer_btn_layout3.addWidget(self.btn_force_learn)
        timer_btn_layout3.addWidget(self.btn_restore_defaults)
        ctrl_layout.addLayout(timer_btn_layout3)
        
        # Line break separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #28283a;")
        ctrl_layout.addWidget(sep)
        
        # Pause Controls Group
        self.pause_container = QWidget()
        pause_layout = QVBoxLayout(self.pause_container)
        pause_layout.setContentsMargins(0, 0, 0, 0)
        pause_layout.setSpacing(8)
        
        lbl_pause = QLabel("Pause Background adjustments")
        lbl_pause.setStyleSheet("color: #88889a; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        pause_layout.addWidget(lbl_pause)
        
        pause_btn_layout = QHBoxLayout()
        self.btn_pause_1h = QPushButton("1h")
        style_secondary(self.btn_pause_1h)
        self.btn_pause_1h.setToolTip("Pause automatic brightness adjustments\nfor 1 hour.")
        self.btn_pause_1h.clicked.connect(lambda: self.apply_pause(3600))
        
        self.btn_pause_3h = QPushButton("3h")
        style_secondary(self.btn_pause_3h)
        self.btn_pause_3h.setToolTip("Pause automatic brightness adjustments\nfor 3 hours.")
        self.btn_pause_3h.clicked.connect(lambda: self.apply_pause(3 * 3600))
        
        self.btn_pause_8h = QPushButton("8h")
        style_secondary(self.btn_pause_8h)
        self.btn_pause_8h.setToolTip("Pause automatic brightness adjustments\nfor 8 hours.")
        self.btn_pause_8h.clicked.connect(lambda: self.apply_pause(8 * 3600))
        
        self.btn_pause_indef = QPushButton("Indefinite")
        style_secondary(self.btn_pause_indef)
        self.btn_pause_indef.setToolTip("Freeze brightness levels indefinitely without\nstopping the background timer service.")
        self.btn_pause_indef.clicked.connect(lambda: self.apply_pause("indefinite"))
        
        pause_btn_layout.addWidget(self.btn_pause_1h)
        pause_btn_layout.addWidget(self.btn_pause_3h)
        pause_btn_layout.addWidget(self.btn_pause_8h)
        pause_btn_layout.addWidget(self.btn_pause_indef)
        pause_layout.addLayout(pause_btn_layout)
        ctrl_layout.addWidget(self.pause_container)
        
        # Paused countdown overlay
        self.paused_status_container = QWidget()
        paused_status_layout = QVBoxLayout(self.paused_status_container)
        paused_status_layout.setContentsMargins(0, 0, 0, 0)
        paused_status_layout.setSpacing(8)
        
        self.lbl_pause_countdown = QLabel("Paused")
        self.lbl_pause_countdown.setStyleSheet("color: #f0a820; font-size: 13px; font-weight: 700; margin: 4px 0;")
        self.lbl_pause_countdown.setAlignment(Qt.AlignCenter)
        
        self.btn_resume = QPushButton("Resume Adjustments")
        style_primary(self.btn_resume)
        self.btn_resume.clicked.connect(self.resume_adjustments)
        
        paused_status_layout.addWidget(self.lbl_pause_countdown)
        paused_status_layout.addWidget(self.btn_resume)
        ctrl_layout.addWidget(self.paused_status_container)
        
        left_panel.addWidget(ctrl_card, 3)
        
        layout.addLayout(left_panel, 2)
        
        # RIGHT PANEL: Spline graph & Override Panel
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)
        
        # Graph Card
        graph_card = QFrame()
        graph_card.setProperty("class", "Card")
        gf_layout = QVBoxLayout(graph_card)
        gf_layout.setContentsMargins(16, 16, 16, 16)
        
        header_graph = QHBoxLayout()
        vl = QLabel("24-Hour Adaptive Brightness Path")
        vl.setProperty("class", "HeaderLabel")
        
        lbl_hint = QLabel("Drag coordinate nodes directly to adjust")
        lbl_hint.setStyleSheet("color: #5c5c6e; font-size: 11px; font-weight: 600;")
        
        header_graph.addWidget(vl)
        header_graph.addStretch()
        header_graph.addWidget(lbl_hint)
        
        gf_layout.addLayout(header_graph)
        gf_layout.addWidget(self.curve_widget)
        
        # Timeblock details
        tb_detail_layout = QHBoxLayout()
        tb_detail_layout.setSpacing(16)
        
        v_blk = QVBoxLayout()
        lbl_blk_title = QLabel("Active Time Block")
        lbl_blk_title.setStyleSheet("color: #88889a; font-size: 11px; font-weight: bold;")
        self.lbl_active_block = QLabel("00:00")
        self.lbl_active_block.setStyleSheet("font-size: 18px; font-weight: 800; color: #ececee; font-family: monospace;")
        v_blk.addWidget(lbl_blk_title)
        v_blk.addWidget(self.lbl_active_block)
        
        v_tgt = QVBoxLayout()
        lbl_tgt_title = QLabel("Target Brightness")
        lbl_tgt_title.setStyleSheet("color: #88889a; font-size: 11px; font-weight: bold;")
        self.lbl_profile_target = QLabel("15%")
        self.lbl_profile_target.setStyleSheet("font-size: 18px; font-weight: 800; color: #ececee; font-family: monospace;")
        v_tgt.addWidget(lbl_tgt_title)
        v_tgt.addWidget(self.lbl_profile_target)
        
        tb_detail_layout.addLayout(v_blk)
        tb_detail_layout.addLayout(v_tgt)
        tb_detail_layout.addStretch()
        gf_layout.addLayout(tb_detail_layout)
        
        right_panel.addWidget(graph_card, 3)
        
        # Focused Display Controls Card
        self.override_card = QFrame()
        self.override_card.setProperty("class", "Card")
        self.of_layout = QVBoxLayout(self.override_card)
        self.of_layout.setContentsMargins(16, 16, 16, 16)
        self.of_layout.setSpacing(12)
        
        self.lbl_display_ctrl_title = QLabel("DISPLAY CONTROLS")
        self.lbl_display_ctrl_title.setProperty("class", "HeaderLabel")
        self.of_layout.addWidget(self.lbl_display_ctrl_title)
        
        # Focused single-display control row
        disp_ctrl_row = QHBoxLayout()
        disp_ctrl_row.setSpacing(10)
        
        self.lbl_display_brightness_val = QLabel("--%")
        self.lbl_display_brightness_val.setStyleSheet(
            "font-family: monospace; font-size: 18px; font-weight: 900; color: #ececee; background: transparent;"
        )
        self.lbl_display_brightness_val.setFixedWidth(50)
        
        self.slider_display_brightness = NoWheelSlider(Qt.Horizontal)
        self.slider_display_brightness.setRange(5, 100)
        self.slider_display_brightness.setValue(50)
        self.slider_display_brightness.setFixedHeight(30)
        self.slider_display_brightness.sliderReleased.connect(self._on_focused_slider_released)
        
        self.btn_display_auto_toggle = QPushButton("AUTO ON")
        self.btn_display_auto_toggle.setFixedWidth(120)
        self.btn_display_auto_toggle.setFixedHeight(38)
        self.btn_display_auto_toggle.setCheckable(True)
        style_primary(self.btn_display_auto_toggle)
        self.btn_display_auto_toggle.clicked.connect(self._on_focused_auto_toggled)
        
        disp_ctrl_row.addWidget(self.lbl_display_brightness_val)
        disp_ctrl_row.addWidget(self.slider_display_brightness, 2)
        disp_ctrl_row.addWidget(self.btn_display_auto_toggle)
        self.of_layout.addLayout(disp_ctrl_row)
        
        # Bottom controls: Ambient and Learning note
        bottom_ctrls = QVBoxLayout()
        bottom_ctrls.setSpacing(8)
        
        self.chk_ambient = QCheckBox("Enable Ambient Sensor Scaling")
        self.chk_ambient.setObjectName("chk_ambient")
        self.chk_ambient.toggled.connect(self.toggle_ambient_sensor)
        
        self.chk_autostart = QCheckBox("Start Control Panel on Login")
        self.chk_autostart.setObjectName("chk_autostart")
        self.chk_autostart.toggled.connect(self.toggle_autostart)
        
        self.chk_autostart_minimized = QCheckBox("Start Minimized in System Tray")
        self.chk_autostart_minimized.setObjectName("chk_autostart_minimized")
        self.chk_autostart_minimized.toggled.connect(self.toggle_autostart_minimized)
        
        bottom_ctrls.addWidget(self.chk_ambient)
        bottom_ctrls.addWidget(self.chk_autostart)
        bottom_ctrls.addWidget(self.chk_autostart_minimized)
        self.of_layout.addLayout(bottom_ctrls)
        
        self.lbl_learning_note = QLabel(
            "ℹ️ Slider overrides hardware immediately. "
            "Changes within 20 mins of a profile node will trigger adaptive learning."
        )
        self.lbl_learning_note.setStyleSheet("color: #5c5c6e; font-size: 11px; font-weight: 500;")
        self.lbl_learning_note.setWordWrap(True)
        self.of_layout.addWidget(self.lbl_learning_note)
        
        right_panel.addWidget(self.override_card, 2)
        
        layout.addLayout(right_panel, 3)

    def setup_profile_tab(self):
        tab_layout = QVBoxLayout(self.tab_profile)
        tab_layout.setContentsMargins(16, 16, 16, 16)
        tab_layout.setSpacing(12)
        
        lbl_info = QLabel("Customize Target Brightness for Time Blocks")
        lbl_info.setProperty("class", "HeaderLabel")
        tab_layout.addWidget(lbl_info)
        
        # Add Time Block form card
        add_block_card = QFrame()
        add_block_card.setProperty("class", "Card")
        add_block_layout = QHBoxLayout(add_block_card)
        add_block_layout.setContentsMargins(16, 12, 16, 12)
        add_block_layout.setSpacing(16)
        
        lbl_add = QLabel("ADD BLOCK:")
        lbl_add.setProperty("class", "HeaderLabel")
        lbl_add.setStyleSheet("color: #ececee;")
        
        lbl_time_lbl = QLabel("Time:")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(12, 0))
        self.time_edit.setStyleSheet(
            "background-color: #0d0d14; border: 1px solid #28283a; border-radius: 8px; "
            "padding: 6px 12px; color: #ececee; font-weight: bold;"
        )
        
        lbl_bright_lbl = QLabel("Brightness:")
        self.spin_brightness_input = QSpinBox()
        self.spin_brightness_input.setRange(5, 100)
        self.spin_brightness_input.setValue(50)
        self.spin_brightness_input.setSuffix("%")
        self.spin_brightness_input.setFixedWidth(85)
        
        self.btn_add_block = QPushButton("Add Block")
        style_primary(self.btn_add_block)
        self.btn_add_block.setFixedWidth(110)
        self.btn_add_block.clicked.connect(self.add_profile_block)
        
        add_block_layout.addWidget(lbl_add)
        add_block_layout.addWidget(lbl_time_lbl)
        add_block_layout.addWidget(self.time_edit)
        add_block_layout.addWidget(lbl_bright_lbl)
        add_block_layout.addWidget(self.spin_brightness_input)
        add_block_layout.addStretch()
        add_block_layout.addWidget(self.btn_add_block)
        
        tab_layout.addWidget(add_block_card)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.profile_grid = QGridLayout(scroll_content)
        self.profile_grid.setContentsMargins(12, 12, 12, 12)
        self.profile_grid.setSpacing(16)
        
        scroll.setWidget(scroll_content)
        tab_layout.addWidget(scroll)
        
        action_layout = QHBoxLayout()
        self.btn_reset_profile = QPushButton("Reload Profile")
        style_secondary(self.btn_reset_profile)
        self.btn_reset_profile.clicked.connect(self.load_profile_config)
        
        self.btn_save_profile = QPushButton("Save Profiles")
        style_primary(self.btn_save_profile)
        self.btn_save_profile.clicked.connect(self.save_profile_config)
        
        action_layout.addWidget(self.btn_reset_profile)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_save_profile)
        tab_layout.addLayout(action_layout)
        
        self.profile_widgets = {}

    def setup_logs_tab(self):
        layout = QVBoxLayout(self.tab_logs)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header = QHBoxLayout()
        lbl_logs = QLabel("Real-time Service Operation Logs")
        lbl_logs.setProperty("class", "HeaderLabel")
        
        btn_clear = QPushButton("Clear Logs")
        style_secondary(btn_clear)
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
        
        # Submenu for Pause daemon
        pause_submenu = QMenu("Pause Adjustments", tray_menu)
        
        act_pause_1h = QAction("1 Hour", self)
        act_pause_1h.triggered.connect(lambda: self.apply_pause(3600))
        pause_submenu.addAction(act_pause_1h)
        
        act_pause_3h = QAction("3 Hours", self)
        act_pause_3h.triggered.connect(lambda: self.apply_pause(3 * 3600))
        pause_submenu.addAction(act_pause_3h)
        
        act_pause_8h = QAction("8 Hours", self)
        act_pause_8h.triggered.connect(lambda: self.apply_pause(8 * 3600))
        pause_submenu.addAction(act_pause_8h)
        
        act_pause_indef = QAction("Indefinitely", self)
        act_pause_indef.triggered.connect(lambda: self.apply_pause("indefinite"))
        pause_submenu.addAction(act_pause_indef)
        
        tray_menu.addMenu(pause_submenu)
        
        self.act_resume_tray = QAction("Resume Adjustments", self)
        self.act_resume_tray.triggered.connect(self.resume_adjustments)
        tray_menu.addAction(self.act_resume_tray)
        
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
        if self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "Adaptive Brightness",
                "Control panel minimized. Run in background.",
                QSystemTrayIcon.Information,
                3000
            )
            event.ignore()
        else:
            event.accept()

    def quit_app(self):
        self.tray.hide()
        QApplication.quit()

    def on_curve_point_dragged(self, minutes, value):
        """Callback from curve dragging to keep sliders in sync. Writes to per-display profile."""
        h = minutes // 60
        m = minutes % 60
        time_str = f"{h:02d}{m:02d}"
        
        dev = self.get_active_display_dev()
        if dev not in self.profiles:
            self.profiles[dev] = {}
        self.profiles[dev][time_str] = value
        
        if time_str in self.profile_widgets:
            slider, spin = self.profile_widgets[time_str]
            slider.blockSignals(True)
            spin.blockSignals(True)
            slider.setValue(value)
            spin.setValue(value)
            slider.blockSignals(False)
            spin.blockSignals(False)
            
        self.update_status_dashboard_only()

    def update_status_dashboard_only(self):
        """Update textual target values quickly during live curve drags."""
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        
        target_val = self.curve_widget.get_interpolated_value(cur_min)
        
        self.circular_display.setValue(target_val)
        
        # Find active block boundary using per-display profile
        profile_data = self.get_profile_for_current_display()
        sorted_times = sorted(profile_data.keys())
        active_time_str = "0000"
        for t in sorted_times:
            try:
                h = int(t[:2])
                m = int(t[2:])
                min_val = h * 60 + m
                if cur_min >= min_val:
                    active_time_str = t
            except Exception:
                pass
                
        self.lbl_active_block.setText(f"{active_time_str[:2]}:{active_time_str[2:]}")
        self.lbl_profile_target.setText(f"{target_val}%")

    def rebuild_display_controllers(self):
        """Builds controls dynamically for every connected backlight device."""
        # Populate active display selector dropdown
        self.combo_active_display.blockSignals(True)
        self.combo_active_display.clear()
        
        devices = get_backlight_devices()
        for dev in devices:
            nice_name = "Primary Screen" if dev == "default" else f"Screen ({dev})"
            self.combo_active_display.addItem(nice_name.upper(), dev)
            
        self.combo_active_display.blockSignals(False)
        
        # Update focused display controls card title
        self._update_focused_display_card()

    def _update_focused_display_card(self):
        """Updates the focused display controls card to reflect selected display."""
        dev = self.get_active_display_dev()
        nice_name = "PRIMARY SCREEN" if dev == "default" else f"SCREEN ({dev.upper()})"
        self.lbl_display_ctrl_title.setText(f"CONTROLS: {nice_name}")
        
        # Update auto toggle state & slider state
        is_manual = dev in self.disabled_displays_list
        self.btn_display_auto_toggle.blockSignals(True)
        self.btn_display_auto_toggle.setChecked(is_manual)
        if is_manual:
            self.btn_display_auto_toggle.setText("Manual")
            self.btn_display_auto_toggle.setStyleSheet(
                "QPushButton { background-color: transparent; color: #5c5c6e; border: 2px solid #28283a; "
                "padding: 8px 16px; border-radius: 10px; font-weight: bold; font-size: 13px; }"
                "QPushButton:hover { background-color: rgba(240, 168, 32, 0.1); border-color: #f0a820; color: #ececee; }"
            )
            self.slider_display_brightness.setEnabled(True)
        else:
            self.btn_display_auto_toggle.setText("Auto")
            style_primary(self.btn_display_auto_toggle)
            self.slider_display_brightness.setEnabled(False)
        self.btn_display_auto_toggle.blockSignals(False)
        
        # Update brightness slider and label
        try:
            pct_val = get_device_brightness(dev)
            if pct_val is not None:
                self.lbl_display_brightness_val.setText(f"{pct_val:02d}%")
                self.slider_display_brightness.blockSignals(True)
                self.slider_display_brightness.setValue(pct_val)
                self.slider_display_brightness.blockSignals(False)
        except Exception:
            pass
    
    def _on_focused_slider_released(self):
        """Applies slider override to the currently selected display."""
        dev = self.get_active_display_dev()
        val = self.slider_display_brightness.value()
        self.apply_device_override(dev, val)
    
    def _on_focused_auto_toggled(self, checked):
        """Toggles auto-adjust for the currently selected display."""
        dev = self.get_active_display_dev()
        self.toggle_display_adjust(dev, checked)

    def toggle_display_adjust(self, dev, disable):
        """Adds or removes device from auto-adjust exclusion list."""
        if disable:
            if dev not in self.disabled_displays_list:
                self.disabled_displays_list.append(dev)
        else:
            if dev in self.disabled_displays_list:
                self.disabled_displays_list.remove(dev)
        self.save_disabled_displays()
        self.update_status()

    def save_disabled_displays(self):
        """Saves exclusion list permanently to config file."""
        if not os.path.exists(CONFIG_FILE):
            return
            
        lines = []
        found = False
        val = ",".join(self.disabled_displays_list)
        
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("disabled_displays="):
                    lines.append(f"disabled_displays={val}\n")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"disabled_displays={val}\n")
            
        with open(CONFIG_FILE, "w") as f:
            f.writelines(lines)
            
        self.trigger_script_adjust()
        self.update_status()

    def get_active_display_dev(self):
        """Returns currently selected device identifier from Active Screen dropdown."""
        if hasattr(self, "combo_active_display") and self.combo_active_display.count() > 0:
            dev = self.combo_active_display.currentData()
            if dev:
                return dev
        return "default"

    def get_profile_for_current_display(self):
        """Retrieves profile coordinates dict for selected display, falling back gracefully to default."""
        dev = self.get_active_display_dev()
        if dev in self.profiles and self.profiles[dev]:
            return self.profiles[dev]
        devices = get_backlight_devices()
        primary = devices[0] if devices else "default"
        if dev == primary or dev == "default":
            if "default" in self.profiles:
                return self.profiles["default"]
        if "default" in self.profiles:
            return self.profiles["default"]
        return {}

    def on_active_display_changed(self):
        """Triggers updates across profile list spline and circular dial when active display changes."""
        profile_data = self.get_profile_for_current_display()
        self.curve_widget.set_profile_data(profile_data)
        self._update_focused_display_card()
        self.rebuild_profile_editor()
        self.update_status()

    def restart_systemd_service(self):
        """Restarts background auto-brightness timer and service to ensure configurations load fresh."""
        try:
            subprocess.run(["systemctl", "--user", "restart", "auto-brightness.timer"], capture_output=True)
            subprocess.run(["systemctl", "--user", "restart", "auto-brightness.service"], capture_output=True)
            self.load_logs()
        except Exception:
            pass
        self.update_status()
        
    def clear_state_overrides(self):
        """Deletes all persistent and per-device override state files and forces background script to run."""
        try:
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            devices = get_backlight_devices()
            for dev in devices:
                dev_state = os.path.expanduser(f"~/.local/state/auto-brightness.{dev}.state")
                if os.path.exists(dev_state):
                    os.remove(dev_state)
            if os.path.exists(SCRIPT_PATH):
                subprocess.Popen(["bash", SCRIPT_PATH])
        except Exception:
            pass
        QTimer.singleShot(300, self.update_status)

    def force_learn_now(self):
        """Immediately saves current hardware brightness as the learned preference for active time block."""
        dev = self.get_active_display_dev()
        try:
            pct_val = get_device_brightness(dev)
            if pct_val is None:
                return
        except Exception:
            return
        
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        
        # Find nearest profile time block
        profile_data = self.get_profile_for_current_display()
        nearest_time = "0000"
        min_diff = 9999
        for t in profile_data.keys():
            try:
                h = int(t[:2])
                m = int(t[2:])
                t_min = h * 60 + m
                diff = abs(cur_min - t_min)
                if diff < min_diff:
                    min_diff = diff
                    nearest_time = t
            except Exception:
                pass
        
        # Update profile
        if dev not in self.profiles:
            self.profiles[dev] = {}
        self.profiles[dev][nearest_time] = pct_val
        
        self.save_profile_config()
        self.curve_widget.set_profile_data(self.get_profile_for_current_display())
        self.rebuild_profile_editor()
        self.update_status()

    def restore_default_profile(self):
        """Resets the selected display's profile curve back to factory 24-hour defaults."""
        default_curve = {
            "0000": 15, "0100": 15, "0200": 15, "0300": 15, "0400": 15, "0500": 15,
            "0530": 18, "0600": 22, "0630": 26, "0700": 30, "0730": 35, "0800": 40,
            "0830": 45, "0900": 50, "0930": 55, "1000": 60, "1030": 65, "1100": 70,
            "1130": 75, "1200": 80, "1230": 80, "1300": 78, "1330": 76, "1400": 74,
            "1430": 72, "1500": 70, "1530": 68, "1600": 66, "1630": 64, "1700": 62,
            "1730": 60, "1800": 55, "1830": 50, "1900": 45, "1930": 40, "2000": 35,
            "2030": 30, "2100": 26, "2130": 23, "2200": 20, "2230": 18, "2300": 16,
            "2330": 15,
        }
        dev = self.get_active_display_dev()
        self.profiles[dev] = dict(default_curve)
        
        self.save_profile_config()
        self.curve_widget.set_profile_data(self.get_profile_for_current_display())
        self.rebuild_profile_editor()
        self.update_status()

    def apply_device_override(self, dev, val):
        """Applies manual override exclusively to targeted screen backlight."""
        devices = get_backlight_devices()
        primary = devices[0] if devices else "default"
        
        if dev == primary or dev == "default":
            now_epoch = int(datetime.now().timestamp())
            try:
                os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
                with open(STATE_FILE, "w") as f:
                    f.write(f"{val} {now_epoch}\n")
            except Exception:
                pass
                
        self.set_device_brightness(dev, val)
        
        if (dev == "default" or dev == primary) and os.path.exists(SCRIPT_PATH):
            subprocess.Popen(["bash", SCRIPT_PATH])
            
        QTimer.singleShot(250, self.update_status)

    def set_device_brightness(self, dev, val):
        """Sets brightness for display using kscreen-doctor first, then D-Bus or brightnessctl fallback."""
        # 1. Try kscreen-doctor first
        if dev != "default":
            try:
                res = subprocess.run(["kscreen-doctor", f"output.{dev}.brightness.{val}"], capture_output=True)
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        # 2. Fallback to normal primary/secondary methods
        devices = get_backlight_devices()
        primary = devices[0] if devices else "default"
        if dev == "default" or dev == primary:
            self.set_primary_brightness(val)
        else:
            try:
                subprocess.run(["brightnessctl", "-d", dev, "-q", "set", f"{val}%"])
            except Exception:
                # If brightnessctl failed, try direct set as last resort
                try:
                    subprocess.run(["brightnessctl", "-q", "set", f"{val}%"])
                except Exception:
                    pass
        return True

    def set_primary_brightness(self, val):
        dbus_cmd = ""
        if os.path.exists("/usr/bin/qdbus6"):
            dbus_cmd = "qdbus6"
        elif os.path.exists("/usr/bin/qdbus"):
            dbus_cmd = "qdbus"
            
        if dbus_cmd:
            try:
                val_scale = val * 100
                subprocess.run([
                    dbus_cmd, "org.kde.Solid.PowerManagement", 
                    "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                    "org.kde.Solid.PowerManagement.Actions.BrightnessControl.setBrightnessSilent",
                    str(val_scale)
                ], capture_output=True)
                return
            except Exception:
                pass
                
        subprocess.run(["brightnessctl", "-q", "set", f"{val}%"])

    def load_profile_config(self):
        """Loads and parses the profile configuration file, including disabled screen lists."""
        if not os.path.exists(CONFIG_FILE):
            return
            
        profiles = {}
        self.ambient_sensor_enabled = False
        self.disabled_displays_list = []
        
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("ambient_sensor="):
                    self.ambient_sensor_enabled = (line.split("=")[1].strip() == "1")
                    continue
                if line.startswith("disabled_displays="):
                    val = line.split("=")[1].strip()
                    if val:
                        self.disabled_displays_list = [d.strip() for d in val.split(",") if d.strip()]
                    continue
                
                # Support multi-display formatting, e.g. HDMI-A-1_0530=25
                match_dev = re.match(r"^([a-zA-Z0-9-]+)_(\d{4})=(\d+)", line)
                if match_dev:
                    dev = match_dev.group(1)
                    t = match_dev.group(2)
                    v = int(match_dev.group(3))
                    if dev not in profiles:
                        profiles[dev] = {}
                    profiles[dev][t] = v
                else:
                    match_def = re.match(r"^(\d{4})=(\d+)", line)
                    if match_def:
                        t = match_def.group(1)
                        v = int(match_def.group(2))
                        if "default" not in profiles:
                            profiles["default"] = {}
                        profiles["default"][t] = v
                        
        self.profiles = profiles
        self.curve_widget.set_profile_data(self.get_profile_for_current_display())
        self.chk_ambient.blockSignals(True)
        self.chk_ambient.setChecked(self.ambient_sensor_enabled)
        self.chk_ambient.blockSignals(False)
        
        # Check autostart status on login
        try:
            autostart_file = os.path.expanduser("~/.config/autostart/auto-brightness-gui.desktop")
            autostart_exists = os.path.exists(autostart_file)
            
            is_minimized = False
            if autostart_exists:
                try:
                    with open(autostart_file, "r") as f:
                        content = f.read()
                        if "--minimized" in content:
                            is_minimized = True
                except Exception:
                    pass
            
            self.chk_autostart.blockSignals(True)
            self.chk_autostart.setChecked(autostart_exists)
            self.chk_autostart.blockSignals(False)
            
            self.chk_autostart_minimized.blockSignals(True)
            self.chk_autostart_minimized.setChecked(is_minimized)
            self.chk_autostart_minimized.setEnabled(autostart_exists)
            self.chk_autostart_minimized.blockSignals(False)
        except Exception:
            pass
            
        self.rebuild_profile_editor()
        
    def rebuild_profile_editor(self):
        for i in reversed(range(self.profile_grid.count())):
            self.profile_grid.itemAt(i).widget().setParent(None)
            
        self.profile_widgets = {}
        
        profile_data = self.get_profile_for_current_display()
        sorted_times = sorted(profile_data.keys())
        
        row = 0
        for t in sorted_times:
            formatted_time = f"{t[:2]}:{t[2:]}"
            
            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            time_edit.setTime(QTime(int(t[:2]), int(t[2:])))
            time_edit.setStyleSheet(
                "background-color: #0d0d14; border: 1px solid #28283a; border-radius: 8px; "
                "padding: 4px 8px; color: #ececee; font-weight: bold; font-family: monospace;"
            )
            time_edit.setFixedWidth(80)
            time_edit.setProperty("old_time", t)
            time_edit.editingFinished.connect(lambda te=time_edit: self.on_profile_time_changed(te))
            
            slider = NoWheelSlider(Qt.Horizontal)
            slider.setRange(5, 100)
            slider.setValue(profile_data[t])
            slider.setFixedHeight(36)
            
            spin = QSpinBox()
            spin.setRange(5, 100)
            spin.setValue(profile_data[t])
            spin.setSuffix("%")
            spin.setFixedWidth(85)
            
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            
            slider.sliderReleased.connect(self.save_profile_config)
            spin.editingFinished.connect(self.save_profile_config)
            
            btn_delete = QPushButton("✕")
            style_danger_icon(btn_delete)
            btn_delete.setFixedWidth(36)
            btn_delete.setFixedHeight(32)
            btn_delete.setToolTip(f"Delete time block {formatted_time}")
            btn_delete.clicked.connect(lambda checked=False, time_key=t: self.delete_profile_block(time_key))
            
            self.profile_grid.addWidget(time_edit, row, 0)
            self.profile_grid.addWidget(slider, row, 1)
            self.profile_grid.addWidget(spin, row, 2)
            self.profile_grid.addWidget(btn_delete, row, 3)
            
            self.profile_widgets[t] = (slider, spin)
            row += 1
            
    def on_profile_time_changed(self, time_edit):
        """Called when a user manually modifies the QTimeEdit for an existing time block."""
        old_time = time_edit.property("old_time")
        new_time = time_edit.time().toString("HHmm")
        if old_time == new_time:
            return
            
        dev = self.get_active_display_dev()
        if dev in self.profiles and old_time in self.profiles[dev]:
            val = self.profiles[dev][old_time]
            # Delete old time key and set new time key
            del self.profiles[dev][old_time]
            self.profiles[dev][new_time] = val
            
            self.save_profile_config()
            self.rebuild_profile_editor()
            self.update_status()

    def save_profile_config(self):
        """Saves current profile coordinates permanently to config file."""
        if not os.path.exists(CONFIG_FILE):
            return
            
        dev = self.get_active_display_dev()
        if dev not in self.profiles:
            self.profiles[dev] = {}
            
        new_values = {}
        for t, (slider, _) in self.profile_widgets.items():
            new_values[t] = slider.value()
            
        self.profiles[dev].update(new_values)
        self.curve_widget.set_profile_data(self.get_profile_for_current_display())
        
        lines = []
        lines.append("# LeanBitLab Adaptive Auto-Brightness Profiles\n")
        lines.append(f"ambient_sensor={'1' if self.ambient_sensor_enabled else '0'}\n")
        lines.append(f"disabled_displays={','.join(self.disabled_displays_list)}\n\n")
        
        # Write default profile first
        lines.append("# Default/Primary Display Profile\n")
        if "default" in self.profiles:
            for t in sorted(self.profiles["default"].keys()):
                lines.append(f"{t}={self.profiles['default'][t]}\n")
        lines.append("\n")
        
        # Write other custom display profiles
        for d in sorted(self.profiles.keys()):
            if d == "default":
                continue
            lines.append(f"# Custom Profile for {d}\n")
            for t in sorted(self.profiles[d].keys()):
                lines.append(f"{d}_{t}={self.profiles[d][t]}\n")
            lines.append("\n")
            
        with open(CONFIG_FILE, "w") as f:
            f.writelines(lines)
            
        self.trigger_script_adjust()

    def toggle_ambient_sensor(self, checked):
        self.ambient_sensor_enabled = checked
        self.save_profile_config()

    def toggle_autostart(self, checked):
        """Enables or disables automatic launch of the GUI control panel on login."""
        self.chk_autostart_minimized.setEnabled(checked)
        self.save_autostart_settings()

    def toggle_autostart_minimized(self, checked):
        """Updates whether the autostart launcher starts the GUI minimized."""
        self.save_autostart_settings()

    def save_autostart_settings(self):
        """Saves current autostart settings to the desktop entry file."""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "auto-brightness-gui.desktop")
        
        if self.chk_autostart.isChecked():
            try:
                os.makedirs(autostart_dir, exist_ok=True)
                bin_path = os.path.expanduser("~/.local/bin/auto-brightness-gui")
                if self.chk_autostart_minimized.isChecked():
                    exec_cmd = f"{bin_path} --minimized"
                else:
                    exec_cmd = bin_path
                    
                content = f"""[Desktop Entry]
Name=Adaptive Brightness
Comment=Configure and monitor adaptive auto-brightness
Exec={exec_cmd}
Icon=video-display
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;
X-GNOME-Autostart-enabled=true
"""
                with open(desktop_file, "w") as f:
                    f.write(content)
            except Exception:
                pass
        else:
            try:
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)
            except Exception:
                pass

    def add_profile_block(self):
        """Adds a manually entered time block to the profile editor list."""
        time_val = self.time_edit.time().toString("HHmm")
        brightness_val = self.spin_brightness_input.value()
        
        dev = self.get_active_display_dev()
        if dev not in self.profiles:
            self.profiles[dev] = {}
            
        self.profiles[dev][time_val] = brightness_val
        
        self.save_profile_config()
        self.rebuild_profile_editor()
        self.update_status()

    def delete_profile_block(self, time_key):
        """Deletes a selected time block from the display profile."""
        dev = self.get_active_display_dev()
        if dev in self.profiles and time_key in self.profiles[dev]:
            if len(self.profiles[dev]) <= 1:
                return
            del self.profiles[dev][time_key]
            
        self.save_profile_config()
        self.rebuild_profile_editor()
        self.update_status()

    def apply_pause(self, duration):
        """Saves target pause epoch or indefinite code to trigger script freeze."""
        now_epoch = int(datetime.now().timestamp())
        try:
            os.makedirs(os.path.dirname(PAUSE_FILE), exist_ok=True)
            with open(PAUSE_FILE, "w") as f:
                if duration == "indefinite":
                    f.write("indefinite\n")
                else:
                    f.write(f"{now_epoch + duration}\n")
        except Exception as e:
            print(f"Error pausing daemon: {e}")
        self.update_status()

    def resume_adjustments(self):
        """Clears paused state and triggers instant correction."""
        if os.path.exists(PAUSE_FILE):
            try:
                os.remove(PAUSE_FILE)
            except Exception:
                pass
        self.update_status()
        self.trigger_script_adjust()

    def update_status(self):
        """Polls system status, pauses, and updates sliders / dial dials."""
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
            
        # 2. Check Temporary Pause state
        self.is_paused = False
        self.pause_remaining = ""
        if os.path.exists(PAUSE_FILE):
            try:
                with open(PAUSE_FILE, "r") as f:
                    content = f.read().strip()
                now_epoch = int(datetime.now().timestamp())
                if content == "indefinite":
                    self.is_paused = True
                    self.pause_remaining = "Indefinite"
                else:
                    target_epoch = int(content)
                    if now_epoch < target_epoch:
                        self.is_paused = True
                        diff = target_epoch - now_epoch
                        h = diff // 3600
                        m = (diff % 3600) // 60
                        self.pause_remaining = f"{h}h {m}m"
                    else:
                        os.remove(PAUSE_FILE)
            except Exception:
                pass
                
        self.act_resume_tray.setVisible(self.is_paused)
        
        # 3. Update badges
        if self.is_paused:
            self.active_badge.setText("☀ BRIGHTNESS <span style='color: #88889a;'>PAUSED</span>")
            self.btn_daemon_toggle.setText("Disable Timer")
            style_secondary(self.btn_daemon_toggle)
            
            self.pause_container.hide()
            self.paused_status_container.show()
            self.lbl_pause_countdown.setText(f"⏸ DAEMON PAUSED ({self.pause_remaining.upper()})")
        else:
            self.paused_status_container.hide()
            self.pause_container.show()
            
            if timer_active:
                self.active_badge.setText("☀ BRIGHTNESS <span style='color: #f0a820;'>ACTIVE</span>")
                self.btn_daemon_toggle.setText("Disable Timer")
                style_secondary(self.btn_daemon_toggle)
            else:
                self.active_badge.setText("☀ BRIGHTNESS <span style='color: #5c5c6e;'>INACTIVE</span>")
                self.btn_daemon_toggle.setText("Enable Timer")
                style_primary(self.btn_daemon_toggle)
                
        self.btn_daemon_toggle.style().unpolish(self.btn_daemon_toggle)
        self.btn_daemon_toggle.style().polish(self.btn_daemon_toggle)
        
        # 4. Update focused display controls card for selected display
        dev = self.get_active_display_dev()
        self._update_focused_display_card()
        
        # Update circular dial with selected display brightness
        try:
            pct_val = get_device_brightness(dev)
            if pct_val is not None:
                self.current_brightness = pct_val
                self.circular_display.setValue(self.current_brightness)
        except Exception:
            pass
            
        # 5. Load active target and time from per-display profile
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        self.curve_widget.set_current_time(cur_min)
        
        target_val = self.curve_widget.get_interpolated_value(cur_min)
        self.lbl_profile_target.setText(f"{target_val}%")
        
        profile_data = self.get_profile_for_current_display()
        sorted_times = sorted(profile_data.keys())
        active_time_str = "0000"
        for t in sorted_times:
            try:
                h = int(t[:2])
                m = int(t[2:])
                min_val = h * 60 + m
                if cur_min >= min_val:
                    active_time_str = t
            except Exception:
                pass
        self.lbl_active_block.setText(f"{active_time_str[:2]}:{active_time_str[2:]}")

    def toggle_daemon(self):
        is_active = ("ACTIVE" in self.active_badge.text() and "INACTIVE" not in self.active_badge.text()) or "PAUSED" in self.active_badge.text()
        action = "stop" if is_active else "start"
        enable_action = "disable" if is_active else "enable"
        
        try:
            subprocess.run(["systemctl", "--user", enable_action, "auto-brightness.timer"])
            subprocess.run(["systemctl", "--user", action, "auto-brightness.timer"])
        except Exception as e:
            print(f"Error toggling systemd service: {e}")
            
        self.update_status()
        
    def trigger_script_adjust(self):
        if os.path.exists(SCRIPT_PATH):
            subprocess.Popen(["bash", SCRIPT_PATH])
            QTimer.singleShot(250, self.update_status)

    @Slot(str)
    def load_logs(self):
        if not os.path.exists(LOG_FILE):
            self.txt_logs.setHtml("<span style='color: #88889a;'>No operation log files found yet.</span>")
            return
            
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()[-80:]
                
            formatted_html = []
            for line in lines:
                line_str = line.strip()
                if "Learned new manual preference" in line_str:
                    colorized = f"<span style='color: #ececee; font-weight: bold;'>{line_str}</span>"
                elif "Ambient sensor active" in line_str:
                    colorized = f"<span style='color: #88889a; font-weight: bold;'>{line_str}</span>"
                elif "Display auto-adjust disabled" in line_str:
                    colorized = f"<span style='color: #e84848; font-weight: bold;'>{line_str}</span>"
                elif "Laptop:" in line_str:
                    colorized = f"<span style='color: #ececee;'>{line_str}</span>"
                else:
                    colorized = f"<span style='color: #88889a;'>{line_str}</span>"
                formatted_html.append(colorized)
                
            self.txt_logs.setHtml("<br>".join(formatted_html))
            scrollbar = self.txt_logs.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self.txt_logs.setHtml(f"<span style='color: #e84848;'>Failed reading logs: {e}</span>")
            
    def clear_logs(self):
        try:
            with open(LOG_FILE, "w") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Log cleared from Control Panel.\n")
        except Exception:
            pass
        self.load_logs()


class FastTooltipStyle(QProxyStyle):
    """Custom proxy style to reduce tooltip popup delay to 100ms."""
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ToolTip_WakeUpDelay:
            return 100
        if hint == QStyle.SH_ToolTip_FallAsleepDelay:
            return 50
        return super().styleHint(hint, option, widget, returnData)


def main():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setStyle(FastTooltipStyle())
    app.setQuitOnLastWindowClosed(False)
    
    gui = BrightnessGUI()
    if "--minimized" not in sys.argv:
        gui.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
