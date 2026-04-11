from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from ui.widgets.dashboard_button_painter import DashboardButtonPainter
from ui.constants import PAGE_INDICATOR_WIDTH, FOOTER_HEIGHT


class PageIndicatorButton(QPushButton):
    """Footer button showing page indicator dots. Scroll or click to change page."""

    page_scrolled = pyqtSignal(int)   # delta: +1 / -1
    page_jumped = pyqtSignal(int)     # absolute page index from click

    # Dot appearance
    ACTIVE_DIAMETER = 8
    INACTIVE_DIAMETER = 6
    DOT_SPACING = 14      # center-to-center
    ACTIVE_OPACITY = 255
    INACTIVE_OPACITY = 90  # ~35%

    button_style = 'Gradient'

    def __init__(self, page_count: int = 3, current_page: int = 0, parent=None):
        super().__init__(parent)
        self._page_count = page_count
        self._current_page = current_page

        self.setFixedSize(PAGE_INDICATOR_WIDTH, FOOTER_HEIGHT)
        self.setText("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_page(self, index: int) -> None:
        self._current_page = index
        self.update()

    def set_page_count(self, n: int) -> None:
        self._page_count = n
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._page_count < 1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2  # vertical center

        # Total horizontal span of all dot centers
        total_span = (self._page_count - 1) * self.DOT_SPACING
        start_x = (w - total_span) / 2

        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self._page_count):
            cx = start_x + i * self.DOT_SPACING
            is_active = (i == self._current_page)

            diameter = self.ACTIVE_DIAMETER if is_active else self.INACTIVE_DIAMETER
            opacity = self.ACTIVE_OPACITY if is_active else self.INACTIVE_OPACITY
            radius = diameter / 2

            color = QColor(255, 255, 255, opacity)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

        DashboardButtonPainter.draw_button_bevel_edge(
            painter,
            QRectF(self.rect()),
            intensity_modifier=0.25,
            corner_radius=4,
        )

        painter.end()

    def _dot_index_at(self, x: float) -> int:
        """Return the dot index at position x, or -1 if none."""
        if self._page_count < 1:
            return -1
        total_span = (self._page_count - 1) * self.DOT_SPACING
        start_x = (self.width() - total_span) / 2
        hit_radius = self.DOT_SPACING / 2
        for i in range(self._page_count):
            cx = start_x + i * self.DOT_SPACING
            if abs(x - cx) <= hit_radius:
                return i
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._dot_index_at(event.position().x())
            if idx >= 0 and idx != self._current_page:
                self.page_jumped.emit(idx)
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.page_scrolled.emit(-1)  # scroll up → previous page
        elif delta < 0:
            self.page_scrolled.emit(1)   # scroll down → next page
        event.accept()
