"""
In-app notification banner that replaces native QMessageBox dialogs.
A standalone floating window that appears above/below the dashboard.
Supports toast (auto-dismiss) and confirm (Yes/No) modes.
"""

import sys
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, pyqtProperty, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont
from core.utils import SYSTEM_FONT
from ui.widgets.dashboard_button_painter import DashboardButtonPainter
from ui.constants import BANNER_HEIGHT, BANNER_VERTICAL_MARGIN, GRID_MARGIN_LEFT, GRID_MARGIN_RIGHT, ROOT_MARGIN
from ui.visuals.dashboard_effects import (
    draw_aurora_border, draw_rainbow_border, draw_prism_shard_border, draw_liquid_mercury_border
)


GAP = 5  # px gap between dashboard edge and banner


class NotificationBanner(QWidget):
    """Floating notification banner that sits just outside the dashboard window."""

    confirmed = pyqtSignal()
    rejected = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, message: str, banner_type: str = "toast", auto_dismiss_ms: int = 4000,
                 button_style: str = "Gradient", border_effect: str = "None",
                 text_color: str = "#ffffff"):
        super().__init__(None)
        self.banner_type = banner_type
        self._auto_dismiss_ms = auto_dismiss_ms
        self._border_effect = border_effect
        self._slide_origin = 0
        self._target_y = 0

        # Border effect animation (same pattern as dashboard)
        self._border_progress = 0.0
        self.border_anim = QPropertyAnimation(self, b"glow_progress")
        self.border_anim.setDuration(3000)
        self.border_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Window flags — frameless, on top, no taskbar entry
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setMinimumHeight(BANNER_HEIGHT + BANNER_VERTICAL_MARGIN * 2)
        self._hovered = False  # once hovered, disable auto-dismiss

        # Auto-dismiss timer (stoppable)
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._on_dismiss)

        # Slide + fade animation
        self._anim_progress = 0.0
        self._slide_anim = QPropertyAnimation(self, b"windowOpacity")
        self._slide_anim.setDuration(250)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(250)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            GRID_MARGIN_LEFT + ROOT_MARGIN,
            BANNER_VERTICAL_MARGIN,
            GRID_MARGIN_RIGHT + ROOT_MARGIN,
            BANNER_VERTICAL_MARGIN,
        )
        layout.setSpacing(8)

        # Message label
        self.label = QLabel(message)
        self.label.setFont(QFont(SYSTEM_FONT, 11))
        self.label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 1)

        btn_style = (
            "QPushButton {"
            "  background: rgba(255,255,255,0.12);"
            "  border: none;"
            "  border-radius: 4px;"
            "  color: #ccc;"
            "  padding: 2px 10px;"
            f"  font-family: '{SYSTEM_FONT}';"
            "  font-size: 10px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(255,255,255,0.2);"
            "}"
        )

        if banner_type == "confirm":
            btn_h = BANNER_HEIGHT - 8
            use_gradient = button_style == "Gradient"

            if use_gradient:
                yes_bg       = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                                "stop:0 rgb(75,175,75),stop:1 rgb(50,145,50))")
                yes_bg_hover = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                                "stop:0 rgb(90,200,90),stop:1 rgb(65,165,65))")
                no_bg        = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                                "stop:0 rgb(195,65,65),stop:1 rgb(160,45,45))")
                no_bg_hover  = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                                "stop:0 rgb(220,75,75),stop:1 rgb(185,55,55))")
            else:
                yes_bg       = "rgb(55,155,55)"
                yes_bg_hover = "rgb(70,180,70)"
                no_bg        = "rgb(175,55,55)"
                no_bg_hover  = "rgb(205,65,65)"

            yes_style = (
                f"QPushButton {{ background: {yes_bg}; border: none; border-radius: 6px;"
                f"  color: #fff; padding: 4px 20px;"
                f"  font-family: '{SYSTEM_FONT}'; font-size: 11px; font-weight: 500; }}"
                f"QPushButton:hover {{ background: {yes_bg_hover}; }}"
            )
            self.btn_yes = QPushButton("Yes")
            self.btn_yes.setFixedHeight(btn_h)
            self.btn_yes.setMinimumWidth(72)
            self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_yes.setStyleSheet(yes_style)
            self.btn_yes.clicked.connect(self._on_confirm)
            layout.addWidget(self.btn_yes)

            no_style = (
                f"QPushButton {{ background: {no_bg}; border: none; border-radius: 6px;"
                f"  color: #fff; padding: 4px 20px;"
                f"  font-family: '{SYSTEM_FONT}'; font-size: 11px; font-weight: 500; }}"
                f"QPushButton:hover {{ background: {no_bg_hover}; }}"
            )
            self.btn_no = QPushButton("No")
            self.btn_no.setFixedHeight(btn_h)
            self.btn_no.setMinimumWidth(72)
            self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_no.setStyleSheet(no_style)
            self.btn_no.clicked.connect(self._on_reject)
            layout.addWidget(self.btn_no)
        else:
            btn_h = BANNER_HEIGHT - 8
            self.btn_close = QPushButton("\u2715")
            self.btn_close.setFixedSize(btn_h, btn_h)
            self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_close.setStyleSheet(btn_style)
            self.btn_close.clicked.connect(self._on_dismiss)
            layout.addWidget(self.btn_close)

    def show_at(self, x: int, y: int, width: int, slide_from_y: int):
        """Position and show the banner with a slide+fade animation."""
        self.setFixedWidth(width)
        self._target_y = y

        # Start just off-target (slide direction)
        self.move(x, slide_from_y)
        self.setWindowOpacity(0.0)
        self.show()

        # Animate position
        self._pos_anim.setStartValue(QPoint(x, slide_from_y))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.start()

        # Animate opacity
        self._slide_anim.setStartValue(0.0)
        self._slide_anim.setEndValue(1.0)
        self._slide_anim.start()

        # Auto-dismiss timer for toasts
        if self.banner_type == "toast" and self._auto_dismiss_ms > 0:
            self._dismiss_timer.start(self._auto_dismiss_ms)

        # Border effect animation
        if self._border_effect and self._border_effect != "None":
            self.border_anim.stop()
            self.border_anim.setStartValue(0.0)
            self.border_anim.setEndValue(1.0)
            self.border_anim.start()

    def get_glow_progress(self):
        return self._border_progress

    @pyqtSlot(float)
    def set_glow_progress(self, val):
        self._border_progress = val
        self.update()

    glow_progress = pyqtProperty(float, get_glow_progress, set_glow_progress)

    def enterEvent(self, event):
        """Pause auto-dismiss on hover; once hovered it won't auto-dismiss."""
        super().enterEvent(event)
        if self.banner_type == "toast":
            self._hovered = True
            self._dismiss_timer.stop()

    def leaveEvent(self, event):
        """Leave does nothing — user must click X after hovering."""
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(
            ROOT_MARGIN, BANNER_VERTICAL_MARGIN,
            -ROOT_MARGIN, -BANNER_VERTICAL_MARGIN,
        )

        # Solid dark background — match dashboard container style
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 40, 40, 255))
        painter.drawRoundedRect(rect, 8, 8)

        # Subtle border
        painter.setPen(QColor(255, 255, 255, 30))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        # Bevel edge
        DashboardButtonPainter.draw_button_bevel_edge(
            painter, rect,
            intensity_modifier=0.3,
            corner_radius=8,
        )

        # Border effect (runs once on open, same as dashboard)
        if self.border_anim.state() == QPropertyAnimation.State.Running:
            painter.setOpacity(0.7)
            if self._border_effect == 'Rainbow':
                draw_rainbow_border(painter, rect, self._border_progress, width=1)
            elif self._border_effect == 'Aurora Borealis':
                draw_aurora_border(painter, rect, self._border_progress, width=1)
            elif self._border_effect == 'Prism Shard':
                draw_prism_shard_border(painter, rect, self._border_progress, width=1)
            elif self._border_effect == 'Liquid Mercury':
                draw_liquid_mercury_border(painter, rect, self._border_progress, width=1)

        painter.end()

    def _on_confirm(self):
        self.confirmed.emit()

    def _on_reject(self):
        self.rejected.emit()

    def _on_dismiss(self):
        self.dismissed.emit()
