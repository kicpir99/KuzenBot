"""List Screen — paginated build cards with filter bar."""

import os, sys
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor, QFont, QIcon
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QSizePolicy, QGraphicsOpacityEffect)

from ui.components.skeleton import QSkeleton, clear_layout
from ui.components.segmented_toggle import SegmentedToggle
from core.translations import _t, get_role_translation

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

class ListScreen(QWidget):
    """Build list screen with cards, filter bar, and pagination."""

    build_selected = pyqtSignal(int)   # globalny indeks buildu
    role_filter_clicked = pyqtSignal()
    aspect_filter_clicked = pyqtSignal()
    source_changed = pyqtSignal(str)
    retry_requested = pyqtSignal()

    def __init__(self, icon_factory=None, role_click_cb=None, aspect_click_cb=None, parent=None, colorizer=None, tooltip_filter=None):
        super().__init__(parent)
        self._icon_factory = icon_factory
        self._colorizer = colorizer
        self._icon_factory = icon_factory
        self._tooltip_filter = tooltip_filter
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
        elif not self.current_patch:
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
            if not self._aspect_banner_dismissed:
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

    def style_tier_badge(self, label, tier_str, font_size_px=10, is_mini=False):
        """Styluje odznakę oceny buildu (S+, S, A+, A, B, C, D) w spójnej skali kolorystycznej."""
        t = (tier_str or "").strip().upper()
        if t in ("S+", "S"):
            # Szmaragdowy zielony (najlepsza ocena, spójna z aktualnym patchem)
            bg_color = "rgba(16, 185, 129, 0.15)"
            border_color = "rgba(16, 185, 129, 0.45)"
            text_color = "#34d399"
        elif t in ("A+", "A"):
            # Jasnozielony / limonkowy (bardzo dobra ocena)
            bg_color = "rgba(132, 204, 22, 0.15)"
            border_color = "rgba(132, 204, 22, 0.45)"
            text_color = "#a3e635"
        elif t == "B":
            # Żółty / bursztynowy (średnia/solidna ocena)
            bg_color = "rgba(245, 158, 11, 0.15)"
            border_color = "rgba(245, 158, 11, 0.45)"
            text_color = "#fbbf24"
        elif t == "C":
            # Pomarańczowy (poniżej średniej)
            bg_color = "rgba(249, 115, 22, 0.15)"
            border_color = "rgba(249, 115, 22, 0.45)"
            text_color = "#fb923c"
        elif t == "D":
            # Czerwony (najsłabsza ocena)
            bg_color = "rgba(239, 68, 68, 0.15)"
            border_color = "rgba(239, 68, 68, 0.45)"
            text_color = "#f87171"
        else:
            # Ciemny granat z subtelnym błękitem (spójny z motywem aplikacji)
            bg_color = "rgba(30, 41, 59, 0.6)"
            border_color = "rgba(59, 130, 246, 0.35)"
            text_color = "#93c5fd"

        radius = 3 if is_mini else 4
        pad_h = 3 if is_mini else 5
        label.setStyleSheet(f"""
            QLabel {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: {radius}px;
                color: {text_color};
                font-size: {font_size_px}px;
                font-weight: 800;
                padding: 1px {pad_h}px;
            }}
        """)

    def _attach_tooltip(self, widget, tooltip_html):
        if not widget or not tooltip_html:
            return
        widget.setProperty("tooltip_html", tooltip_html)
        widget.setObjectName("build_stats_badge")
        widget.setMouseTracking(True)
        if hasattr(self, '_tooltip_filter') and self._tooltip_filter:
            widget.installEventFilter(self._tooltip_filter)

    def get_build_tooltip_html(self, build) -> str:
        """Zwraca jednolity, elegancki tooltip HTML dla buildów ze statystykami oraz Unranked w kolorystyce ciemnego granatu."""
        has_wr = bool(getattr(build, 'win_rate', None) and build.win_rate)
        cost_val = getattr(build, 'cost', 0)
        cost_str = f"{cost_val:,}g".replace(",", " ") if cost_val else ""

        if has_wr:
            tier_str = getattr(build, 'tier', '') or ''
            tier_html = f" <span style='color: #60a5fa; font-weight: bold;'>[{tier_str}]</span>" if tier_str else ""
            total_matches_str = _t("tt_total").format(count=build.total_matches)
            lines = [
                f"<div style='margin-bottom: 2px;'><b style='color: #93c5fd;'>{_t('tt_win_rate')}</b> <span style='color: #10b981; font-weight: bold;'>{build.win_rate}</span>{tier_html}</div>",
                f"<div style='margin-bottom: 2px;'><b style='color: #93c5fd;'>{_t('tt_matches')}</b> <span style='color: #34d399; font-weight: bold;'>{build.wins}W</span> - <span style='color: #f87171; font-weight: bold;'>{build.losses}L</span> <span style='color: #94a3b8;'>({total_matches_str})</span></div>"
            ]
        else:
            lines = [
                f"<div style='margin-bottom: 2px;'><b style='color: #93c5fd;'>{_t('tt_status')}</b> <span style='color: #60a5fa; font-weight: bold;'>{_t('tt_unranked')}</span></div>",
                f"<div style='margin-bottom: 2px;'><b style='color: #93c5fd;'>{_t('tt_matches')}</b> <span style='color: #e2e8f0;'>{_t('tt_unranked_desc')}</span></div>"
            ]

        if cost_str:
            lines.append(f"<div><b style='color: #93c5fd;'>{_t('tt_build_cost')}</b> <span style='color: #fbbf24; font-weight: bold;'>{cost_str}</span></div>")

        return f"<div style='line-height: 140%; padding: 2px 4px;'>{''.join(lines)}</div>"


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
            
            raw_role = build.roles[0] if build.roles else ""
            role_val = get_role_translation(raw_role) if raw_role else _t('role_any')
            if getattr(build, 'is_stats', False):
                if getattr(build, 'is_aspect', False):
                    display_title = f"{role_val} ({_t('aspect_badge')})"
                else:
                    display_title = role_val
            else:
                display_title = build.title

            title = QLabel(display_title)
            title.setStyleSheet("font-size: 11px; font-weight: bold; color: #f8fafc;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setWordWrap(True)
            
            s_data = build.stats_data or {}
            reason_type = s_data.get("reason_type")
            raw_reason = str(s_data.get("insufficient_reason", "")).lower()
            is_variety = reason_type == "low_variety" or "różnorodn" in raw_reason or "variety" in raw_reason
            
            if is_variety:
                reason = _t("err_low_variety_mini").format(role=role_val)
            else:
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
            role_text = "/".join(get_role_translation(r) for r in build.roles)
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
                has_prev_stage = False
                if build.stats_data.get("starter"):
                    best = build.stats_data["starter"][0]
                    used.add(best["item"].lower().strip().replace("’", "'"))
                    st_icon = self._icon_factory({"to": best["item"], "alts": build.stats_data["starter"][1:]}, 28)
                    st_icon.setStyleSheet("border: 1px solid #3b82f6; border-radius: 4px;")
                    items_lay.addWidget(st_icon)
                    sep_st = QFrame()
                    sep_st.setFixedSize(1, 18)
                    sep_st.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                    items_lay.addWidget(sep_st)
                    has_prev_stage = True
                # Slots
                for slot in build.stats_data.get("slots", []):
                    if slot:
                        chosen = slot[0]
                        for c in slot:
                            name = c["item"].lower().strip().replace("’", "'")
                            if name not in used:
                                chosen = c
                                used.add(name)
                                break
                        alts = [s for s in slot if s["item"] != chosen["item"]]
                        items_lay.addWidget(self._icon_factory({"to": chosen["item"], "alts": alts}, 28))
                        has_prev_stage = True
                # Relic
                if build.stats_data.get("relic"):
                    if has_prev_stage:
                        sep_rel = QFrame()
                        sep_rel.setFixedSize(1, 18)
                        sep_rel.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                        items_lay.addWidget(sep_rel)
                    best = build.stats_data["relic"][0]
                    rel_icon = self._icon_factory({"to": best["item"], "alts": build.stats_data["relic"][1:]}, 28)
                    rel_icon.setStyleSheet("border: 1px solid #C5A059; border-radius: 4px;")
                    items_lay.addWidget(rel_icon)
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
                
                if hasattr(build, 'relics') and build.relics:
                    for r in build.relics:
                        filter_item_names.add(r.lower().strip().replace("’", "'"))
                
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
                        
                if has_starter_or_items and filtered_final:
                    sep_st = QFrame()
                    sep_st.setFixedSize(1, 18)
                    sep_st.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                    items_lay.addWidget(sep_st)

                for item_name in filtered_final[:6]:
                    icon = self._icon_factory(item_name, 28)
                    items_lay.addWidget(icon)
                has_starter_or_items = True

                # 3. Separator przed Relikiem
                if has_starter_or_items and hasattr(build, 'relics') and build.relics:
                    sep = QFrame()
                    sep.setFixedSize(1, 18)
                    sep.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                    items_lay.addWidget(sep)

                # 4. Relikt (na samym końcu)
                if hasattr(build, 'relics') and build.relics:
                    relic_icon = self._icon_factory(build.relics[0], 28)
                    relic_icon.setStyleSheet("border: 1px solid #C5A059; border-radius: 4px;")
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
                self._attach_tooltip(up, _t("stats_info_tooltip"))
                meta_lay.addWidget(up)
            else:
                tt_html = self.get_build_tooltip_html(build)
                if getattr(build, 'win_rate', None) and build.win_rate:
                    if getattr(build, 'tier', None) and build.tier and build.tier != "-":
                        tier_lbl = QLabel(build.tier)
                        self.style_tier_badge(tier_lbl, build.tier, font_size_px=9, is_mini=True)
                        self._attach_tooltip(tier_lbl, tt_html)
                        meta_lay.addWidget(tier_lbl)
                    
                    up = QLabel(f"{build.win_rate} WR")
                    up.setStyleSheet("font-size: 9px; font-weight: 800; color: #10b981;")
                    self._attach_tooltip(up, tt_html)
                    meta_lay.addWidget(up)
                else:
                    unranked_lbl = QLabel(_t("unranked_badge"))
                    self.style_tier_badge(unranked_lbl, "Unranked", font_size_px=9, is_mini=True)
                    self._attach_tooltip(unranked_lbl, tt_html)
                    meta_lay.addWidget(unranked_lbl)
            
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

    def show_empty_state(self, is_new_god=False):
        """Shows a message when no builds are available."""
        self._is_skeleton = False
        from ui.components.skeleton import clear_layout # Upewnij się, że masz ten import, jeśli był tam wcześniej
        clear_layout(self._list_layout)
        self.pagination.hide()
        self._list_layout.setContentsMargins(0, 0, 0, 10 if self.is_mini else 0)

        # Zamiast generować stary, zwykły tekst, używamy naszej nowej, pięknej graficznej karty!
        # PRZEKAZUJEMY FLAGĘ DALEJ ->
        self._show_empty(is_new_god)
        
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

    def retranslate_ui(self):
        """Updates filters and re-renders build cards when language changes."""
        if hasattr(self, 'toggle'):
            self.toggle.label_builds.setText(_t("builds_toggle"))
            self.toggle.label_stats.setText(_t("stats_toggle"))
        if hasattr(self, 'btn_aspect'):
            aspect_text = _t('aspect_only') if getattr(self, '_aspect_filter', 1) == 2 else _t('aspect_off')
            self.btn_aspect.setText(f" {aspect_text}")
        if hasattr(self, '_all_builds') and self._all_builds:
            self._render_current_page()

    def reset_page(self):
        self._current_page = 0

    # ------------------------------------------------------------- private
    def _show_empty(self, is_new_god=False, error_message=None):
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
            from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
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

            # --- ZMIANA: Inteligentny wybór tekstu! ---
            if is_new_god:
                # Używamy HTML, żeby pogrubić tytuł w jednej etykiecie bez rujnowania Twojego układu
                msg_text = f"<b>{_t('empty_new_god_title')}</b><br>{_t('empty_new_god_sub')}"
            else:
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
            
            raw_role = build.roles[0] if build.roles else ""
            role_val = get_role_translation(raw_role) if raw_role else _t('role_any')
            if getattr(build, 'is_stats', False):
                if getattr(build, 'is_aspect', False):
                    display_title = f"{role_val} ({_t('aspect_badge')})"
                else:
                    display_title = role_val
            else:
                display_title = build.title

            title = QLabel(display_title)
            title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setWordWrap(True)
            
            s_data = build.stats_data or {}
            reason_type = s_data.get("reason_type")
            raw_reason = str(s_data.get("insufficient_reason", "")).lower()
            is_variety = reason_type == "low_variety" or "różnorodn" in raw_reason or "variety" in raw_reason
            
            if is_variety:
                reason = _t("err_low_variety_ext").format(role=role_val)
            else:
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
            rl = ClickableLabel(get_role_translation(role))
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
                # Stats view logic (Top 1 + alts in tooltip, dedup across slots)
                used = set()
                has_prev_stage = False
                # Starter
                if build.stats_data.get("starter"):
                    best = build.stats_data["starter"][0]
                    used.add(best["item"].lower().strip().replace("’", "'"))
                    st_icon = self._icon_factory({"to": best["item"], "alts": build.stats_data["starter"][1:]}, 34)
                    st_icon.setStyleSheet("border: 1px solid #3b82f6; border-radius: 4px;")
                    items_lay.addWidget(st_icon)
                    sep_st = QFrame()
                    sep_st.setFixedSize(1, 22)
                    sep_st.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                    items_lay.addWidget(sep_st)
                    has_prev_stage = True
                # Slots
                for slot in build.stats_data.get("slots", []):
                    if slot:
                        chosen = slot[0]
                        for c in slot:
                            name = c["item"].lower().strip().replace("’", "'")
                            if name not in used:
                                chosen = c
                                used.add(name)
                                break
                        alts = [s for s in slot if s["item"] != chosen["item"]]
                        items_lay.addWidget(self._icon_factory({"to": chosen["item"], "alts": alts}, 34))
                        has_prev_stage = True
                # Relic
                if build.stats_data.get("relic"):
                    if has_prev_stage:
                        sep_rel = QFrame()
                        sep_rel.setFixedSize(1, 22)
                        sep_rel.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                        items_lay.addWidget(sep_rel)
                    best = build.stats_data["relic"][0]
                    rel_icon = self._icon_factory({"to": best["item"], "alts": build.stats_data["relic"][1:]}, 34)
                    rel_icon.setStyleSheet("border: 1px solid #C5A059; border-radius: 4px;")
                    items_lay.addWidget(rel_icon)
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
                
                if hasattr(build, 'relics') and build.relics:
                    for r in build.relics:
                        filter_item_names.add(r.lower().strip().replace("’", "'"))
                
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
                        
                if has_starter_or_items and filtered_final:
                    sep_st = QFrame()
                    sep_st.setFixedSize(1, 22)
                    sep_st.setStyleSheet("background: rgba(148, 163, 184, 0.25); margin: 0 2px;")
                    items_lay.addWidget(sep_st)

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
            self._attach_tooltip(up, _t("stats_info_tooltip"))
            bottom.addWidget(up, 0, Qt.AlignmentFlag.AlignBottom)
        else:
            tt_html = self.get_build_tooltip_html(build)
            if getattr(build, 'win_rate', None) and build.win_rate:
                stats_box = QHBoxLayout()
                stats_box.setSpacing(6)
                stats_box.setAlignment(Qt.AlignmentFlag.AlignBottom)
                
                if getattr(build, 'tier', None) and build.tier and build.tier != "-":
                    tier_badge = QLabel(f" {build.tier} ")
                    self.style_tier_badge(tier_badge, build.tier, font_size_px=10, is_mini=False)
                    self._attach_tooltip(tier_badge, tt_html)
                    stats_box.addWidget(tier_badge)
                    
                up = QLabel(f"{build.win_rate} WR")
                up.setObjectName("upvotes_count")
                up.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981;")
                self._attach_tooltip(up, tt_html)
                stats_box.addWidget(up)
                bottom.addLayout(stats_box)
            else:
                unranked_badge = QLabel(f" {_t('unranked_badge')} ")
                unranked_badge.setObjectName("upvotes_count")
                self.style_tier_badge(unranked_badge, "Unranked", font_size_px=10, is_mini=False)
                self._attach_tooltip(unranked_badge, tt_html)
                bottom.addWidget(unranked_badge, 0, Qt.AlignmentFlag.AlignBottom)
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
    