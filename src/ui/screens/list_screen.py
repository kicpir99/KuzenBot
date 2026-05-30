"""List Screen — paginated build cards with filter bar."""

import os, sys
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor, QFont, QIcon
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QSizePolicy, QGraphicsOpacityEffect)

from ui.components.skeleton import QSkeleton, clear_layout
from ui.components.segmented_toggle import SegmentedToggle
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


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class ItemTooltip(QFrame):
    def __init__(self, alternatives, icon_factory):
        super().__init__()
        self.setObjectName("item_tooltip")
        self.setStyleSheet("""
            QFrame#item_tooltip {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(5)
        
        for alt in alternatives:
            row = QHBoxLayout()
            icon = icon_factory(alt["item"], 24)
            pct = QLabel(f"{alt['pct']}%")
            pct.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
            row.addWidget(icon)
            row.addWidget(pct)
            lay.addLayout(row)

class ListScreen(QWidget):
    """Build list screen with cards, filter bar, and pagination."""

    build_selected = pyqtSignal(int)   # globalny indeks buildu
    role_filter_clicked = pyqtSignal()
    aspect_filter_clicked = pyqtSignal()
    source_changed = pyqtSignal(str)
    retry_requested = pyqtSignal()

    def __init__(self, icon_factory=None, role_click_cb=None, aspect_click_cb=None, parent=None, colorizer=None):
        super().__init__(parent)
        self._icon_factory = icon_factory
        self._colorizer = colorizer
        self._icon_factory = icon_factory
        self._all_builds = []
        self._current_page = 0
        self._items_per_page = 5
        self.is_mini = False
        self._is_skeleton = False
        self._aspect_banner_dismissed = False
        self._set_role_filter_cb = role_click_cb
        self._set_aspect_filter_cb = aspect_click_cb
        
        # Wczytywanie bazy przedmiotów w celu wykrywania starterów
        self.item_db = {}
        import json
        import os
        items_path = resource_path("assets", "items.json")
        if os.path.exists(items_path):
            try:
                with open(items_path, "r", encoding="utf-8") as f:
                    self.item_db = json.load(f)
            except:
                pass
                
        self.current_patch = None
        self._build_ui()

    def set_mini_mode(self, is_mini):
        """Switches between card view and compact list view."""
        self.is_mini = is_mini
        
        # Ukrywamy na chwilę, by uniknąć migotania i wymusić przeliczenie
        self.scroll.hide()
        
        self.filter_bar.setVisible(not is_mini)
        self.pagination.setVisible(not is_mini and len(self._all_builds) > self._items_per_page)
        
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if is_mini else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list_layout.setSpacing(4 if is_mini else 8)
        
        if self._is_skeleton:
            self.show_skeleton()
        else:
            self.populate(self._all_builds)

        # Wymuszamy odświeżenie geometrii i natychmiastowe przeliczenie layoutu
        self._list_widget.adjustSize()
        self.scroll.show()
        self.scroll.verticalScrollBar().setValue(0)
        self.updateGeometry() # Wymuszenie aktualizacji geometrii widgetu
        self.parent().adjustSize() # Wymuszenie aktualizacji okna nadrzędnego



    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # --- Filter bar (contains filters + engine toggle) ---
        self.filter_bar = QWidget()
        fb = QHBoxLayout(self.filter_bar)
        fb.setContentsMargins(0, 0, 0, 0)
        fb.setSpacing(8)

        self.btn_role = QPushButton(f" {_t('role_any')}") 
        self.btn_role.setObjectName("filter_btn")
        self.btn_role.setFixedHeight(28)
        self.btn_role.setMinimumWidth(100)
        self.btn_role.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        from PyQt6.QtGui import QIcon
        if hasattr(self, '_colorizer') and self._colorizer:
            # Wymuszamy pokolorowanie "Any" już przy starcie
            colored_icon = self._colorizer(resource_path("assets", "role_any_mask.svg"), "#94a3b8")
            self.btn_role.setIcon(colored_icon)
        else:
            self.btn_role.setIcon(QIcon(resource_path("assets", "role_any_mask.svg")))
            
        self.btn_role.setIconSize(QSize(16, 16))
        
        # Pamiętaj, żeby dodać też to połączenie, jeśli go nie masz:
        self.btn_role.clicked.connect(self.role_filter_clicked.emit)

        self.btn_aspect = QPushButton(f" {_t('aspect_off')}")
        self.btn_aspect.setObjectName("filter_btn")
        self.btn_aspect.setFixedHeight(28)
        self.btn_aspect.setMinimumWidth(100)
        self.btn_aspect.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_aspect.setIcon(QIcon(resource_path("assets", "aspect_off.png")))
        self.btn_aspect.setIconSize(QSize(16, 16))
        self.btn_aspect.clicked.connect(self.aspect_filter_clicked.emit)

        fb.addWidget(self.btn_role)
        fb.addWidget(self.btn_aspect)
        fb.addStretch() # Space between filters and toggle

        # --- Engine Selector ---
        self.toggle = SegmentedToggle(self, size_mode="compact")
        self.toggle.valueChanged.connect(self._on_toggle_changed)
        fb.addWidget(self.toggle)
        
        root.addWidget(self.filter_bar)

        # --- Scroll area (cards) ---
        self.scroll = QScrollArea()
        self.scroll.setObjectName("build_list_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self._list_widget)
        root.addWidget(self.scroll, 1)

        # --- Pagination ---
        self.pagination = QWidget()
        pl = QHBoxLayout(self.pagination)
        pl.setContentsMargins(0, 5, 0, 5)

        self.btn_prev_page = QPushButton(_t("btn_prev"))
        self.btn_prev_page.setObjectName("nav_btn")
        # Zamiast FixedSize ustawiamy tylko sztywną wysokość, a szerokość robi się elastyczna:
        self.btn_prev_page.setFixedHeight(26)
        # Nadpisujemy styl, dodając wewnętrzny margines dla tekstu (padding)
        self.btn_prev_page.setStyleSheet("padding: 0px 15px;") 
        self.btn_prev_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        sp_prev = self.btn_prev_page.sizePolicy()
        sp_prev.setRetainSizeWhenHidden(True)
        self.btn_prev_page.setSizePolicy(sp_prev)
        self.btn_prev_page.clicked.connect(self._prev_page)

        self.page_label = QLabel(_t("page_indicator").format(current=1, total=1))
        self.page_label.setObjectName("card_meta")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next_page = QPushButton(_t("btn_next"))
        self.btn_next_page.setObjectName("nav_btn")
        # Zamiast FixedSize ustawiamy tylko sztywną wysokość:
        self.btn_next_page.setFixedHeight(26)
        self.btn_next_page.setStyleSheet("padding: 0px 15px;")
        self.btn_next_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        sp_next = self.btn_next_page.sizePolicy()
        sp_next.setRetainSizeWhenHidden(True)
        self.btn_next_page.setSizePolicy(sp_next)
        self.btn_next_page.clicked.connect(self._next_page)

        pl.addWidget(self.btn_prev_page)
        pl.addStretch()
        pl.addWidget(self.page_label)
        pl.addStretch()
        pl.addWidget(self.btn_next_page)
        self.pagination.hide()
        root.addWidget(self.pagination)

    def populate(self, builds, god_name="", current_patch=None, error_message=None):
        """Populates the list with build cards. Supports pagination or mini-listing."""
        self._is_skeleton = False
        self._all_builds = builds
        
        
        if god_name:
            self._current_god_name = god_name
            self._current_page = 0
        else:
            # Gdy aplikacja odświeża układ i nie poda nazwy, używamy tej zapisanej
            god_name = getattr(self, '_current_god_name', "")

        print(f"[DEBUG] populate: current_patch={current_patch}")
        if current_patch and current_patch.lower() != "unknown":
            self.current_patch = current_patch
        else:
            # Fallback - automatyczne wykrycie najwyższego patcha z listy buildów
            max_num = 0
            best_patch = None
            import re
            for b in builds:
                if b.patch:
                    m = re.search(r'(?i)ob(\d+)', b.patch)
                    if m:
                        num = int(m.group(1))
                        if num > max_num:
                            max_num = num
                            best_patch = b.patch
            if best_patch:
                self.current_patch = best_patch
            else:
                self.current_patch = "OB35.0"

        clear_layout(self._list_layout)

        # --- JEDYNE TWORZENIE BANERA (brak duplikatów) ---
        if builds and getattr(builds[0], 'is_stats', False):
            if god_name.lower() == "ratatoskr":
                banner = QFrame()
                banner.setObjectName("ratatoskr_banner")
                banner_lay = QHBoxLayout(banner)
                
                info_text = _t("ratatoskr_acorn_ext")
                mini_text = _t("ratatoskr_acorn_mini")
                
                if self.is_mini:
                    banner.setStyleSheet("background: transparent; border: none; margin: 0px; padding: 0px;")
                    banner_lay.setContentsMargins(0, 0, 0, 2)
                    
                    badge = QLabel(mini_text)
                    badge.setStyleSheet("""
                        background-color: rgba(245, 158, 11, 0.15);
                        border: 1px dashed rgba(245, 158, 11, 0.4);
                        border-radius: 6px;
                        color: #fbbf24;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 8px;
                    """)
                    
                    badge.setObjectName("mode_info_btn")
                    badge.setProperty("info_text", info_text) 
                    badge.installEventFilter(self.window())
                    badge.setCursor(Qt.CursorShape.WhatsThisCursor)
                    
                    banner_lay.addStretch()
                    banner_lay.addWidget(badge)
                    banner_lay.addStretch()
                    
                else:
                    banner.setStyleSheet("""
                        QFrame#ratatoskr_banner {
                            background-color: rgba(245, 158, 11, 0.15);
                            border: 1px dashed rgba(245, 158, 11, 0.4);
                            border-radius: 8px;
                        }
                    """)
                    banner_lay.setContentsMargins(10, 8, 10, 8)
                    banner_lay.setSpacing(10)
                    
                    if self._icon_factory:
                        icon_lbl = self._icon_factory("Acorn", 32)
                        icon_lbl.setStyleSheet("background: transparent; border: none;")
                    else:
                        icon_lbl = QLabel("🌰") 
                        icon_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")
                        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                    banner_lay.addWidget(icon_lbl)
                    
                    text_lbl = QLabel(info_text)
                    text_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold; background: transparent; border: none;")
                    text_lbl.setWordWrap(True)
                    banner_lay.addWidget(text_lbl, 1)
                
                self._list_layout.addWidget(banner)
                
            # NOWOŚĆ: Baner informacyjny dla całej reszty postaci (jeśli nie został zamknięty "X")
            elif not self._aspect_banner_dismissed:
                banner = QFrame()
                banner.setObjectName("aspect_warning_banner")
                banner_lay = QHBoxLayout(banner)
                
                # Zabezpieczamy referencję, żeby móc ukryć baner po kliknięciu
                def dismiss_banner():
                    self._aspect_banner_dismissed = True
                    banner.hide()
                
                info_text = _t("aspect_bug_ext")
                mini_text = _t("aspect_bug_mini")
                
                if self.is_mini:
                    banner.setStyleSheet("background: transparent; border: none; margin: 0px; padding: 0px;")
                    banner_lay.setContentsMargins(0, 0, 0, 2)
                    
                    badge = QLabel(mini_text)
                    badge.setStyleSheet("""
                        background-color: rgba(59, 130, 246, 0.15);
                        border: 1px dashed rgba(59, 130, 246, 0.4);
                        border-radius: 6px;
                        color: #93c5fd;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 8px;
                    """)
                    badge.setObjectName("mode_info_btn")
                    badge.setProperty("info_text", info_text) 
                    badge.installEventFilter(self.window())
                    badge.setCursor(Qt.CursorShape.WhatsThisCursor)
                    
                    close_btn = QPushButton("✕")
                    close_btn.setFixedSize(16, 16)
                    close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    close_btn.setStyleSheet("""
                        QPushButton { background: transparent; color: #93c5fd; border: none; font-size: 10px; font-weight: bold; }
                        QPushButton:hover { color: #eff6ff; background: rgba(59, 130, 246, 0.3); border-radius: 8px; }
                    """)
                    close_btn.clicked.connect(dismiss_banner)
                    
                    banner_lay.addStretch()
                    banner_lay.addWidget(badge)
                    banner_lay.addWidget(close_btn)
                    banner_lay.addStretch()
                    
                else:
                    banner.setStyleSheet("""
                        QFrame#aspect_warning_banner {
                            background-color: rgba(59, 130, 246, 0.15);
                            border: 1px dashed rgba(59, 130, 246, 0.4);
                            border-radius: 8px;
                        }
                    """)
                    banner_lay.setContentsMargins(10, 8, 10, 8)
                    banner_lay.setSpacing(10)
                    
                    # --- PODMIENIONA IKONA ---
                    icon_lbl = QLabel()
                    icon_lbl.setStyleSheet("background: transparent; border: none;")
                    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    from PyQt6.QtGui import QPixmap
                    import os
                    
                    icon_path = resource_path("assets", "aspect_off.png")
                    pix = QPixmap(icon_path)
                    if not pix.isNull():
                        # Skalujemy grafikę do ładnego rozmiaru 20x20 z wygładzaniem
                        icon_lbl.setPixmap(pix.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    else:
                        # Fallback w razie braku pliku
                        icon_lbl.setText("ℹ️")
                        icon_lbl.setStyleSheet("font-size: 18px; background: transparent; border: none;")
                    # -------------------------
                    
                    banner_lay.addWidget(icon_lbl)
                    
                    text_lbl = QLabel(info_text)
                    text_lbl.setStyleSheet("color: #93c5fd; font-size: 11px; background: transparent; border: none;")
                    text_lbl.setWordWrap(True)
                    banner_lay.addWidget(text_lbl, 1)
                    
                    close_btn = QPushButton("✕")
                    close_btn.setFixedSize(20, 20)
                    close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    close_btn.setStyleSheet("""
                        QPushButton { background: transparent; color: #93c5fd; border: none; font-size: 12px; font-weight: bold; }
                        QPushButton:hover { color: #eff6ff; background: rgba(59, 130, 246, 0.3); border-radius: 10px; }
                    """)
                    close_btn.clicked.connect(dismiss_banner)
                    
                    banner_lay.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
                
                self._list_layout.addWidget(banner)
        # -------------------------------------------------

        if not builds:
            self._show_empty(error_message=error_message)
            self.pagination.hide()
            return

        if self.is_mini:
            # W trybie MINI pokazujemy wszystkie buildy w jednej przewijalnej liście
            for build in builds:
                row = self._make_mini_build_row(build)
                self._list_layout.addWidget(row)
            self.pagination.hide()
        else:
            # Tryb EXPANDED z paginacją
            total = len(builds)
            total_pages = (total - 1) // self._items_per_page + 1
            start = self._current_page * self._items_per_page
            end = start + self._items_per_page
            page_builds = builds[start:end]

            count_lbl = QLabel(
                _t("showing_builds").format(start=start+1, end=min(end, total), total=total)
            )
            count_lbl.setObjectName("card_meta")
            count_lbl.setStyleSheet("margin-bottom: 5px;")
            self._list_layout.addWidget(count_lbl)

            for build in page_builds:
                card = self._make_build_card(build)
                self._list_layout.addWidget(card)

            # Pagination update
            self.page_label.setText(_t("page_indicator").format(current=self._current_page + 1, total=total_pages))
            self.btn_prev_page.setVisible(self._current_page > 0)
            self.btn_next_page.setVisible(self._current_page < total_pages - 1)
            self.pagination.setVisible(total_pages > 1)

        self._list_layout.addStretch()

    def style_patch_badge(self, label, patch_str, current_patch, font_size_px=9):
        import re
        def get_patch_number(p_str):
            if not p_str:
                return 0
            m = re.search(r'(?i)ob(\d+)', p_str)
            if m:
                return int(m.group(1))
            m2 = re.search(r'(\d+)', p_str)
            if m2:
                return int(m2.group(1))
            return 0

        p_num = get_patch_number(patch_str)
        curr_num = get_patch_number(current_patch)
        
        bg_color = "rgba(40, 50, 70, 0.6)"
        border_color = "rgba(148, 163, 184, 0.2)"
        text_color = "#94a3b8"
        
        if p_num > 0 and curr_num > 0:
            diff = curr_num - p_num
            if diff <= 0:
                # Obecny patch (zielony)
                bg_color = "rgba(16, 185, 129, 0.15)"
                border_color = "rgba(16, 185, 129, 0.4)"
                text_color = "#34d399"
            elif diff <= 3:
                # Do 3 patchy wstecz (żółty)
                bg_color = "rgba(245, 158, 11, 0.15)"
                border_color = "rgba(245, 158, 11, 0.4)"
                text_color = "#fbbf24"
            else:
                # Starsze patche (czerwony)
                bg_color = "rgba(239, 68, 68, 0.15)"
                border_color = "rgba(239, 68, 68, 0.4)"
                text_color = "#f87171"
                
        label.setStyleSheet(f"""
            background: {bg_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            color: {text_color};
            font-size: {font_size_px}px;
            font-weight: bold;
            padding: 1px 5px;
        """)

    def _make_mini_build_row(self, build):
        """Creates a compact build card for Mini mode (68px height)."""
        if getattr(build, 'insufficient_data', False):
            card = QFrame()
            card.setObjectName("mini_build_row")
            card.setStyleSheet("""
                QFrame#mini_build_row {
                    background-color: rgba(239, 68, 68, 0.05);
                    border: 1px dashed rgba(239, 68, 68, 0.25);
                    border-radius: 8px;
                }
                QFrame#mini_build_row:hover {
                    background-color: rgba(239, 68, 68, 0.09);
                    border-color: rgba(239, 68, 68, 0.45);
                }
            """)
            card.setFixedHeight(68)
            
            layout = QVBoxLayout(card)
            layout.setContentsMargins(15, 6, 15, 6)
            layout.setSpacing(2)
            
            display_title = build.title
            if getattr(build, 'is_stats', False):
                display_title = build.title.split(" (Meta Stats -")[0]
            title = QLabel(display_title)
            title.setStyleSheet("font-size: 11px; font-weight: bold; color: #f8fafc;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setWordWrap(True)
            
            reason = build.stats_data.get("insufficient_reason_mini") if build.stats_data else None
            if not reason:
                role_val = build.roles[0] if build.roles else _t('role_any')
                reason = _t("err_low_stats_mini").format(role=role_val, count=build.upvotes)
            msg = QLabel(reason)
            msg.setStyleSheet("font-size: 10px; color: #f87171; font-weight: bold;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setWordWrap(True)
            
            layout.addWidget(title)
            layout.addWidget(msg)
            return card

        card = ClickableFrame()
        card.setObjectName("mini_build_row")
        card.setFixedHeight(68)
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        # --- Top Row (Tytuł + Patch + Role) ---
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        
        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        
        if build.is_aspect:
            aspect_icon = QLabel("⚡")
            aspect_icon.setStyleSheet("color: #3b82f6; font-weight: bold;")
            title_row.addWidget(aspect_icon)
            
        display_title = build.title
        if getattr(build, 'is_stats', False):
            display_title = build.title.split(" (Meta Stats -")[0]
            
        title = QLabel(display_title)
        title.setObjectName("mini_build_title")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #f8fafc;")
        
        # Elidowanie tekstu jeśli jest za długi (zmniejszono limit do 140px, bez elidowania dla stats)
        if getattr(build, 'is_stats', False):
            title.setText(display_title)
        else:
            fm = title.fontMetrics()
            elided_title = fm.elidedText(display_title, Qt.TextElideMode.ElideRight, 140)
            title.setText(elided_title)
        
        title_row.addWidget(title)
        title_row.addStretch()
        
        top_row.addLayout(title_row)

        # Role (skrócone)
        if build.roles:
            role_text = "/".join(build.roles)
            role_lbl = QLabel(role_text)
            role_lbl.setStyleSheet("font-size: 9px; color: #94a3b8; font-weight: bold;")
            top_row.addWidget(role_lbl)

        # Patch Badge (Nowość w Mini)
        patch_badge = QLabel(build.patch)
        self.style_patch_badge(patch_badge, build.patch, self.current_patch, font_size_px=9)
        top_row.addWidget(patch_badge)
        
        layout.addLayout(top_row)

        # --- Bottom Row (Ikony Przedmiotów + Upvotes) ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        items_lay = QHBoxLayout()
        items_lay.setSpacing(4)
        if self._icon_factory:
            if getattr(build, 'is_stats', False):
                # Stats view (Mini) – dedup across slots
                display_items = []
                used = set()
                # Starter
                if build.stats_data.get("starter"):
                    best = build.stats_data["starter"][0]
                    used.add(best["item"].lower().strip().replace("'", "'"))
                    display_items.append({"icon": self._icon_factory(best["item"], 28), "pct": best["pct"], "alts": build.stats_data["starter"][1:]})
                # Slots
                for slot in build.stats_data.get("slots", []):
                    if slot:
                        chosen = slot[0]
                        for i, c in enumerate(slot):
                            name = c["item"].lower().strip().replace("'", "'")
                            if name not in used:
                                chosen = c
                                used.add(name)
                                break
                        display_items.append({"icon": self._icon_factory(chosen["item"], 28), "pct": chosen["pct"], "alts": [s for s in slot if s["item"] != chosen["item"]]})
                # Relic
                if build.stats_data.get("relic"):
                    best = build.stats_data["relic"][0]
                    display_items.append({"icon": self._icon_factory(best["item"], 28), "pct": best["pct"], "alts": build.stats_data["relic"][1:]})

                for item_info in display_items:
                    item_container = QWidget()
                    item_cont_lay = QVBoxLayout(item_container)
                    item_cont_lay.setContentsMargins(0, 0, 0, 0)
                    item_cont_lay.setSpacing(1)
                    item_cont_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    item_cont_lay.addWidget(item_info["icon"])
                    
                    # pct_lbl = QLabel(f"{item_info['pct']}%")
                    # pct_lbl.setStyleSheet("font-size: 8px; color: #94a3b8; font-weight: bold;")
                    # pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # item_cont_lay.addWidget(pct_lbl)
                    
                    if item_info["alts"]:
                        tt = f"{_t('alternatives')}<br>" + "<br>".join([f"{a['item']}: {a['pct']}%" for a in item_info["alts"]])
                        item_container.setToolTip(tt)
                        
                    items_lay.addWidget(item_container)
            else:
                # Regular view (Mini)
                has_starter_or_items = False
                # 1. Starter
                if hasattr(build, 'starter_items') and build.starter_items:
                    starter_name = build.starter_items[0]
                    if hasattr(self, 'item_db') and self.item_db:
                        s_low = starter_name.lower().strip().replace("’", "'")
                        info = self.item_db.get(s_low)
                        if isinstance(info, dict) and info.get("is_starter_t1"):
                            upgrades = info.get("upgrades") or []
                            upgrades_lower = {u.lower().strip().replace("’", "'") for u in upgrades}
                            for item in (build.final_items or []):
                                item_low = item.lower().strip().replace("’", "'")
                                if item_low in upgrades_lower:
                                    for u in upgrades:
                                        if u.lower().strip().replace("’", "'") == item_low:
                                            starter_name = u
                                            break
                                    break
                    
                    starter_icon = self._icon_factory(starter_name, 28)
                    starter_icon.setStyleSheet("border: 1px solid #3b82f6; border-radius: 4px;")
                    items_lay.addWidget(starter_icon)
                    has_starter_or_items = True

                # 2. Przedmioty (max 6 z wykluczeniem ulepszonych starterów)
                filter_item_names = set()
                if hasattr(build, 'starter_items') and build.starter_items:
                    for s in build.starter_items:
                        s_low = s.lower().strip().replace("’", "'")
                        filter_item_names.add(s_low)
                        
                        # Pobieramy dynamiczne ulepszenia z bazy przedmiotów
                        if hasattr(self, 'item_db') and self.item_db:
                            item_info = self.item_db.get(s_low)
                            if isinstance(item_info, dict):
                                upgrades = item_info.get("upgrades") or []
                                for upg in upgrades:
                                    filter_item_names.add(upg.lower().strip().replace("’", "'"))
                
                filtered_final = []
                for item_name in (build.final_items or []):
                    item_low = item_name.lower().strip().replace("’", "'")
                    if item_low in filter_item_names:
                        continue
                    # Wykluczamy jeśli to starter (podstawowy lub ulepszony)
                    if hasattr(self, 'item_db') and self.item_db:
                        item_info = self.item_db.get(item_low)
                        if isinstance(item_info, dict) and item_info.get("category") == "starter":
                            continue
                    filtered_final.append(item_name)
                        
                for item_name in filtered_final[:6]:
                    icon = self._icon_factory(item_name, 28)
                    icon.setToolTip(item_name)
                    items_lay.addWidget(icon)
                has_starter_or_items = True

                # 3. Separator przed Relikiem
                if has_starter_or_items and hasattr(build, 'relics') and build.relics:
                    sep = QFrame()
                    sep.setFixedSize(1, 18)
                    sep.setStyleSheet("background: rgba(148, 163, 184, 0.2); margin: 0 2px;")
                    items_lay.addWidget(sep)

                # 4. Relikt (na samym końcu)
                if hasattr(build, 'relics') and build.relics:
                    relic_icon = self._icon_factory(build.relics[0], 28)
                    relic_icon.setStyleSheet("border: 1px solid #C5A059; border-radius: 4px;")
                    relic_icon.setToolTip(build.relics[0])
                    items_lay.addWidget(relic_icon)
            
            bottom_row.addLayout(items_lay)
            bottom_row.addStretch()
            
            # Meta info (Author + Upvotes)
            meta_lay = QHBoxLayout()
            meta_lay.setSpacing(8)
            meta_lay.setAlignment(Qt.AlignmentFlag.AlignBottom)
            
            if getattr(build, 'is_stats', False):
                uses_obsidian = build.stats_data.get("uses_obsidian", False) if build.stats_data else False
                ranks_str = "Obsidian+" if uses_obsidian else "Master+"
                author_mini = QLabel(ranks_str)
                author_mini.setStyleSheet("font-size: 9px; color: #94a3b8; font-weight: bold;")
                meta_lay.addWidget(author_mini)
                up = QLabel(f"🎮 {build.upvotes}")
                up.setStyleSheet("font-size: 9px; font-weight: 800; color: #60a5fa;")
                up.setToolTip(_t("stats_info_tooltip"))
            else:
                up = QLabel(f"👍 {build.upvotes}")
                up.setStyleSheet("font-size: 9px; font-weight: 800; color: #10b981;")
            meta_lay.addWidget(up)
            
            bottom_row.addLayout(meta_lay)
            layout.addLayout(bottom_row)


        # Click handler
        try:
            idx = self._all_builds.index(build)
            card.clicked.connect(lambda i=idx: self.build_selected.emit(i))
        except ValueError:
            pass

        return card


    def show_skeleton(self):
        """Animated skeleton cards shown during loading."""
        self._is_skeleton = True
        clear_layout(self._list_layout)
        self.pagination.hide()

        # Marginesy dla listy (dodajemy dół w mini by nie ucinało ramki)
        self._list_layout.setContentsMargins(0, 0, 0, 10 if self.is_mini else 0)

        lbl = QLabel(_t("fetching"))
        lbl.setObjectName("card_meta")
        lbl.setStyleSheet("margin-bottom: 5px;")
        self._list_layout.addWidget(lbl)

        count = 6 if self.is_mini else 4
        height = 68 if self.is_mini else 120
        obj_name = "mini_build_row" if self.is_mini else "build_card"

        for _ in range(count):
            card = QFrame()
            card.setObjectName(obj_name)
            card.setFixedHeight(height)
            cl = QVBoxLayout(card)
            
            if self.is_mini:
                cl.setContentsMargins(10, 6, 10, 6)
                cl.setSpacing(4)
                
                # Top: Title + Meta
                top = QHBoxLayout()
                top.addWidget(QSkeleton(140, 14))
                top.addStretch()
                top.addWidget(QSkeleton(40, 14))
                cl.addLayout(top)
                
                # Bottom: Icons
                bot = QHBoxLayout()
                for _ in range(5):
                    bot.addWidget(QSkeleton(28, 28, 6))
                bot.addStretch()
                bot.addWidget(QSkeleton(30, 12))
                cl.addLayout(bot)
            else:
                cl.setContentsMargins(15, 12, 15, 12)
                top = QHBoxLayout()
                tc = QVBoxLayout()
                tc.addWidget(QSkeleton(180, 16))
                tc.addWidget(QSkeleton(100, 10))
                top.addLayout(tc)
                top.addStretch()
                top.addWidget(QSkeleton(60, 20))
                cl.addLayout(top)
                cl.addStretch()
                bottom = QHBoxLayout()
                for _ in range(6):
                    bottom.addWidget(QSkeleton(34, 34, 8))
                cl.addLayout(bottom)
                
            self._list_layout.addWidget(card)
        self._list_layout.addStretch()

    def show_error_screen(self, title, message):
        """Displays a styled error panel with a retry button."""
        self._is_skeleton = False
        clear_layout(self._list_layout)
        self.pagination.hide()
        self._list_layout.setContentsMargins(0, 0, 0, 10 if self.is_mini else 0)

        # 1. GŁÓWNY KONTENER ZEWNĘTRZNY (posiada 2px ramkę i delikatne czerwone tło z QSS)
        container = QFrame()
        container.setObjectName("error_state_card_container")
        container.setFixedWidth(420) # Sztywna szerokość gwarantuje idealne proporcje (nie rozjedzie się w poziomie)
        
        container_lay = QVBoxLayout(container)
        container_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_lay.setContentsMargins(25, 25, 25, 25)
        container_lay.setSpacing(12)

        # 2. WEWNĘTRZNY KAFELEK (zgodnie z QSS jest transparentny i wyśrodkowany)
        card = QFrame()
        card.setObjectName("error_state_card")
        
        lay = QVBoxLayout(card)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # Ikona błędu
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 32px; background: transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        # Nagłówek (Tytuł błędu)
        t = QLabel(title)
        t.setStyleSheet("color: #f87171; font-size: 14px; font-weight: 800; background: transparent;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        # Komunikat szczegółowy
        m = QLabel(message)
        m.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        m.setWordWrap(True)
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(m)

        # Wpychamy kafelek tekstowy do wnętrza głównej ramki
        container_lay.addWidget(card)

        # 3. PRZYCISK "PONÓW" (odpowiada stylowi QPushButton#nav_btn z efektem :hover)
        btn = QPushButton(_t("retry"))
        btn.setObjectName("nav_btn")
        btn.setFixedSize(140, 35)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(lambda: self.retry_requested.emit())
        container_lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        # 4. DODANIE DO GŁÓWNEGO LAYOUTU EKRANU (perfekcyjne wyśrodkowanie w pionie i poziomie)
        self._list_layout.addStretch()
        self._list_layout.addWidget(container, 0, Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addStretch()

        # 5. PŁYNNA ANIMACJA (Przejście fade-in z punktu 2)
        self.animate_fade_in(container)

    def show_empty_state(self):
        """Shows a message when no builds are available."""
        self._is_skeleton = False
        clear_layout(self._list_layout)
        self.pagination.hide()
        self._list_layout.setContentsMargins(0, 0, 0, 10 if self.is_mini else 0)

        # Zamiast generować stary, zwykły tekst, używamy naszej nowej, pięknej graficznej karty!
        self._show_empty()
        
        # Ponieważ metoda _show_empty dodaje układ: Stretch -> Kafelek -> Stretch, 
        # nasz graficzny kafelek jest przedostatnim elementem w układzie.
        # Pobieramy go, aby dodać mu efekt płynnego pojawiania się (fade-in).
        item = self._list_layout.itemAt(self._list_layout.count() - 2)
        if item and item.widget():
            self.animate_fade_in(item.widget())

    def set_role(self, icon_or_path, text):
        self.btn_role.setText(f" {text}")
        
        # Sprawdzamy czy dostaliśmy ścieżkę do pliku (str) czy gotowy obiekt QIcon
        if isinstance(icon_or_path, str):
            from PyQt6.QtGui import QIcon
            self.btn_role.setIcon(QIcon(icon_or_path))
        else:
            self.btn_role.setIcon(icon_or_path)

    def set_aspect(self, icon_or_path, text, style=""):
        self.btn_aspect.setText(f" {text}")
        
        # Sprawdzamy czy dostaliśmy ścieżkę do pliku (str) czy gotowy obiekt QIcon
        if isinstance(icon_or_path, str):
            from PyQt6.QtGui import QIcon
            self.btn_aspect.setIcon(QIcon(icon_or_path))
        else:
            self.btn_aspect.setIcon(icon_or_path)
            
        self.btn_aspect.setStyleSheet(style)

    def reset_page(self):
        self._current_page = 0

    # ------------------------------------------------------------- private
    def _show_empty(self, error_message=None):
        card = QFrame()
        card.setObjectName("empty_state_card")
        
        if self.is_mini:
            # Nieco wyższy kafelek w trybie mini, by ładnie zmieścić ramkę
            card.setFixedHeight(75) 
            el = QHBoxLayout(card)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setContentsMargins(15, 10, 15, 10)
            el.setSpacing(15)
        else:
            card.setFixedHeight(220 if error_message else 200)
            el = QVBoxLayout(card)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setSpacing(15) # Ładny odstęp między ikoną a tekstem
        
        
        icon_box = QFrame()
        icon_lay = QVBoxLayout(icon_box)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Sam obrazek (Wewnątrz boxa, całkowicie przezroczysty)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        
        if error_message:
            icon_label.setText("⚠️")
            if self.is_mini:
                icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
            else:
                icon_label.setStyleSheet("font-size: 40px; background: transparent; border: none;")
            
            icon_lay.addWidget(icon_label)
            
            msg_text = _t("empty_state_error").format(
                title=_t("err_conn_title"),
                subtitle=_t("err_conn_sub"),
                details=_t("err_details"),
                error=error_message 
            )
            card.setStyleSheet("")
        else:
            from PyQt6.QtGui import QPixmap, QPainter, QPainterPath # <-- Dodane importy
            import os
            
            # Wpisz dokładną nazwę pliku
            icon_path = resource_path("assets", "placeholder.png") 
            pixmap = QPixmap(icon_path)
            
            icon_size = 28 if self.is_mini else 56
            
            if not pixmap.isNull():
                # 1. Najpierw skalujemy zdjęcie do odpowiedniego rozmiaru
                pixmap = pixmap.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                # 2. --- MAGICZNA MASKA WYCINAJĄCA ROGI ZDJĘCIA ---
                rounded_pixmap = QPixmap(pixmap.size())
                rounded_pixmap.fill(Qt.GlobalColor.transparent) # Wypełniamy tło całkowitą przezroczystością
                
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing) # Wygładzanie krawędzi (żeby nie były "poszarpane")
                
                path = QPainterPath()
                # Tutaj ustalasz jak bardzo zaokrąglone ma być samo zdjęcie (np. 12px)
                img_rad = 6 if self.is_mini else 12 
                path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), img_rad, img_rad)
                
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                
                # 3. Przypisujemy nasze "wycięte" zdjęcie
                icon_label.setPixmap(rounded_pixmap)
                
                # Ustawiamy proporcje szklanej ramki (tła)
                pad = 12 if self.is_mini else 20
                rad = 12 if self.is_mini else 24
                box_size = icon_size + (pad * 2)
                
                icon_box.setFixedSize(box_size, box_size)
                icon_box.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(30, 41, 59, 0.6);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: {rad}px;
                    }}
                """)
                icon_lay.setContentsMargins(pad, pad, pad, pad)
            else:
                icon_label.setText("🔍")
                if self.is_mini:
                    icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
                else:
                    icon_label.setStyleSheet("font-size: 40px; background: transparent; border: none;")
                    
            icon_lay.addWidget(icon_label)

            msg_text = _t("no_builds_found") 
            card.setStyleSheet("""
                QFrame#empty_state_card {
                    background-color: rgba(15, 23, 42, 0.3);
                    border: 1px dashed rgba(148, 163, 184, 0.25);
                    border-radius: 16px;
                }
            """)

        # Dodajemy pudełko z ikoną do layoutu (wyśrodkowane)
        el.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(msg_text)
        msg.setObjectName("empty_state_text")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if self.is_mini:
            msg.setStyleSheet("font-size: 11px;")
            msg.setWordWrap(False)
            if error_message:
                msg.setText(_t("err_conn_short"))
        else:
            msg.setStyleSheet("color: #94a3b8; font-size: 12px;") 
            msg.setWordWrap(True)
            
        el.addWidget(msg)

        self._list_layout.addStretch()
        self._list_layout.addWidget(card)
        self._list_layout.addStretch()

    def _make_build_card(self, build):
        # ... (insufficient data check remains) ...
        if getattr(build, 'insufficient_data', False):
            # ... (keep existing) ...
            card = QFrame()
            card.setObjectName("build_card")
            card.setStyleSheet("""
                QFrame#build_card {
                    background-color: rgba(239, 68, 68, 0.05);
                    border: 1px dashed rgba(239, 68, 68, 0.25);
                    border-radius: 12px;
                }
                QFrame#build_card:hover {
                    background-color: rgba(239, 68, 68, 0.09);
                    border-color: rgba(239, 68, 68, 0.45);
                }
            """)
            card.setFixedHeight(120)
            
            layout = QVBoxLayout(card)
            layout.setContentsMargins(30, 12, 30, 12)
            layout.setSpacing(4)
            
            display_title = build.title
            if getattr(build, 'is_stats', False):
                display_title = build.title.split(" (Meta Stats -")[0]
            title = QLabel(display_title)
            title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setWordWrap(True)
            
            reason = build.stats_data.get("insufficient_reason") if build.stats_data else None
            if not reason:
                role_val = build.roles[0] if build.roles else _t('role_any')
                reason = _t("err_low_stats_ext").format(role=role_val, count=build.upvotes)
            msg = QLabel(reason)
            msg.setStyleSheet("font-size: 11px; color: #f87171; font-weight: 600;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setWordWrap(True)
            
            sub = QLabel(_t("err_stats_threshold"))
            sub.setStyleSheet("font-size: 9px; color: #94a3b8; font-style: italic;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setWordWrap(True)
            
            layout.addWidget(title)
            layout.addWidget(msg)
            layout.addWidget(sub)
            return card

        card = ClickableFrame()
        card.setObjectName("build_card")
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card.setFixedHeight(120)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(0)

        # --- Top (text) ---
        top = QHBoxLayout()
        top.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(4)
        display_title = build.title
        if getattr(build, 'is_stats', False):
            display_title = build.title.split(" (Meta Stats -")[0]
            
        title = QLabel(display_title)
        title.setObjectName("card_title")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        
        # Elidowanie tekstu jeśli jest za długi (bez elidowania dla wersji stats, limit 260px dla curated)
        if getattr(build, 'is_stats', False):
            title.setText(display_title)
        else:
            fm = title.fontMetrics()
            elided_title = fm.elidedText(display_title, Qt.TextElideMode.ElideRight, 260)
            title.setText(elided_title)
        
        left.addWidget(title)

        author_row = QHBoxLayout()
        author_row.setSpacing(6)
        if getattr(build, 'is_stats', False):
            uses_obsidian = build.stats_data.get("uses_obsidian", False) if build.stats_data else False
            # Pozbywamy się słowa "Matches" na sztywno
            ranks_str = "Obsidian+, Master+ & Demigod" if uses_obsidian else "Master+ & Demigod"
            
            # Wrzucamy rangi w miejsce {count}, dzięki czemu silnik sam doklei słowo "meczów/matches" z pliku translations.py
            translated_text = _t("aggregated").format(count=ranks_str)
            
            a_lbl = QLabel(translated_text)
            a_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
            author_row.addWidget(a_lbl)
        else:
            a_lbl = QLabel(build.author)
            a_lbl.setObjectName("card_author")
            a_lbl.setStyleSheet("font-size: 11px; color: #fbbf24;")
            author_row.addWidget(a_lbl)
            if build.is_partner:
                pb = QLabel(_t("partner_badge"))
                pb.setProperty("class", "partner_badge")
                author_row.addWidget(pb)
        author_row.addStretch()
        left.addLayout(author_row)
        top.addLayout(left)
        top.addStretch()

        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        meta_row = QHBoxLayout()
        meta_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        meta_row.setSpacing(4)
        roles = build.roles if build.roles else ["Any"]
        for i, role in enumerate(roles):
            rl = ClickableLabel(role)
            rl.setProperty("class", "role_link")
            rl.setCursor(Qt.CursorShape.PointingHandCursor)
            if self._set_role_filter_cb:
                rl.clicked.connect(lambda r_val=role: self._set_role_filter_cb(r_val))

            meta_row.addWidget(rl)
            if i < len(roles) - 1:
                sep = QLabel("/")
                sep.setStyleSheet("font-size: 10px; color: #475569;")
                meta_row.addWidget(sep)
        dot = QLabel(" · ")
        dot.setStyleSheet("font-size: 10px; color: #475569;")
        meta_row.addWidget(dot)
        patch_lbl = QLabel(build.patch)
        self.style_patch_badge(patch_lbl, build.patch, self.current_patch, font_size_px=9)
        meta_row.addWidget(patch_lbl)
        right.addLayout(meta_row)

        if build.is_aspect:
            badge = ClickableLabel(f"⚡ {_t('aspect_badge')}")
            badge.setObjectName("card_aspect_badge")
            badge.setFixedHeight(20)
            badge.setFixedWidth(80)
            badge.setCursor(Qt.CursorShape.PointingHandCursor)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self._set_aspect_filter_cb:
                badge.clicked.connect(lambda: self._set_aspect_filter_cb(2))

            right.addWidget(badge, 0, Qt.AlignmentFlag.AlignRight)
        else:
            right.addStretch()

        top.addLayout(right)
        layout.addLayout(top)
        layout.addStretch()

        # --- Bottom (icons + upvotes) ---
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignmentFlag.AlignBottom)
        items_lay = QHBoxLayout()
        items_lay.setSpacing(10)
        
        if self._icon_factory:
            if getattr(build, 'is_stats', False):
                # Stats view logic (Top 1 only, dedup across slots)
                used = set()
                # Starter
                if build.stats_data.get("starter"):
                    best = build.stats_data["starter"][0]
                    used.add(best["item"].lower().strip().replace("'", "'"))
                    items_lay.addWidget(self._icon_factory(best["item"], 34))
                # Slots
                for slot in build.stats_data.get("slots", []):
                    if slot:
                        chosen = slot[0]
                        for c in slot:
                            name = c["item"].lower().strip().replace("'", "'")
                            if name not in used:
                                chosen = c
                                used.add(name)
                                break
                        items_lay.addWidget(self._icon_factory(chosen["item"], 34))
                # Relic
                if build.stats_data.get("relic"):
                    best = build.stats_data["relic"][0]
                    items_lay.addWidget(self._icon_factory(best["item"], 34))
            else:
                # Regular view logic
                has_starter_or_items = False
                # 1. Starter
                if hasattr(build, 'starter_items') and build.starter_items:
                    starter_name = build.starter_items[0]
                    if hasattr(self, 'item_db') and self.item_db:
                        s_low = starter_name.lower().strip().replace("’", "'")
                        info = self.item_db.get(s_low)
                        if isinstance(info, dict) and info.get("is_starter_t1"):
                            upgrades = info.get("upgrades") or []
                            upgrades_lower = {u.lower().strip().replace("’", "'") for u in upgrades}
                            for item in (build.final_items or []):
                                item_low = item.lower().strip().replace("’", "'")
                                if item_low in upgrades_lower:
                                    for u in upgrades:
                                        if u.lower().strip().replace("’", "'") == item_low:
                                            starter_name = u
                                            break
                                    break
                    
                    starter_icon = self._icon_factory(starter_name, 34)
                    starter_icon.setStyleSheet("border: 1px solid #3b82f6; border-radius: 4px;")
                    items_lay.addWidget(starter_icon)
                    has_starter_or_items = True
                    
                # 2. Final Items (z wykluczeniem ulepszonych starterów)
                filter_item_names = set()
                if hasattr(build, 'starter_items') and build.starter_items:
                    for s in build.starter_items:
                        s_low = s.lower().strip().replace("’", "'")
                        filter_item_names.add(s_low)
                        
                        # Pobieramy dynamiczne ulepszenia z bazy przedmiotów
                        if hasattr(self, 'item_db') and self.item_db:
                            item_info = self.item_db.get(s_low)
                            if isinstance(item_info, dict):
                                upgrades = item_info.get("upgrades") or []
                                for upg in upgrades:
                                    filter_item_names.add(upg.lower().strip().replace("’", "'"))
                
                filtered_final = []
                for item_name in (build.final_items or []):
                    item_low = item_name.lower().strip().replace("’", "'")
                    if item_low in filter_item_names:
                        continue
                    # Wykluczamy jeśli to starter (podstawowy lub ulepszony)
                    if hasattr(self, 'item_db') and self.item_db:
                        item_info = self.item_db.get(item_low)
                        if isinstance(item_info, dict) and item_info.get("category") == "starter":
                            continue
                    filtered_final.append(item_name)
                        
                for item_name in filtered_final[:6]:
                    items_lay.addWidget(self._icon_factory(item_name, 34))
                    has_starter_or_items = True
                    
                # 3. Separator przed Relikiem
                if has_starter_or_items and hasattr(build, 'relics') and build.relics:
                    sep = QFrame()
                    sep.setFixedSize(1, 22)
                    sep.setStyleSheet("background: rgba(148, 163, 184, 0.2); margin: 0 4px;")
                    items_lay.addWidget(sep)
                    
                # 4. Relic (na samym końcu)
                if hasattr(build, 'relics') and build.relics:
                    relic_icon = self._icon_factory(build.relics[0], 34)
                    relic_icon.setStyleSheet("border: 1px solid #C5A059; border-radius: 4px;")
                    items_lay.addWidget(relic_icon)
                
        bottom.addLayout(items_lay)
        bottom.addStretch()
        
        if getattr(build, 'is_stats', False):
            up = QLabel(f"🎮 {build.upvotes}")
            up.setObjectName("upvotes_count")
            up.setStyleSheet("font-size: 11px; font-weight: bold; color: #60a5fa;")
            up.setToolTip(_t("stats_info_tooltip"))
        else:
            up = QLabel(f"👍 {build.upvotes}")
            up.setObjectName("upvotes_count")
            up.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981;")
            
        bottom.addWidget(up, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(bottom)

        # Click handler
        try:
            idx = self._all_builds.index(build)
            card.clicked.connect(lambda i=idx: self.build_selected.emit(i))
        except ValueError:
            pass

        return card

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self.populate(self._all_builds)

    def _next_page(self):
        max_p = (len(self._all_builds) - 1) // self._items_per_page
        if self._current_page < max_p:
            self._current_page += 1
            self.populate(self._all_builds)

    def _on_toggle_changed(self, value):
        """Value to 'builds' lub 'stats' z Twojego SegmentedToggle."""
        if self.isVisible():
            print(f"[UI] Przełączono źródło na: {value}")
            self.source_changed.emit(value)

    def animate_fade_in(self, widget, duration=300):
        """Adds a fade-in animation effect to any widget."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        # Przechowujemy animację jako atrybut, żeby Python jej nie usunął zbyt wcześnie
        widget._fade_anim = anim
    