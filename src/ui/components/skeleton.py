"""Reusable UI utility: animated skeleton loader with pulsing opacity effect."""

import random
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect


class QSkeleton(QFrame):
    """Animowany element 'skeleton loader' z efektem pulsowania."""

    def __init__(self, width=None, height=None, radius=6, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: rgba(148, 163, 184, 0.15); border-radius: {radius}px;"
        )
        if width:
            self.setFixedWidth(width)
        if height:
            self.setFixedHeight(height)

        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)

        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(0.2)
        self.anim.setEndValue(0.5)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.setLoopCount(-1)
        # Losowe opóźnienie startu dla naturalnego efektu
        QTimer.singleShot(random.randint(0, 300), self.anim.start)


def clear_layout(layout):
    """Recursively removes all widgets and sub-layouts from *layout*."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        else:
            child_layout = item.layout()
            if child_layout:
                clear_layout(child_layout)
                child_layout.deleteLater()
