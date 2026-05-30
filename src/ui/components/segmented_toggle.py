"""SegmentedToggle — a premium glassmorphic sliding switch."""

from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QLabel
from PyQt6.QtCore import pyqtSignal, QPropertyAnimation, QRect, Qt, QEasingCurve
from PyQt6.QtGui import QCursor
from core.translations import _t

class SegmentedToggle(QWidget):
    valueChanged = pyqtSignal(str)  # Emits "builds" or "stats"

    def __init__(self, parent=None, size_mode="standard"):
        super().__init__(parent)
        self.active_value = "builds"
        self.size_mode = size_mode  # "standard" lub "compact"
        self._build_ui()

    def _build_ui(self):
        # Definicja wymiarów w zależności od trybu
        if self.size_mode == "compact":
            w, h = 180, 28
            self._slider_w, self._slider_h = 86, 24
            self._target_builds = 2
            self._target_stats = 92
            half_w = 90
        else:
            w, h = 220, 36
            self._slider_w, self._slider_h = 106, 32
            self._target_builds = 2
            self._target_stats = 112
            half_w = 110

        self.setFixedSize(w, h)
        
        # 1. Główne Tło (Dynamiczny radius)
        self.bg = QFrame(self)
        self.bg.setGeometry(0, 0, w, h)
        self.bg.setStyleSheet(f"QFrame {{ background-color: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: {h//2}px; }}")

        # 2. Pigułka (Slider)
        self.slider = QFrame(self.bg)
        self.slider.setGeometry(2, 2, self._slider_w, self._slider_h)
        self.slider.setStyleSheet(f"background-color: #3b82f6; border-radius: {self._slider_h//2}px;")

        # 3. STATYCZNE TEKSTY nałożone na wierzch
        self.label_builds = QLabel(_t("builds_toggle"), self.bg)
        self.label_builds.setGeometry(0, 0, half_w, h)
        self.label_builds.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_builds.setContentsMargins(0, 0, 0, 0)
        self.label_builds.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.label_stats = QLabel(_t("stats_toggle"), self.bg)
        self.label_stats.setGeometry(half_w, 0, half_w, h)
        self.label_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_stats.setContentsMargins(0, 0, 0, 0)
        self.label_stats.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # 4. Niewidoczne przyciski do klikania
        self.btn_builds = QPushButton(self)
        self.btn_builds.setGeometry(0, 0, half_w, h)
        self.btn_builds.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_builds.setStyleSheet("background: transparent; border: none;")
        self.btn_builds.clicked.connect(lambda: self.set_value("builds"))

        self.btn_stats = QPushButton(self)
        self.btn_stats.setGeometry(half_w, 0, half_w, h)
        self.btn_stats.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stats.setStyleSheet("background: transparent; border: none;")
        self.btn_stats.clicked.connect(lambda: self.set_value("stats"))

        # Ustawienie początkowych kolorów tekstów
        self._update_text_colors("builds")

    def _update_text_colors(self, active_val):
        """Changes static text colors based on the active option."""
        # --- Magia trybu compact --- Mniejsza czcionka dopasowana do filtrów!
        fs = "10px" if self.size_mode == "compact" else "12px"
        active_style = f"color: white; font-weight: 600; font-size: {fs}; background: transparent; padding-top: 1px;"
        inactive_style = f"color: #94a3b8; font-weight: 400; font-size: {fs}; background: transparent; padding-top: 1px;"
        
        if active_val == "builds":
            self.label_builds.setStyleSheet(active_style)
            self.label_stats.setStyleSheet(inactive_style)
        else:
            self.label_builds.setStyleSheet(inactive_style)
            self.label_stats.setStyleSheet(active_style)

    def set_value(self, val, animate=True):
        if val == self.active_value:
            return
            
        if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.State.Running:
            return

        self.active_value = val
        self.btn_builds.setEnabled(False)
        self.btn_stats.setEnabled(False)
        
        target_x = self._target_builds if val == "builds" else self._target_stats
        
        # Od razu "podświetlamy" docelowy napis
        self._update_text_colors(val)
        
        if animate:
            self.anim = QPropertyAnimation(self.slider, b"geometry")
            self.anim.setDuration(240)
            self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.anim.setStartValue(self.slider.geometry())
            self.anim.setEndValue(QRect(target_x, 2, self._slider_w, self._slider_h))
            self.anim.finished.connect(self._on_anim_finished)
            self.anim.start()
        else:
            self.slider.setGeometry(target_x, 2, self._slider_w, self._slider_h)
            self._on_anim_finished()

        self.valueChanged.emit(val)

    def _on_anim_finished(self):
        self.btn_builds.setEnabled(True)
        self.btn_stats.setEnabled(True)

    def set_theme(self, theme_key):
        """Updates toggle pill color based on the selected theme."""
        gradients = {
            "gold": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 #eab308)",
            "ruby": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9f1239, stop:1 #e11d48)",
            "blizzard": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #3b82f6)",
            "emerald": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15803d, stop:1 #22c55e)",
            "void": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6d28d9, stop:1 #8b5cf6)",
            "cyber": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be185d, stop:1 #ec4899)",
            "toxic": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4d7c0f, stop:1 #84cc16)",
            "abyss": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7f1d1d, stop:1 #dc2626)"
        }
        grad = gradients.get(theme_key, gradients["gold"])
        radius = self._slider_h // 2
        self.slider.setStyleSheet(f"background: {grad}; border-radius: {radius}px;")