"""Search Screen — manual god search with visual god selector."""

import os,sys
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QScrollArea, QGridLayout,
                             QFrame)
from core.translations import _t

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class SearchScreen(QWidget):
    """God search screen — text input + portrait grid."""
    search_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_gods = []
        self._last_filtered = None
        self.is_mini = False
        self._portrait_cache = {}
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_filter)
        self._build_ui()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 20, 15, 10)
        self.main_layout.setSpacing(15)
        # 1. Search Bar
        self.search_bar_container = QWidget()
        self.search_bar_container.setFixedHeight(45)
        sl = QHBoxLayout(self.search_bar_container)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText(_t("search_ph"))
        self.input.setObjectName("search_input")
        self.input.setFixedHeight(40)
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self._on_search)
        sl.addWidget(self.input)
        self.search_btn = QPushButton(_t("btn_go"))
        self.search_btn.setObjectName("search_btn")
        self.search_btn.setFixedSize(70, 40)
        self.search_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.search_btn.clicked.connect(self._on_search)
        sl.addWidget(self.search_btn)
        self.main_layout.addWidget(self.search_bar_container)

        # 2. Divider / Label
        self.status_label = QLabel(_t("select_god"))
        self.status_label.setStyleSheet("""
            color: #64748b; 
            font-size: 10px; 
            font-weight: 800; 
            letter-spacing: 1px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 3. God Grid Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setObjectName("god_scroll_area")
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Przezroczysty kontener główny scrolla
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Wyrównaj cały kontener do góry

        # Właściwy boks z tłem i siatką
        self.results_box = QWidget()
        from PyQt6.QtWidgets import QSizePolicy
        self.results_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum) # Maksymalnie kurczy się w pionie
        self.results_box.setObjectName("god_results_box")
        self.grid_layout = QGridLayout(self.results_box)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll_layout.addWidget(self.results_box)

        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll, 1)

    # ------------------------------------------------------------- public
    def set_mini_mode(self, is_mini):
        """Switches between grid (expanded) and ribbon (mini) layouts."""
        if self.is_mini != is_mini:
            self.is_mini = is_mini
            if is_mini:
                # Blokada pionowa dla Mini (160px total)
                self.main_layout.setContentsMargins(5, 4, 5, 2)
                self.main_layout.setSpacing(8) 
                self.status_label.hide()
                self.search_bar_container.setFixedHeight(28)
                self.input.setFixedHeight(26)
                self.search_btn.setFixedSize(40, 26)
                self.grid_layout.setContentsMargins(0, 0, 0, 0)
                
                self.scroll.setFixedHeight(52) # Sztywna wysokość pola ikon
                self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                # Instalujemy filtr, aby kółko myszy przewijało w poziomie
                self.scroll.viewport().installEventFilter(self)
            else:
                self.main_layout.setContentsMargins(15, 20, 15, 10)
                self.main_layout.setSpacing(15)
                self.status_label.show()
                self.search_bar_container.setFixedHeight(45)
                self.input.setFixedHeight(40)
                self.search_btn.setFixedSize(70, 40)
                self.grid_layout.setContentsMargins(10, 10, 10, 10)
                
                self.scroll.setFixedHeight(16777215) # QWIDGETSIZE_MAX
                self.scroll.setMaximumHeight(16777215)
                self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.scroll.viewport().removeEventFilter(self)
            
            self._refresh_grid(self._last_filtered or self._all_gods)

    def set_gods(self, god_list, new_gods=None):
        """Sets the base god list and optionally newly added gods."""
        self._portrait_cache.clear()
        self._all_gods = sorted(god_list)
        self._new_gods = set(n.lower() for n in (new_gods or []))
        self._last_filtered = None
        self._refresh_grid(self._all_gods)

    def activate(self):
        """Focuses the search input when entering the screen."""
        from PyQt6.QtCore import QTimer
        # Używamy QTimer.singleShot, aby bezpiecznie przenieść focus po zakończeniu
        # propagacji bieżących zdarzeń (np. mouseRelease z ekranu startowego).
        QTimer.singleShot(50, self._focus_input)

    def _focus_input(self):
        try:
            self.input.setFocus()
            self.input.selectAll()
        except:
            pass

    # ------------------------------------------------------------ internal
    def _on_text_changed(self, text):
        # Za każdym naciśnięciem klawisza odsuwamy wykonanie w czasie o 250ms
        self.search_timer.start(250) 

    def _perform_filter(self):
        # Pobieramy aktualny tekst bezpośrednio z pola input
        text = self.input.text()
        query = text.strip().lower()
        if not query:
            if not self.is_mini: self.status_label.setText(_t("select_god"))
            self._last_filtered = None
            self._refresh_grid(self._all_gods)
            return

        starts_with = [g for g in self._all_gods if g.lower().startswith(query)]
        contains = [g for g in self._all_gods if query in g.lower() and not g.lower().startswith(query)]
        filtered = starts_with + contains

        self._last_filtered = filtered
        if not self.is_mini: self.status_label.setText(_t("found_matches").format(count=len(filtered)))
        self._refresh_grid(filtered)

    def _refresh_grid(self, gods_to_show):
        from ui.components.skeleton import clear_layout
        clear_layout(self.grid_layout)
        
        # Resetujemy wyrównanie siatki na domyślne (Top-Left)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # Resetujemy minimalną wysokość (na wypadek gdyby wcześniej był stan pusty)
        self.results_box.setMinimumHeight(0)

        if not gods_to_show:
            self._show_empty_state()
            return
            
        if self.is_mini:
            # TRYB MINI: Wstążka (1 rząd)
            for i, name in enumerate(gods_to_show):
                portrait = self._make_god_portrait(name)
                self.grid_layout.addWidget(portrait, 0, i)
        else:
            # TRYB EXPANDED: Siatka
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            cols = 6
            for i, name in enumerate(gods_to_show):
                portrait = self._make_god_portrait(name)
                self.grid_layout.addWidget(portrait, i // cols, i % cols)
            
        # KLUCZ: Usuwamy WSZYSTKIE stretche z rzędów i kolumn
        for r in range(self.grid_layout.rowCount()):
            self.grid_layout.setRowStretch(r, 0)
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)

    def _show_empty_state(self):
        # Dla stanu pustego chcemy pełne wyśrodkowanie
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(_t("no_gods_found"))
        msg.setStyleSheet(f"color: #C5A059; font-size: {'14px' if self.is_mini else '20px'}; font-weight: 900; margin-top: {'5px' if self.is_mini else '30px'};")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub = QLabel(_t("try_another_name"))
        sub.setStyleSheet(f"color: #64748b; font-size: {'9px' if self.is_mini else '12px'}; font-weight: 600; margin-bottom: {'5px' if self.is_mini else '30px'}; letter-spacing: 1px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Sprawiamy, że boks ma minimalną wysokość w stanie pustym
        self.results_box.setMinimumHeight(60 if self.is_mini else 150)
        
        self.grid_layout.addWidget(msg, 0, 0)
        self.grid_layout.addWidget(sub, 1, 0)

    def _on_search(self):
        text = self.input.text().strip()
        if not text:
            return
            
        # 1. Dokładne dopasowanie (ignorując wielkość liter)
        exact = [g for g in self._all_gods if g.lower() == text.lower()]
        if exact:
            self._reset_status_label()
            self.search_requested.emit(exact[0])
            return
            
        # 2. Inteligentny wybór pierwszego pasującego bóstwa
        if self._last_filtered:
            self._reset_status_label()
            self.search_requested.emit(self._last_filtered[0])
            return
            
        # 3. Brak dopasowań - błąd
        if not self.is_mini:
            self.status_label.setText(_t("unknown_god"))
            self.status_label.setStyleSheet("""
                color: #ef4444; 
                font-size: 10px; 
                font-weight: 800; 
                letter-spacing: 1px;
            """)
        # Można też wyczyścić input, by dać znać użytkownikowi
        self.input.clear()

    def _reset_status_label(self):
        if not self.is_mini:
            self.status_label.setText(_t("select_god"))
            self.status_label.setStyleSheet("""
                color: #64748b; 
                font-size: 10px; 
                font-weight: 800; 
                letter-spacing: 1px;
            """)


    def _make_god_portrait(self, name):
        container = ClickableFrame()
        container.setObjectName("god_portrait_container")
        
        # Adaptacyjny rozmiar i property dla stylów CSS
        if self.is_mini:
            container.setFixedSize(42, 42) # Jeszcze mniejszy
            container.setProperty("mini", "true")
        else:
            container.setFixedSize(82, 125)
            container.setProperty("mini", "false")
            
        container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        container.style().unpolish(container)
        container.style().polish(container)
        
        cl = QVBoxLayout(container)
        cl.setContentsMargins(2, 2, 2, 2)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter if self.is_mini else Qt.AlignmentFlag.AlignTop)

        # Icon size
        sz = 36 if self.is_mini else 60

        # Icon
        icon = QLabel()
        icon.setFixedSize(sz, sz)
        icon.setObjectName("god_portrait_img")
        
        from core.image_manager import ImageManager
        path = ImageManager().get_god_portrait_path(name)
        
        if not path or not os.path.exists(path):
            slug = name.lower().strip().replace(" ", "-").replace("'", "")
            path = resource_path("assets", "gods", f"{slug}.png")
        # -----------------------------------------------------------
        
        cache_key = (name, sz)
        if cache_key in self._portrait_cache:
            pix = self._portrait_cache[cache_key]
            if pix is not None:
                icon.setPixmap(pix)
            else:
                self._set_placeholder(icon, name, sz)
        else:
            if os.path.exists(path):
                pix = QPixmap(path)
                if not pix.isNull():
                    scaled_pix = pix.scaled(
                        sz, sz, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    icon.setPixmap(scaled_pix)
                    self._portrait_cache[cache_key] = scaled_pix
                else:
                    self._set_placeholder(icon, name, sz)
                    self._portrait_cache[cache_key] = None
            else:
                self._set_placeholder(icon, name, sz)
                self._portrait_cache[cache_key] = None
        
        cl.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        # NEW badge for recently added gods
        if name.lower() in getattr(self, '_new_gods', set()):
            if not self.is_mini:
                badge = QLabel(_t("badge_new"))
                badge.setStyleSheet("""
                    QLabel {
                        background-color: #22c55e;
                        color: #052e16;
                        font-size: 7px;
                        font-weight: 900;
                        padding: 1px 4px;
                        border-radius: 3px;
                        letter-spacing: 0.5px;
                    }
                """)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cl.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)

        # Name (Tylko w trybie Expanded)
        if not self.is_mini:
            lbl = QLabel(name)
            lbl.setObjectName("god_portrait_name")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(35)
            cl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignTop)
            cl.addStretch()

        # Click event - safe Qt signal connection
        container.clicked.connect(lambda: self.search_requested.emit(name))
        
        return container

    def _set_placeholder(self, icon, name, sz):
        icon.setText(name[0])
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fs = 14 if self.is_mini else 20
        br = sz // 2
        icon.setStyleSheet(f"color: #C5A059; font-size: {fs}px; font-weight: bold; border-radius: {br}px;")

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.scroll.viewport() and event.type() == QEvent.Type.Wheel:
            # Przekieruj kółko myszy na przewijanie poziome
            self.scroll.horizontalScrollBar().setValue(
                self.scroll.horizontalScrollBar().value() - event.angleDelta().y()
            )
            return True
        return super().eventFilter(obj, event)

