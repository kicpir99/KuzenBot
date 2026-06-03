"""AutoWaitScreen — Pulsating "Scanning" view for Auto-Mode."""

import sys, os
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty, QSize
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect, QFrame
from PyQt6.QtGui import QFont, QMovie
from core.translations import _t
from ui.components.skeleton import clear_layout

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

class RatatoskrLoading(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        
        # Ładujemy GIF (użytkownik musi go umieścić w assets/loading.gif)
        self.movie_obj = QMovie(resource_path("assets", "loading.gif"))
        self.setMovie(self.movie_obj)
        self.movie_obj.start()

class AutoWaitScreen(QWidget):
    def __init__(self, switch_manual_cb, parent=None):
        super().__init__(parent)
        self.switch_manual_cb = switch_manual_cb
        self._expanded = True
        self._state = "waiting" # "waiting" lub "choice"
        self._lang_banner_dismissed = False
        self._build_ui()

    def _build_ui(self):
        # Główny layout ekranu
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        self.lang_banner = QFrame()
        self.lang_banner.setObjectName("lang_warning_banner")
        banner_lay = QHBoxLayout(self.lang_banner)
        banner_lay.setContentsMargins(10, 8, 10, 8)
        banner_lay.setSpacing(10)
        
        icon_lbl = QLabel("ℹ️")
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_lay.addWidget(icon_lbl)
        
        self.lang_banner_text = QLabel(_t("lang_warning_ext"))
        self.lang_banner_text.setStyleSheet("color: #93c5fd; font-size: 11px; background: transparent; border: none;")
        self.lang_banner_text.setWordWrap(True)
        banner_lay.addWidget(self.lang_banner_text, 1)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #93c5fd; border: none; font-size: 12px; font-weight: bold; }
            QPushButton:hover { color: #eff6ff; background: rgba(59, 130, 246, 0.3); border-radius: 10px; }
        """)
        close_btn.clicked.connect(self._dismiss_lang_banner)
        banner_lay.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        
        self.lang_banner.setStyleSheet("""
            QFrame#lang_warning_banner {
                background-color: rgba(59, 130, 246, 0.15);
                border: 1px dashed rgba(59, 130, 246, 0.4);
                border-radius: 8px;
            }
        """)
        self.main_layout.addWidget(self.lang_banner)
        self.lang_banner.hide() # domyślnie ukryty

        self.main_layout.addStretch(1)

        # Title (widoczny tylko w Extended)
        self.title_lbl = QLabel(_t("auto_active"))
        self.title_lbl.setStyleSheet("""
            color: #64748b; 
            font-size: 10px; 
            font-weight: 800; 
            letter-spacing: 1px;
        """)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_lbl)

        # Kontener na zawartość, który będzie przebudowywany
        self.container = QFrame()
        self.container.setObjectName("auto_wait_card")
        self.main_layout.addWidget(self.container, 0, Qt.AlignmentFlag.AlignCenter)

        # Tworzymy widżety
        self.robot = RatatoskrLoading()
        
        self.status_lbl = QLabel(_t("wait_lobby"))
        self.status_lbl.setObjectName("mode_desc_lbl")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("font-weight: bold; color: #C5A059; letter-spacing: 1px;")
        self.status_lbl.setWordWrap(True)

        self.btn_manual = QPushButton(_t("manual_mode"))
        self.btn_manual.setObjectName("nav_btn")
        self.btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manual.setFixedHeight(35)
        self.btn_manual.setFixedWidth(220)
        self.btn_manual.clicked.connect(self.switch_manual_cb)

        # Nowe przyciski dla stanu wyboru
        self.btn_yes = QPushButton(_t("yes"))
        self.btn_yes.setObjectName("nav_btn")
        self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yes.setFixedHeight(35)
        self.btn_yes.setFixedWidth(160)

        self.btn_no = QPushButton(_t("no"))
        self.btn_no.setObjectName("nav_btn")
        self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_no.setFixedHeight(35)
        self.btn_no.setFixedWidth(160)

        # NOWOŚĆ: Dolny "rozpychacz", który spycha zawartość do góry (razem z górnym centrują całość)
        self.main_layout.addStretch(1)

        # Inicjalizujemy układ dla trybu Extended
        self._setup_expanded_layout()

    def _setup_expanded_layout(self):
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setSpacing(10)
        self.title_lbl.show()
        self.container.setObjectName("auto_wait_card")
        self.container.setStyleSheet("") 
        self.container.setMinimumSize(450, 350) 
        
        lay = QVBoxLayout(self.container)
        lay.setContentsMargins(50, 50, 50, 50) 
        lay.setSpacing(30)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if self.robot.movie_obj:
            self.robot.movie_obj.setScaledSize(QSize(120, 120))
        self.status_lbl.setStyleSheet("font-weight: bold; color: #C5A059; font-size: 16px; letter-spacing: 1px;")
        
        lay.addWidget(self.robot)
        lay.addWidget(self.status_lbl)
        
        if self._state in ["waiting", "lobby_waiting"]:
            self.btn_manual.setFixedHeight(45)
            self.btn_manual.setFixedWidth(260)
            self.btn_manual.setStyleSheet("font-size: 12px; font-weight: bold;")
            lay.addWidget(self.btn_manual)
            self.btn_manual.show()
            self.btn_yes.hide()
            self.btn_no.hide()
        elif self._state == "choice":
            self.btn_manual.hide()
            self.btn_yes.show()
            self.btn_no.show()
            
            self.btn_yes.setFixedHeight(45)
            self.btn_no.setFixedHeight(45)
            self.btn_yes.setStyleSheet("font-size: 12px; font-weight: bold; background: rgba(34, 197, 94, 0.2); border-color: #22c55e;")
            self.btn_no.setStyleSheet("font-size: 12px; font-weight: bold; background: rgba(239, 68, 68, 0.2); border-color: #ef4444;")
            
            btn_row = QHBoxLayout()
            btn_row.setSpacing(20)
            btn_row.addWidget(self.btn_yes)
            btn_row.addWidget(self.btn_no)
            lay.addLayout(btn_row)

    def _setup_mini_layout(self):
        self.title_lbl.hide()
        self.container.setObjectName("auto_wait_card")
        self.container.setStyleSheet("") 
        self.container.setMinimumSize(0, 0) 
        
        # Redukujemy marginesy zewnętrzne do minimum, aby kafelek mógł urosnąć w pionie
        self.main_layout.setContentsMargins(10, 2, 10, 2)
        self.main_layout.setSpacing(0)
        
        lay = QHBoxLayout(self.container)
        lay.setContentsMargins(15, 10, 15, 10) 
        lay.setSpacing(15)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if self.robot.movie_obj:
            self.robot.movie_obj.setScaledSize(QSize(60, 60))
        lay.addWidget(self.robot)
        
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_lbl.setStyleSheet("font-weight: bold; color: #C5A059; font-size: 12px;")
        right_col.addWidget(self.status_lbl)
        
        if self._state in ["waiting", "lobby_waiting"]:
            self.btn_manual.setFixedHeight(28)
            self.btn_manual.setFixedWidth(180)
            self.btn_manual.setStyleSheet("font-size: 9px;")
            right_col.addWidget(self.btn_manual)
            self.btn_manual.show()
            self.btn_yes.hide()
            self.btn_no.hide()
        elif self._state == "choice":
            self.btn_manual.hide()
            self.btn_yes.show()
            self.btn_no.show()
            
            self.btn_yes.setFixedHeight(32)
            self.btn_no.setFixedHeight(32)
            self.btn_yes.setFixedWidth(110)
            self.btn_no.setFixedWidth(110)
            self.btn_yes.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(34, 197, 94, 0.2); border-color: #22c55e;")
            self.btn_no.setStyleSheet("font-size: 10px; font-weight: bold; background: rgba(239, 68, 68, 0.2); border-color: #ef4444;")
            
            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)
            btn_row.addWidget(self.btn_yes)
            btn_row.addWidget(self.btn_no)
            right_col.addLayout(btn_row)
            
        lay.addLayout(right_col, 1)

    def _rebuild_layout(self):
        # Aktualizacja tekstu w zależności od stanu i trybu
        if self._state == "waiting":
            self.status_lbl.setText(_t("wait_lobby").upper())
        elif self._state == "lobby_waiting":
            self.status_lbl.setText(_t("lobby_detected").upper())
        elif self._state == "choice":
            god = getattr(self, '_current_god_name', '').upper()
            if self._expanded:
                self.status_lbl.setText(_t("session_found_ext").format(god=god))
            else:
                self.status_lbl.setText(_t("session_found_mini").format(god=god))

        if self._expanded and not self._lang_banner_dismissed:
            self.lang_banner.show()
        else:
            self.lang_banner.hide()

        old_lay = self.container.layout()
        if old_lay:
            clear_layout(old_lay) # BEZPIECZNE CZYSZCZENIE Z TWOJEGO SKELETON.PY
            QWidget().setLayout(old_lay) # "Wyrzucenie" layoutu z widgetu

        if self._expanded:
            self._setup_expanded_layout()
        else:
            self._setup_mini_layout()

    def set_expanded(self, expanded: bool):
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._rebuild_layout()

    def show_waiting(self):
        self._state = "waiting" # <--- TEGO BRAKOWAŁO (Resetowanie stanu wewnętrznego)
        self._rebuild_layout()

    def show_lobby_waiting(self):
        self._state = "lobby_waiting" # <--- TEGO BRAKOWAŁO
        self._rebuild_layout()
        
    def show_choice(self, god_name, yes_cb, no_cb):
        self._state = "choice"
        self._current_god_name = god_name
        
        try: self.btn_yes.clicked.disconnect()
        except: pass
        try: self.btn_no.clicked.disconnect()
        except: pass
        
        self.btn_yes.clicked.connect(yes_cb)
        self.btn_no.clicked.connect(no_cb)
        
        self._rebuild_layout()

    def set_status(self, text):
        self.status.setText(text.upper())

    def _dismiss_lang_banner(self):
        """Zamyka baner językowy do końca cyklu życia apki."""
        self._lang_banner_dismissed = True
        self.lang_banner.hide()