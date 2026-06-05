"""SmiteOverlay — Master Page.

Slim orchestrator (~300 lines) that owns:
  • Header bar (navigation buttons, title, toggle)
  • QStackedWidget page-router (Home / Search / List / Detail)
  • Mini bar (compact view for List/Detail)
  • Floating tooltip
  • Window dragging
"""

import os
import re
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QRect, QSize, QByteArray, QTimer, QUrl, QThread
from PyQt6.QtGui import QPixmap, QCursor, QFont, QIcon, QDesktopServices
from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QFrame, QStackedWidget,
                             QSizePolicy, QApplication)

from ui.styles import get_stylesheet
from ui.components.skeleton import clear_layout
from ui.screens.home_screen import HomeScreen
from ui.screens.search_screen import SearchScreen
from ui.screens.list_screen import ListScreen
from ui.screens.detail_screen import DetailScreen
from ui.screens.auto_wait_screen import AutoWaitScreen
from core.translations import _t

# Page indices in QStackedWidget
PAGE_HOME = 0
PAGE_SEARCH = 1
PAGE_LIST = 2
PAGE_DETAIL = 3
PAGE_AUTO_WAIT = 4

def resource_path(*paths):
    """Resolves resource paths inside _MEIPASS for bundled executables."""
    import sys, os
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

class AsyncIconDownloader(QThread):
    icon_ready = pyqtSignal(str, str, object, int)

    def __init__(self, overlay, name, size, icon_widget):
        super().__init__()
        self.overlay = overlay
        self.name = name
        self.size = size
        self.icon_widget = icon_widget

    def run(self):
        # Pobieranie odbywa się w tle, omijając główne okno!
        path = self.overlay._ensure_item_icon(self.name, self.size)
        self.icon_ready.emit(self.name, path, self.icon_widget, self.size)

class SmiteOverlay(QMainWindow):
    # ---- Signals consumed by SmiteController ----
    next_build_requested = pyqtSignal()
    prev_build_requested = pyqtSignal()
    build_selected = pyqtSignal(int)
    filter_changed = pyqtSignal()
    manual_mode_selected = pyqtSignal()
    auto_mode_selected = pyqtSignal()
    search_requested = pyqtSignal(str)
    settings_requested = pyqtSignal()
    update_accepted = pyqtSignal()
    returned_to_auto_wait = pyqtSignal()

    # ---- Constants ----
    EXPANDED_SIZE = (600, 840)
    MINI_SIZE = (400, 160)

    def __init__(self):
        super().__init__()
        self.is_expanded = True
        self._drag_pos = None
        self.current_build = None
        self.current_idx = 0
        self.total_count = 0
        self._current_page = ""
        self._role_filter = "Any"
        self._aspect_filter = 1
        self._roles_list = ["Any", "Carry", "Jungle", "Mid", "Support", "Solo"]
        self._all_builds = []
        self._current_god_name = ""
        self._history_stack = []
        self._forward_stack = []
        self._reconfiguring = False

        # Wczytujemy bazę przedmiotów do wykrywania usuniętych przedmiotów
        self.item_db = {}
        import json
        items_path = resource_path("assets", "items.json")
        if os.path.exists(items_path):
            try:
                with open(items_path, "r", encoding="utf-8") as f:
                    self.item_db = json.load(f)
            except:
                pass


        self._setup_window()
        self._build_ui()
        self.setStyleSheet(get_stylesheet())
        self._apply_fixed_size()
        self.navigate_to("home", force=True)
        self.setWindowOpacity(0.0)

    # ================================================================ WINDOW
    def _setup_window(self):
        self.setWindowTitle("KuzenBot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # --- DODAJ TUTAJ ---
        # Okno rodzi się całkowicie niewidzialne, co zapobiega mruganiu
        self.setWindowOpacity(0.0)

    # --- WKLEJ TE DWIE METODY TUTAJ ---
    def animate_window_fade_in(self):
        """Smoothly fades in the main application window."""
        config = getattr(self, '_config', {})
        
        
        target_opacity = config.get("opacity_app", 1.0)

        # Animujemy wbudowaną właściwość okna Qt: 'windowOpacity'
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(target_opacity)
        
        # OutCubic sprawia, że animacja startuje dynamicznie i zwalnia pod koniec
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self._fade_anim.start()

    def showEvent(self, event):
        """Overrides show event to trigger the window animation."""
        super().showEvent(event)
        if not self.isMinimized():
            # Opóźniamy animację o 10ms. Daje to menedżerowi okien Windows 
            # czas na wyrenderowanie niewidzialnej klatki, eliminując mruganie.
            QTimer.singleShot(10, self.animate_window_fade_in)
    # ----------------------------------

    def resizeEvent(self, event):
        """Updates floating element positions on window resize."""
        super().resizeEvent(event)
        
        if hasattr(self, 'status_diode'):
            # Ustawiamy pozycję: od prawej i od dołu odejmujemy po 22 piksele, 
            # by dioda nie stykała się z samą krawędzią ramki.
            self.status_diode.move(10, self.height() - 22)

    def toggle_click_through(self):
        import ctypes
        
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FLAGS = SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER

        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        is_locked = getattr(self, '_is_locked', False)
        
        if is_locked:
            style &= ~WS_EX_TRANSPARENT
            self._is_locked = False
            print("🔓 Overlay unlocked (clickable)")
            self.btn_lock.setIcon(self._colorize_icon(resource_path("assets", "unlock_mask.svg"), "#94a3b8"))
        else:
            style |= WS_EX_TRANSPARENT
            self._is_locked = True
            print("🔒 Overlay locked (click-through)")
            self.btn_lock.setIcon(self._colorize_icon(resource_path("assets", "lock_mask.svg"), "#f59e0b"))

        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)

    # ================================================================ UI
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("main_container")
        rl.addWidget(self.container)

        self.main_vbox = QVBoxLayout(self.container)
        self.main_vbox.setContentsMargins(15, 12, 15, 15)
        self.main_vbox.setSpacing(10)

        self._build_header()
        self._build_pages()
        self._build_mini_bar()
        self._build_tooltip()

        # --- NOWOŚĆ: Pływająca dioda w prawym dolnym rogu ---
        self.status_diode = QLabel(self) # Rodzic 'self' odkleja element od gridów/layoutów
        self.status_diode.setFixedSize(10, 10)
        self.status_diode.setStyleSheet("background-color: #10b981; border-radius: 5px;")
        self.status_diode.setToolTip("Gotowy")
        self.status_diode.show()

    # ---------------------------------------- HEADER
    def _build_header(self):
        self.header = QWidget()
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)

        self.btn_home = QPushButton()
        self.btn_home.setObjectName("nav_btn")
        self.btn_home.setFixedSize(30, 26)
        self.btn_home.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_home.setIcon(self._colorize_icon(resource_path("assets", "home_mask.svg"), "#94a3b8"))
        self.btn_home.setIconSize(QSize(16, 16))
        self.btn_home.clicked.connect(lambda: self.navigate_to("home"))
        self.btn_home.installEventFilter(self)

        self.btn_back = QPushButton()
        self.btn_back.setObjectName("nav_btn")
        self.btn_back.setFixedSize(30, 26)
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.setIcon(self._colorize_icon(resource_path("assets", "back_mask.svg"), "#94a3b8"))
        self.btn_back.setIconSize(QSize(16, 16))
        self.btn_back.clicked.connect(self.go_back)
        self.btn_back.installEventFilter(self)
        self.btn_back.hide()

        self.god_label = QLabel()
        self.god_label.setObjectName("god_name")
        self.god_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.god_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.god_label.setMouseTracking(True)
        self.god_label.installEventFilter(self)
        
        # Ładujemy domyślne logo graficzne przy starcie aplikacji
        logo_path = resource_path("assets", "header_logo.png")
        if os.path.exists(logo_logo := logo_path):
            self.god_label.setPixmap(QPixmap(logo_logo).scaledToHeight(50, Qt.TransformationMode.SmoothTransformation))

        # Mini filters
        self.mini_header_filters = QWidget()
        mhfl = QHBoxLayout(self.mini_header_filters)
        mhfl.setContentsMargins(0, 0, 5, 0)
        mhfl.setSpacing(4)
        self.btn_mini_role = QPushButton()
        self.btn_mini_role.setFixedSize(28, 28)
        self.btn_mini_role.setObjectName("mini_filter_btn")
        self.btn_mini_role.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Używamy Twojego nowego wektora i z powrotem kolorujemy go na szaro
        self.btn_mini_role.setIcon(self._colorize_icon(resource_path("assets", "role_any_mask.svg"), "#94a3b8"))
        self.btn_mini_role.setIconSize(QSize(16, 16))
        self.btn_mini_role.clicked.connect(self._cycle_role_filter)
        self.btn_mini_role.installEventFilter(self)

        self.btn_mini_aspect = QPushButton("") # Pusty tekst, żeby emotka nie wisiała
        self.btn_mini_aspect.setFixedSize(28, 28)
        self.btn_mini_aspect.setObjectName("mini_filter_btn")
        self.btn_mini_aspect.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_mini_aspect.setIcon(QIcon(resource_path("assets", "aspect_off.png")))
        self.btn_mini_aspect.setIconSize(QSize(16, 16))
        self.btn_mini_aspect.clicked.connect(self._cycle_aspect_filter)
        self.btn_mini_aspect.installEventFilter(self)

        # === DODAJ TE DWIE LINIJKI TUTAJ ===
        mhfl.addWidget(self.btn_mini_role)
        mhfl.addWidget(self.btn_mini_aspect)
        
        self.patch_badge = QLabel("")
        self.patch_badge.setObjectName("patch_badge")
        self.patch_badge.hide()

        self.btn_lock = QPushButton()
        self.btn_lock.setObjectName("toggle_btn")
        self.btn_lock.setFixedSize(28, 28)
        self.btn_lock.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.btn_lock.setIcon(self._colorize_icon(resource_path("assets", "unlock_mask.svg"), "#94a3b8"))
        self.btn_lock.setIconSize(QSize(16, 16))
        self.btn_lock.installEventFilter(self)

        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("toggle_btn")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Ponieważ aplikacja startuje jako rozszerzona, domyślną akcją jest "zwiń" (collapse)
        self.btn_toggle.setIcon(self._colorize_icon(resource_path("assets", "collapse_mask.svg"), "#94a3b8"))
        self.btn_toggle.setIconSize(QSize(16, 16))
        self.btn_toggle.clicked.connect(self.toggle_mode)
        self.btn_toggle.installEventFilter(self)

        self.btn_source_toggle = QPushButton()
        self.btn_source_toggle.setObjectName("toggle_btn")
        self.btn_source_toggle.setFixedSize(28, 28)
        self.btn_source_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Zmieniamy na kolorowane SVG:
        self.btn_source_toggle.setIcon(self._colorize_icon(resource_path("assets", "community_mask.svg"), "#94a3b8"))
        self.btn_source_toggle.setIconSize(QSize(16, 16))
        self.btn_source_toggle.clicked.connect(self._toggle_build_source)
        self.btn_source_toggle.installEventFilter(self)

        self.btn_close = QPushButton()
        # ... (cały blok stylesheet) ...
        self.btn_close.setText("✕")
        # ...

# --- MA BYĆ (usuwamy linijkę z .setText("✕") i dodajemy zestaw ikon): ---
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("close_btn")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton#close_btn {
                background: rgba(239,68,68,0.12);
                border: 1px solid rgba(239,68,68,0.2);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                color: #f87171;
            }
            QPushButton#close_btn:hover {
                background: rgba(239,68,68,0.25);
                border-color: rgba(239,68,68,0.4);
                color: #ef4444;
            }
        """)
        self.btn_close.setIcon(self._colorize_icon(resource_path("assets", "close_mask.svg"), "#ef4444"))
        self.btn_close.setIconSize(QSize(14, 14)) # Krzyżyk wygląda najlepiej, gdy jest odrobinę mniejszy
        self.btn_close.clicked.connect(self._on_close_clicked)
        self.btn_close.installEventFilter(self)

        # Settings gear — visible only on home page
        
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("toggle_btn")
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.setIcon(self._colorize_icon(resource_path("assets", "settings_mask.svg"), "#94a3b8"))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setToolTip(_t("tt_settings"))
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        self.btn_settings.installEventFilter(self)
        self.btn_settings.hide()
        self.btn_update = QPushButton("🚀")
        self.btn_update.setObjectName("btn_update")
        self.btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update.setStyleSheet("""
            QPushButton#btn_update {
                background-color: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.6);
                border-radius: 6px;
                color: #34d399;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btn_update:hover {
                background-color: rgba(16, 185, 129, 0.4);
            }
        """)
        self.btn_update.hide()

        # Assemble header using a 3-section approach for perfect centering
        # SECTION 1: Left Buttons
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(5)
        
        self.left_layout.addWidget(self.btn_update) # <--- DODANY TUTAJ (Zawsze pierwszy po lewej)
        self.left_layout.addWidget(self.btn_settings)
        self.left_layout.addWidget(self.btn_home)
        self.left_layout.addWidget(self.btn_source_toggle)
        self.left_layout.addWidget(self.btn_back)
        self.left_layout.addWidget(self.mini_header_filters)
        self.left_layout.addStretch() # Push buttons to the left

        # SECTION 3: Right Buttons
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(5)
        self.right_layout.addStretch() # Push buttons to the right
        
        self.right_layout.addWidget(self.patch_badge)
        self.right_layout.addWidget(self.btn_lock)
        self.right_layout.addWidget(self.btn_toggle)
        self.right_layout.addWidget(self.btn_close)

        # Assemble main header layout
        hl.addWidget(self.left_container, 1)    # Stretch 1
        hl.addWidget(self.god_label, 0)         # Content width
        hl.addWidget(self.right_container, 1)   # Stretch 1 (must be equal to left)

        self.main_vbox.addWidget(self.header)

    def show_update_button(self, version, url):
        self._update_version = version
        self._update_url = url
        self._has_update = True

        try: self.btn_update.clicked.disconnect()
        except TypeError: pass

        # Zamiast QDesktopServices.openUrl, wysyłamy sygnał do kontrolera!
        self.btn_update.clicked.connect(self.update_accepted.emit)

        self.update_mini_buttons_visibility()

    # ---------------------------------------- PAGES (QStackedWidget)
    def _build_pages(self):
        self.home_screen = HomeScreen()
        self.search_screen = SearchScreen()
        self.list_screen = ListScreen(
            icon_factory=self._make_icon,
            role_click_cb=self._set_role_filter,
            aspect_click_cb=self._set_aspect_filter,
            colorizer=self._colorize_icon # <--- Przekazujemy funkcję
        )
        self.detail_screen = DetailScreen(icon_factory=self._make_icon)
        self.auto_wait_screen = AutoWaitScreen(
            switch_manual_cb=lambda: self.navigate_to("search")
        )

        # Connect screen signals → overlay signals
        self.home_screen.auto_mode_selected.connect(self.auto_mode_selected.emit)
        self.home_screen.manual_mode_selected.connect(
            lambda: self.navigate_to("search")
        )
        self.search_screen.search_requested.connect(self.search_requested.emit)
        self.list_screen.build_selected.connect(self._on_card_clicked)
        self.list_screen.role_filter_clicked.connect(self._cycle_role_filter)
        self.list_screen.aspect_filter_clicked.connect(self._cycle_aspect_filter)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.home_screen)    # 0
        self.pages.addWidget(self.search_screen)  # 1
        self.pages.addWidget(self.list_screen)    # 2
        self.pages.addWidget(self.detail_screen)  # 3
        self.pages.addWidget(self.auto_wait_screen) # 4
        self.main_vbox.addWidget(self.pages, 1)

    # ---------------------------------------- MINI BAR
    def _build_mini_bar(self):
        self.mini_widget = QWidget()
        self.mini_layout = QVBoxLayout(self.mini_widget)
        self.mini_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_layout.setSpacing(4)
        self.mini_widget.hide()
        self.main_vbox.addWidget(self.mini_widget)

    # ---------------------------------------- TOOLTIP
    def _build_tooltip(self):
        self.tooltip = QWidget(self)
        self.tooltip.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.tooltip.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.tooltip_frame = QFrame(self.tooltip)
        self.tooltip_frame.setObjectName("float_tooltip_frame")
        
        tl = QVBoxLayout(self.tooltip)
        tl.setContentsMargins(0, 0, 0, 0)
        # --- NOWOŚĆ: Zmuszamy główne okno tooltipa do ciągłego kurczenia się ---
        tl.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        tl.addWidget(self.tooltip_frame)
        
        self.tooltip_label = QLabel("", self.tooltip_frame)
        self.tooltip_label.setObjectName("float_tooltip_text")
        self.tooltip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tooltip_label.setWordWrap(True)
        
        self.tooltip_label.setMaximumWidth(220) 
        
        tfl = QVBoxLayout(self.tooltip_frame)
        tfl.setContentsMargins(15, 6, 15, 6)
        # --- NOWOŚĆ: Zmuszamy ramkę z tłem do ciągłego kurczenia się ---
        tfl.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        tfl.addWidget(self.tooltip_label)
        
        self.tooltip.hide()

    # ============================================================ NAVIGATION
    def navigate_to(self, page: str, save_history=True, force=False):
        """Navigates between application screens."""
        if not page:
            return
        if page == self._current_page and not force:
            return

        # Zarządzanie historią (tylko jeśli to nowa nawigacja, a nie back/forward)
        if save_history and self._current_page:
            self._history_stack.append(self._current_page)
            self._forward_stack.clear()

        self._current_page = page
        
        page_map = {
            "home": PAGE_HOME,
            "search": PAGE_SEARCH,
            "list": PAGE_LIST,
            "detail": PAGE_DETAIL,
            "auto_wait": PAGE_AUTO_WAIT
        }
        if page not in page_map:
            return
        idx = page_map[page]
        self.pages.setCurrentIndex(idx)

        # Header adaptation
        self.btn_settings.setVisible(page == "home")
        self.btn_home.setVisible(page != "home")
        self.btn_back.setVisible(page == "detail")
        self.patch_badge.setVisible(self.is_expanded and page == "detail" and bool(self.current_build))
        self.mini_header_filters.hide()
        self.btn_source_toggle.hide()

        if self.is_expanded:
            # Expanded mode logic
            if page == "list":
                self.list_screen.set_mini_mode(False)
            elif page == "search":
                self.search_screen.set_mini_mode(False)
                self.search_screen.activate()
                self.manual_mode_selected.emit()
            self.pages.show()
            self.mini_widget.hide()
        else:
            # Mini mode logic
            if page == "detail":
                self.pages.hide()
                self.mini_widget.show()
            elif page == "list":
                self.list_screen.set_mini_mode(True)
                self.pages.show()
                self.mini_widget.hide()
                self.mini_header_filters.show()
                self.btn_source_toggle.show()
            elif page == "search":
                self.search_screen.set_mini_mode(True)
                self.search_screen.activate()
                self.manual_mode_selected.emit()
                self.pages.show()
                self.mini_widget.hide()
            else:
                self.pages.show()
                self.mini_widget.hide()

        # ZMIANA: Wywołujemy nasz filtr widoczności przy każdej nawigacji stron
        self.update_mini_buttons_visibility()
        self._refresh_title()

    def go_back(self):
        """Cofa do poprzedniego ekranu."""
        print(f"[Overlay] Kliknięto 'Back'. Historia: {len(self._history_stack)}")
        if self._history_stack:
            prev_page = self._history_stack.pop()
            if prev_page:
                self._forward_stack.append(self._current_page)
                self.navigate_to(prev_page, save_history=False)
                
                # --- NOWOŚĆ: Dzwonimy do kontrolera! ---
                if prev_page == "auto_wait":
                    self.returned_to_auto_wait.emit()

    def go_forward(self):
        """Navigates forward in screen history."""
        if self._forward_stack:
            next_page = self._forward_stack.pop()
            if next_page:
                self._history_stack.append(self._current_page)
                self.navigate_to(next_page, save_history=False)
                
                # --- NOWOŚĆ: Dzwonimy do kontrolera! ---
                if next_page == "auto_wait":
                    self.returned_to_auto_wait.emit()

    # Alias for backward compat
    def show_home_page(self):
        self.navigate_to("home")

    def set_god_list(self, god_list, new_gods=None):
        """Passes the god list to the search screen."""
        self.search_screen.set_gods(god_list, new_gods)

    # ============================================================ BUILD LIST
    def show_error_screen(self, title, message):
        """Shows the error screen in ListScreen."""
        if title:
            self._current_god_name = title.upper()
        self.list_screen.show_error_screen(title, message)
        self._refresh_title()
        self.navigate_to("list")

    def show_empty_screen(self, message):
        """Pokazuje ekran braku danych w ListScreen."""
        self.list_screen.show_empty_state()
        self.navigate_to("list")

    def show_builds_list(self, builds, god_name="", current_patch=None, error_message=None):
        self._all_builds = builds
        if god_name:
            self._current_god_name = god_name.upper()
            self.list_screen.reset_page()

        self.list_screen.populate(builds, god_name, current_patch, error_message=error_message)
        self._refresh_title()

        # Empty → update mini
        if not builds:
            self._populate_mini_empty(error_message=error_message)

        # Zawsze nawigujemy, navigate_to ukryje co trzeba
        self.navigate_to("list")

    def show_list_skeleton(self, god_name=""):
        if god_name:
            self._current_god_name = god_name.upper()
        self.list_screen.show_skeleton()
        self.navigate_to("list")
        if self.is_expanded:
            self.list_screen.filter_bar.show()

    # ============================================================ BUILD DETAIL
    def update_build(self, build_obj, current_index, total_count):
        self.current_build = build_obj
        self.current_idx = current_index
        self.total_count = total_count

        self._refresh_title()
        # ZMIANA: Przekazujemy zapamiętaną nazwę boga do DetailScreen
        self.detail_screen.populate(build_obj, self._current_god_name) 
        self._populate_mini()

        # Zawsze nawigujemy, funkcja navigate_to obsłuży tryb Mini vs Expanded
        self.navigate_to("detail")

    def show_details_skeleton(self):
        self.current_build = None
        self.detail_screen.show_skeleton()
        self.navigate_to("detail")

    # ============================================================ TOGGLE MODE
    def toggle_mode(self):
        from PyQt6.QtCore import QParallelAnimationGroup, QPropertyAnimation, QEasingCurve, QSize, QPoint
        from PyQt6.QtGui import QGuiApplication
        
        # 1. Pobieramy obecny rozmiar i POZYCJĘ okna (To MUSI być na samej górze!)
        start_size = self.size()
        start_pos = self.pos()
        
        self.is_expanded = not self.is_expanded
        target_w, target_h = self.EXPANDED_SIZE if self.is_expanded else self.MINI_SIZE
        end_size = QSize(target_w, target_h)

        # --- KULOODPORNE ZACHOWANIE KOTWICY (Smart Anchor Preservation) ---
        # Pobieramy ekran, na którym aktualnie znajduje się środek aplikacji
        screen = QGuiApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QGuiApplication.primaryScreen()
            
        # ZMIANA: Używamy pełnej fizycznej matrycy monitora (ignoruje pasek zadań)
        avail_rect = screen.geometry()

        # Obliczamy fizyczne odległości obecnych krawędzi okna od krawędzi monitora
        dist_left = start_pos.x() - avail_rect.left()
        dist_right = avail_rect.right() - (start_pos.x() + start_size.width())
        dist_top = start_pos.y() - avail_rect.top()
        dist_bottom = avail_rect.bottom() - (start_pos.y() + start_size.height())

        # Dynamiczny wybór kotwicy poziomej (lewa vs prawa)
        if dist_right < dist_left:
            # Okno jest bliżej prawej strony: zachowaj prawą krawędź w miejscu
            current_right = start_pos.x() + start_size.width()
            target_x = current_right - target_w
        else:
            # Okno jest bliżej lewej strony: zachowaj lewą krawędź w miejscu
            target_x = start_pos.x()

        # Dynamiczny wybór kotwicy pionowej (góra vs dół)
        if dist_bottom < dist_top:
            # Okno jest bliżej dołu: zachowaj dolną krawędź w miejscu
            current_bottom = start_pos.y() + start_size.height()
            target_y = current_bottom - target_h
        else:
            # Okno jest bliżej góry: zachowaj górną krawędź w miejscu
            target_y = start_pos.y()

        # Dodatkowe, sztywne zabezpieczenie przed obcięciem okna za ekranem (Clamp)
        if target_x + target_w > avail_rect.right(): target_x = avail_rect.right() - target_w
        if target_x < avail_rect.left(): target_x = avail_rect.left()
        if target_y + target_h > avail_rect.bottom(): target_y = avail_rect.bottom() - target_h
        if target_y < avail_rect.top(): target_y = avail_rect.top()

        end_pos = QPoint(int(target_x), int(target_y))
        # ------------------------------------------------------------------

        # 2. TWARDA BLOKADA: Ustawiamy na sztywno obecny rozmiar ZANIM cokolwiek się zmieni.
        # To neutralizuje 'adjustSize' wywoływane w tle przez inne ekrany.
        self.setFixedSize(start_size)

        # 3. Zmiany w UI i układzie
        self.home_screen.set_expanded(self.is_expanded)
        self.auto_wait_screen.set_expanded(self.is_expanded)
        if hasattr(self, 'search_screen'):
            self.search_screen.set_mini_mode(not self.is_expanded)

        icon_name = "collapse_mask.svg" if self.is_expanded else "expand_mask.svg"
        self.btn_toggle.setIcon(self._colorize_icon(resource_path("assets", icon_name), "#94a3b8"))
        
        if self.is_expanded:
            self.main_vbox.setContentsMargins(15, 12, 15, 15)
        else:
            self.main_vbox.setContentsMargins(15, 8, 5, 10)

        # Przełączamy ekran - layout spróbuje skoczyć, ale zablokowaliśmy go w kroku 2!
        self.navigate_to(self._current_page, save_history=False, force=True)

        # --- ANIMACJA GRUPOWA (Płynne skalowanie i przesuwanie jednocześnie) ---
        self._anim_group = QParallelAnimationGroup(self)

        # Animujemy minimalny rozmiar
        self._min_anim = QPropertyAnimation(self, b"minimumSize")
        self._min_anim.setDuration(450)
        self._min_anim.setStartValue(start_size)
        self._min_anim.setEndValue(end_size)
        self._min_anim.setEasingCurve(QEasingCurve.Type.InOutQuint)

        # Animujemy maksymalny rozmiar
        self._max_anim = QPropertyAnimation(self, b"maximumSize")
        self._max_anim.setDuration(450)
        self._max_anim.setStartValue(start_size)
        self._max_anim.setEndValue(end_size)
        self._max_anim.setEasingCurve(QEasingCurve.Type.InOutQuint)
        
        # Animujemy pozycję (X, Y) okna na pulpicie
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(450)
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(end_pos)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.InOutQuint)
        
        # Animacja przygaszenia (Fade)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(450)
        target_op = getattr(self, '_config', {}).get("opacity_app", 1.0)
        self._fade_anim.setKeyValueAt(0.0, target_op)
        self._fade_anim.setKeyValueAt(0.5, target_op * 0.3) 
        self._fade_anim.setKeyValueAt(1.0, target_op)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Łączymy wszystkie cztery animacje w jeden perfekcyjny mechanizm
        self._anim_group.addAnimation(self._min_anim)
        self._anim_group.addAnimation(self._max_anim)
        self._anim_group.addAnimation(self._pos_anim)
        self._anim_group.addAnimation(self._fade_anim)
        
        self._anim_group.finished.connect(lambda: self._on_toggle_anim_done(target_w, target_h))
        self._anim_group.start()
        
    def _on_toggle_anim_done(self, w, h):
        self.setFixedSize(w, h)
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)

    def _apply_fixed_size(self):
        w, h = self.EXPANDED_SIZE if self.is_expanded else self.MINI_SIZE
        self.setFixedSize(w, h)
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)

        if self.is_expanded:
            self.main_vbox.setContentsMargins(15, 12, 15, 15)
        else:
            self.main_vbox.setContentsMargins(15, 8, 5, 10)

    # ============================================================ SETTINGS
    def _on_settings_clicked(self):
        """Emit settings_requested when gear icon is clicked."""
        self.settings_requested.emit()

    # ============================================================ CLOSE / SYSTEM TRAY
    _user_initiated_close = False

    def _on_close_clicked(self):
        """Called when user clicks the X button in header."""
        self._user_initiated_close = True
        config = getattr(self, '_config', {})
        if config.get("close_to_tray", False) or config.get("minimize_to_tray", False):
            self.hide()
            self._user_initiated_close = False
        else:
            self.close()

    def closeEvent(self, event):
        """Intercept window close (Alt+F4, etc.) to apply minimize-to-tray."""
        if not self._user_initiated_close:
            # Programmatic close during reconfiguration or other internal process — suppress
            event.ignore()
            return
        self._user_initiated_close = False
        config = getattr(self, '_config', {})
        if config.get("close_to_tray", False) or config.get("minimize_to_tray", False):
            event.ignore()
            self.hide()
        else:
            QApplication.instance().quit()

    def set_opacity(self, value):
        """Set window opacity 0.0–1.0."""
        self.setWindowOpacity(value)

    def set_always_on_top(self, enabled):
        """Toggle always-on-top flag."""
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if not self.isVisible():
            self.show()

    # ============================================================ FILTERS
    def _cycle_role_filter(self):
        idx = self._roles_list.index(self._role_filter)
        self._set_role_filter(self._roles_list[(idx + 1) % len(self._roles_list)])

    def _cycle_aspect_filter(self):
        # Przełączamy między 1 (Zwykłe) a 2 (Aspekt)
        self._set_aspect_filter(2 if self._aspect_filter == 1 else 1)

    def _set_role_filter(self, role):
        if role not in self._roles_list:
            return
        self._role_filter = role
        
        # Wracamy do słownika z Twoimi plikami SVG
        icons = {
            "Any": "role_any_mask.svg", 
            "Carry": "role_carry_mask.svg", 
            "Jungle": "role_jungle_mask.svg",
            "Mid": "role_mid_mask.svg", 
            "Support": "role_support_mask.svg", 
            "Solo": "role_solo_mask.svg"
        }
        icon_file = icons.get(role, "role_any_mask.svg")
        icon_path = resource_path("assets", icon_file)
        
        # Kolorujemy pobraną maskę na szaro
        colored_icon = self._colorize_icon(icon_path, "#94a3b8")
        
        display_role = _t("role_any") if role == "Any" else role
        
        # Przekazujemy pokolorowaną ikonę do listy i guzika
        self.list_screen.set_role(colored_icon, display_role)
        self.btn_mini_role.setIcon(colored_icon)
        
        self.btn_mini_role.setToolTip(_t("tt_role").format(role=display_role))
        self.list_screen.reset_page()
        self.filter_changed.emit()

    def _set_aspect_filter(self, mode):
        self._aspect_filter = mode
        
        # Klucze tłumaczeniowe
        text = _t('aspect_only') if mode == 2 else _t('aspect_off')
        
        if mode == 2:
            # 1. Sprawdzamy aktualnie wybrany motyw w ustawieniach
            current_theme = getattr(self, '_config', {}).get("theme", "gold")
            
            # 2. Definiujemy kolory dla motywów (zgodne z Twoim plikiem segmented_toggle.py)
            theme_colors = {
                "gold": "#eab308", "ruby": "#e11d48", "blizzard": "#3b82f6",
                "emerald": "#22c55e", "void": "#a855f7", "cyber": "#14b8a6",
                "toxic": "#84cc16", "abyss": "#dc2626"
            }
            theme_hex = theme_colors.get(current_theme, "#eab308") # Domyślnie złoty
            
            # 3. Kolorujemy naszą maskę w locie!
            mask_path = resource_path("assets", "aspect_mask.png")
            colored_icon = self._colorize_icon(mask_path, theme_hex)
            
            self.btn_mini_aspect.setIcon(colored_icon)
            self.btn_mini_aspect.setStyleSheet("")
            
            # Przekazujemy gotowy pokolorowany obiekt na listę
            self.list_screen.set_aspect(colored_icon, text, "")
            self.btn_mini_aspect.setToolTip(_t("tt_aspect_on"))
        else:
            # TRYB 1: Zwykłe buildy (Wyszarzony piorun)
            icon_path = resource_path("assets", "aspect_off.png")
            self.btn_mini_aspect.setIcon(QIcon(icon_path))
            
            self.btn_mini_aspect.setStyleSheet("")
            self.list_screen.set_aspect(icon_path, text, "")
            self.btn_mini_aspect.setToolTip(_t("tt_aspect_off"))
            
        self.list_screen.reset_page()
        self.filter_changed.emit()

    def reset_filters(self):
        self._role_filter = "Any"
        self._aspect_filter = 1  # Reset do trybu "Bez aspektu"
        
        # Reset roli
        any_icon = self._colorize_icon(resource_path("assets", "role_any_mask.svg"), "#94a3b8")
        self.list_screen.set_role(any_icon, _t('role_any'))
        self.btn_mini_role.setIcon(any_icon)
        
        # Reset przycisków aspektu (Wymuszamy szary piorun)
        icon_path = resource_path("assets", "aspect_off.png")
        self.list_screen.set_aspect(icon_path, _t('aspect_off'), "")
        self.btn_mini_aspect.setIcon(QIcon(icon_path))
        self.btn_mini_aspect.setStyleSheet("")

    # ============================================================ MINI BAR
    def _populate_mini(self):
        clear_layout(self.mini_layout)
        if not self.current_build:
            return
        
        if getattr(self.current_build, 'is_stats', False):
            # --- NOWOŚĆ: Baner Ratatoskra dla wersji Mini ---
            if self._current_god_name.lower() == "ratatoskr":
                banner = QFrame()
                banner.setStyleSheet("background: transparent; border: none; margin: 0px; padding: 0px;")
                banner_lay = QHBoxLayout(banner)
                banner_lay.setContentsMargins(0, 0, 0, 2)
                
                badge = QLabel(_t("ratatoskr_acorn_mini"))
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
                badge.setProperty("info_text", _t("ratatoskr_acorn_ext"))
                # Podpinamy EventFilter do SmiteOverlay, dzięki czemu od razu zadziała globalny tooltip!
                badge.installEventFilter(self) 
                badge.setCursor(Qt.CursorShape.WhatsThisCursor)
                
                banner_lay.addStretch()
                banner_lay.addWidget(badge)
                banner_lay.addStretch()
                
                self.mini_layout.addWidget(banner)
            # ------------------------------------------------
            # Stats build in Mini view
            s_data = self.current_build.stats_data or {}
            
            # Starter
            starters = s_data.get("starter", [])
            # Slots
            slots = s_data.get("slots", [[] for _ in range(6)])
            # Relic
            relics = s_data.get("relic", [])
            
            all_slots_data = [("Starter", starters)]
            for i, slot in enumerate(slots):
                all_slots_data.append((f"Slot {i+1}", slot))
            all_slots_data.append(("Relic", relics))
            
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            rl.setAlignment(Qt.AlignmentFlag.AlignLeft)

            used = set()
            for slot_label, slot_data in all_slots_data:
                if not slot_data:
                    continue
                # Dedup: wybierz pierwszy niewykorzystany przedmiot
                chosen = slot_data[0]
                for i, c in enumerate(slot_data):
                    name = c["item"].lower().strip().replace("'", "'")
                    if name not in used:
                        chosen = c
                        used.add(name)
                        break
                item_name = chosen["item"]
                pct = chosen["pct"]

                item_container = QWidget()
                item_cont_lay = QVBoxLayout(item_container)
                item_cont_lay.setContentsMargins(0, 0, 0, 0)
                item_cont_lay.setSpacing(1)
                item_cont_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

                item_data = {"to": item_name, "alts": [s for s in slot_data if s["item"] != item_name]}
                icon = self._make_icon(item_data, 38)
                item_cont_lay.addWidget(icon)
                
                pct_lbl = QLabel(f"{pct}%")
                pct_lbl.setStyleSheet("font-size: 8px; color: #94a3b8; font-weight: bold;")
                pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                item_cont_lay.addWidget(pct_lbl)
                
                rl.addWidget(item_container)
            
            self.mini_layout.addWidget(row)
        else:
            # Regular community build
            if not self.current_build.final_items:
                return
            self._add_mini_item_row(self.current_build.final_items[:8], 38)
            if self.current_build.swap_items:
                self._add_mini_swap_row(self.current_build.swap_items)

    def _populate_mini_empty(self, error_message=None):
        clear_layout(self.mini_layout)
        card = QFrame()
        card.setObjectName("mini_empty_card")
        card.setFixedHeight(45)
        cl = QVBoxLayout(card)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.setContentsMargins(10, 0, 10, 0)
        
        text = _t("conn_error") if error_message else _t("no_builds_found")
        msg = QLabel(text)
        msg.setObjectName("mini_empty_text")
        msg.setStyleSheet("font-size: 11px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(msg)

        self.mini_layout.addStretch()
        self.mini_layout.addWidget(card)
        self.mini_layout.addStretch()

    def _add_mini_item_row(self, items, size):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for name in items:
            rl.addWidget(self._make_icon(name, size))
        self.mini_layout.addWidget(row)

    def _add_mini_swap_row(self, swaps):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        grouped = {}
        for s in swaps:
            f = s.get('from')
            if f not in grouped:
                grouped[f] = []
            grouped[f].append(s)
        for from_item, group in grouped.items():
            rl.addWidget(self._make_icon(from_item, 32))
            arrow = QLabel("➔")
            arrow.setProperty("class", "swap_arrow")
            rl.addWidget(arrow)
            for i, s in enumerate(group):
                if i > 0:
                    slash = QLabel("/")
                    slash.setStyleSheet("color: #8E9AAF; font-weight: bold; font-size: 14px;")
                    rl.addWidget(slash)
                rl.addWidget(self._make_icon(s, 32))
            rl.addSpacing(15)
        self.mini_layout.addWidget(row)

    # ============================================================ HELPERS
    def _refresh_title(self):
        """Updates header text depending on page and mode."""
        logo_path = resource_path("assets", "logo.svg") 
        header_size = 40 if not self.is_expanded else 50

        if self._current_page == "home":
            if os.path.exists(logo_path):
                self.update_logo()
            else:
                self.god_label.setText("KuzenBot")
            self.patch_badge.hide()
            return
            
        elif self._current_page == "search":
            if os.path.exists(logo_path):
                self.update_logo()
            else:
                self.god_label.setText(_t("manual_mode").upper())
            self.patch_badge.hide()
            return
            
        elif self._current_page == "list":
            full = f"{self._current_god_name} {_t('builds_suffix')}".upper()
            self.patch_badge.hide()
            
        elif self._current_page == "detail":
            if self.current_build:
                full = self.current_build.title.upper()
                self.patch_badge.setText(self.current_build.patch)
                self.patch_badge.setVisible(False)
                if hasattr(self.list_screen, 'style_patch_badge'):
                    self.list_screen.style_patch_badge(
                        self.patch_badge,
                        self.current_build.patch,
                        self.list_screen.current_patch,
                        font_size_px=10
                    )
            else:
                full = f"{self._current_god_name}: {_t('loading')}".upper()

        else:
            # === POPRAWKA: Tryb Auto Wait wpada tutaj. Teraz poprawnie wywołujemy update_logo! ===
            if os.path.exists(logo_path):
                self.update_logo()
            else:
                self.god_label.setText("KuzenBot")
            self.patch_badge.hide()
            return  # Przerywamy działanie funkcji

        # --- TEN KOD WYKONA SIĘ TYLKO DLA EKRANÓW 'list' ORAZ 'detail' ---
        self.god_label.setProperty("full_title", full)
        
        if not self.is_expanded:
            self.god_label.setStyleSheet("font-size: 12px; font-weight: 800;")
            limit = 180 if self._current_page == "detail" else 180 
        else:
            self.god_label.setStyleSheet("")
            
            if self._current_page == "detail":
                limit = 340
            elif self._current_page == "list":
                limit = 420
            else:
                limit = 440

        self.god_label.ensurePolished()
        fm = self.god_label.fontMetrics()

        display = fm.elidedText(full, Qt.TextElideMode.ElideRight, limit)
        self.god_label.setText(display)

    @staticmethod
    def _get_icon_path(name):
        if name.lower().strip() == "acorn":
            return resource_path("assets", "acorn.png")
            
        safe = re.sub(r'[^a-z0-9]', '_', name.strip().lower()).strip('_') + ".png"
        
        local_path = resource_path("assets", "items", safe)
        if os.path.exists(local_path):
            return local_path
            
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        cached_path = os.path.join(appdata, "KuzenBot", "cache", "items", safe)
        
        return cached_path 

    def _ensure_item_icon(self, item_name, size):
        """Downloads item icon from CDN to AppData cache if not found."""
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        cache_dir = os.path.join(appdata, "KuzenBot", "cache", "items")
        os.makedirs(cache_dir, exist_ok=True)

        safe = re.sub(r'[^a-z0-9]', '_', item_name.strip().lower()).strip('_') + ".png"
        filepath = os.path.join(cache_dir, safe)

        if os.path.exists(filepath):
            return filepath

        import requests as http_req
        import time # <--- DODANO
        normalized = item_name.strip().replace("’", "'").lower()
        req_timeout = 1.5 
        
        # Unikalny znacznik czasu omijający cache serwerów (Cache Buster)
        buster = int(time.time())

        # 1. Próba z lokalnej bazy danych (item_db)
        if hasattr(self, 'item_db') and self.item_db:
            info = self.item_db.get(normalized)
            if isinstance(info, dict) and info.get("image_url"):
                try:
                    url = info["image_url"]
                    # Dodajemy buster do URL-a z bazy
                    url += f"&v={buster}" if "?" in url else f"?v={buster}"
                    r = http_req.get(url, timeout=req_timeout)
                    if r.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(r.content)
                        return filepath
                except Exception:
                    pass

        camel = item_name.strip().replace(" ", "").replace("'", "").replace("-", "")
        
        # 2. Próba z Wiki CDN
        for prefix in ["T3_", "T2_", "T1_", "Relic_", "Consumable_", "Curio_", ""]:
            filename = f"{prefix}{camel}.png"
            url = f"https://wiki.smite2.com/images/thumb/{filename}/80px-{filename}?v={buster}" # <--- DODANO BUSTER
            try:
                r = http_req.get(url, timeout=req_timeout)
                if r.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    return filepath
            except Exception:
                continue

        # 3. Próba ze SmiteSource CDN
        for prefix in ["T3_", "T2_", "T1_", "Relic_", "Consumable_"]:
            cdn_name = f"Icon_{prefix}{camel}.png"
            url = f"https://cdn.smitesource.com/Items/{prefix.strip('_')}/{cdn_name}?v={buster}" # <--- DODANO BUSTER
            try:
                r = http_req.get(url, timeout=req_timeout)
                if r.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    return filepath
            except Exception:
                continue

        return ""

    def _make_icon(self, item_data, size):
        name = item_data.get("to", "Unknown") if isinstance(item_data, dict) else str(item_data)
        icon = QLabel()
        icon.setFixedSize(size, size)
        icon.setObjectName("item_icon")
        icon.setProperty("item_data", item_data)
        icon.setMouseTracking(True)
        icon.installEventFilter(self)
        
        path = self._get_icon_path(name)
        
        if not hasattr(self, '_icon_cache'):
            self._icon_cache = {}
            
        cache_key = (name, size)
        
        if os.path.exists(path):
            if cache_key in self._icon_cache:
                pix = self._icon_cache[cache_key]
            else:
                pix = QPixmap(path).scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._icon_cache[cache_key] = pix
            icon.setPixmap(pix)
        else:
            # 1. Natychmiast pokaż stan ładowania (UI się nie zawiesza!)
            icon.setText("⏳")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet(f"""
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #94a3b8;
                font-size: {int(size * 0.4)}px;
                font-weight: bold;
            """)
            
            # 2. Odpal asynchroniczne pobieranie w tle
            if not hasattr(self, '_async_workers'):
                self._async_workers = set()
                
            worker = AsyncIconDownloader(self, name, size, icon)
            self._async_workers.add(worker)
            worker.icon_ready.connect(self._on_async_icon_ready)
            # Usuwamy workera z pamięci po zakończeniu, by nie wyciekał RAM
            worker.finished.connect(lambda w=worker: self._async_workers.discard(w) if w in getattr(self, '_async_workers', set()) else None)
            worker.start()

        # Przezroczystość (aplikowana na koniec)
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        config = getattr(self, '_config', {})
        items_val = config.get("opacity_items", 1.0)
        effect = QGraphicsOpacityEffect(icon)
        effect.setOpacity(items_val)
        icon.setGraphicsEffect(effect)

        return icon

    def _on_async_icon_ready(self, name, path, icon, size):
        try:
            # Zabezpieczenie: jeśli gracz zdążył zmienić zakładkę podczas pobierania, 
            # widget mógł zostać usunięty z pamięci.
            icon.objectName()
        except RuntimeError:
            return

        if path and os.path.exists(path):
            # Sukces - wgrywamy pobrany obrazek
            cache_key = (name, size)
            pix = QPixmap(path).scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._icon_cache[cache_key] = pix
            
            icon.setText("")
            icon.setStyleSheet("") # Resetujemy tło loadera
            icon.setPixmap(pix)
        else:
            # Fallback - Przedmiot usunięty lub nie istnieje na serwerze
            is_removed = True
            if hasattr(self, 'item_db') and self.item_db:
                if name.lower().strip().replace("’", "'") in self.item_db or name.lower().strip() == "acorn":
                    is_removed = False
            
            if is_removed:
                icon.setText("❌")
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon.setStyleSheet(f"""
                    background-color: rgba(239, 68, 68, 0.1);
                    border: 1px dashed #ef4444;
                    border-radius: 4px;
                    color: #ef4444;
                    font-size: {int(size * 0.4)}px;
                    font-weight: bold;
                """)
            else:
                icon.setText("?")
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon.setStyleSheet(f"""
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    color: #C5A059;
                    font-size: {int(size * 0.5)}px;
                    font-weight: bold;
                """)
                
        # Odświeżenie przezroczystości po załadowaniu grafiki
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        config = getattr(self, '_config', {})
        items_val = config.get("opacity_items", 1.0)
        effect = QGraphicsOpacityEffect(icon)
        effect.setOpacity(items_val)
        icon.setGraphicsEffect(effect)

    def _on_card_clicked(self, index):
        """Proxy: list card click triggers build_selected signal."""
        self.build_selected.emit(index)

    # ============================================================ SOURCE TOGGLE (mini header)
    def _toggle_build_source(self):
        current = self.list_screen.toggle.active_value
        new_val = "stats" if current == "builds" else "builds"
        self.list_screen.toggle.set_value(new_val)

    def set_source_button(self, source):
        if source == "stats":
            self.btn_source_toggle.setIcon(self._colorize_icon(resource_path("assets", "stats_mask.svg"), "#94a3b8"))
            self.btn_source_toggle.setToolTip(_t("stat_builds"))
        else:
            self.btn_source_toggle.setIcon(self._colorize_icon(resource_path("assets", "community_mask.svg"), "#94a3b8"))
            self.btn_source_toggle.setToolTip(_t("comm_builds"))

    # ============================================================ TOOLTIP / EVENT FILTER
    def eventFilter(self, obj, event):
        tooltip_widgets = [
            getattr(self, 'god_label', None),
            getattr(self, 'btn_home', None),
            getattr(self, 'btn_mini_role', None),
            getattr(self, 'btn_mini_aspect', None),
            getattr(self, 'btn_toggle', None),
            getattr(self, 'btn_back', None),
            getattr(self, 'btn_lock', None),
            getattr(self, 'btn_source_toggle', None),
            getattr(self, 'btn_close', None),
            getattr(self, 'btn_settings', None),
        ]
        if obj is None:
            return super().eventFilter(obj, event)

        if obj.objectName() in ["item_icon", "mode_info_btn"] or obj in tooltip_widgets:
            if event.type() == QEvent.Type.Enter:
                text = ""
                if obj == getattr(self, 'god_label', None):
                    text = obj.property("full_title")
                elif obj == getattr(self, 'btn_home', None):
                    text = _t("tt_home")
                elif obj == getattr(self, 'btn_mini_role', None):
                    # Tłumaczymy rolę przed wrzuceniem do formatowania
                    role_display = _t("role_any") if self._role_filter == "Any" else self._role_filter
                    text = _t("tt_role").format(role=role_display)
                elif obj == getattr(self, 'btn_mini_aspect', None):
                    text = _t("tt_aspect_on") if self._aspect_filter == 2 else _t("tt_aspect_off")
                elif obj == getattr(self, 'btn_back', None):
                    text = _t("tt_back")
                elif obj == getattr(self, 'btn_toggle', None):
                    text = _t("tt_collapse") if self.is_expanded else _t("tt_expand")
                elif obj == getattr(self, 'btn_lock', None):
                    is_locked = getattr(self, '_is_locked', False)
                    text = _t("tt_locked") if is_locked else _t("tt_unlocked")
                elif obj == getattr(self, 'btn_source_toggle', None):
                    source = self.list_screen.toggle.active_value
                    text = _t("tt_comm") if source == "builds" else _t("tt_stats")
                elif obj == getattr(self, 'btn_close', None):
                    text = _t("tt_close")
                elif obj == getattr(self, 'btn_settings', None):
                    text = _t("tt_settings")
                elif obj.objectName() == "mode_info_btn":
                    text = obj.property("info_text")
                else:
                    data = obj.property("item_data")
                    if isinstance(data, dict):
                        name = data.get('to', 'Unknown')
                        text = f"<b>{name}</b>"
                        if 'alts' in data and data['alts']:
                            text += f"<br><br><b style='color:#94a3b8;'>{_t('alternatives')}</b><br>"
                            for a in data['alts']:
                                icon_path = self._get_icon_path(a['item'])
                                if os.path.exists(icon_path):
                                    file_url = 'file:///' + icon_path.replace('\\', '/')
                                    text += f"<div style='margin:2px 0;'><img src='{file_url}' width='20' height='20' style='vertical-align:middle;margin-right:4px;'> {a['item']}: <b>{a['pct']}%</b></div>"
                                else:
                                    text += f"<div style='margin:2px 0;'>{a['item']}: <b>{a['pct']}%</b></div>"
                    else:
                        text = str(data) if data else ""
                
                if text:
                    self.tooltip_label.setText(text)
                    
                    # --- NAJWIĘKSZY SEKRET PYQT v2: Zapobiegamy mruganiu na środku ekranu! ---
                    # Windows czasem ignoruje ujemne koordynaty przy pierwszym rysowaniu.
                    # 1. ZERUJEMY przezroczystość całkowicie ZANIM pokażemy okno do obliczeń!
                    self.tooltip.setWindowOpacity(0.0)
                    
                    # 2. Pokazujemy okno "w tle" - PyQt posłusznie kurczy je wokół nowego tekstu
                    self.tooltip.show()
                    self.tooltip.adjustSize()
                    
                    # 3. Teraz wymiary są w 100% poprawne
                    tw = self.tooltip.width()
                    th = self.tooltip.height()
                    
                    # 4. Obliczamy pozycję
                    g = obj.mapToGlobal(obj.rect().topLeft())
                    tx = g.x() + (obj.width() // 2) - (tw // 2)
                    ty = g.y() - th - 6
                    
                    # Zabezpieczenie przed wyjściem za ekran nakładki
                    from PyQt6.QtGui import QGuiApplication
                    screen = QGuiApplication.screenAt(g)
                    if not screen:
                        screen = QGuiApplication.primaryScreen()
                    avail_rect = screen.availableGeometry()

                    if tx < avail_rect.left(): 
                        tx = avail_rect.left()
                    elif tx + tw > avail_rect.right(): 
                        tx = avail_rect.right() - tw
                        
                    # Zapobiegamy też "wcięciu" w górną krawędź ekranu (np. nad przyciskiem Home)
                    if ty < avail_rect.top():
                        ty = g.y() + obj.height() + 6 # Pokaż go POD elementem, jeśli nie ma miejsca nad
                    # ------------------------------------------------------------------------
                        
                    # 5. Przesuwamy w niewidzialności na właściwą pozycję nad przyciskiem
                    self.tooltip.move(tx, ty)
                    
                    # 6. Przywracamy pełną widoczność!
                    self.tooltip.setWindowOpacity(1.0)
                    
            elif event.type() == QEvent.Type.Leave:
                self.tooltip.hide()
        return super().eventFilter(obj, event)

    # ============================================================ DRAGGING
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.XButton1:
            # Przycisk "Wstecz" myszy -> Historia wstecz
            self.go_back()
        elif event.button() == Qt.MouseButton.XButton2:
            # Przycisk "Dalej" myszy -> Historia naprzód
            self.go_forward()



    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            event.accept()

            # --- MAGNETYCZNE PRZYCIĄGANIE DO KRAWĘDZI (Smart Edge Snapping) ---
            from PyQt6.QtGui import QGuiApplication
            from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
            
            snap_threshold = 30  # Siła magnesu w pikselach (odległość, przy której okno łapie krawędź)
            
            screen = QGuiApplication.screenAt(self.geometry().center())
            if not screen:
                screen = QGuiApplication.primaryScreen()
                
            # ZMIANA: Używamy pełnej fizycznej matrycy monitora (ignoruje pasek zadań)
            avail_rect = screen.geometry() 
            current_rect = self.geometry()
            
            target_x = current_rect.x()
            target_y = current_rect.y()
            snapped = False
            
            # 1. Sprawdzanie osi X (Lewa / Prawa krawędź)
            if abs(current_rect.left() - avail_rect.left()) < snap_threshold:
                target_x = avail_rect.left()
                snapped = True
            elif abs(current_rect.right() - avail_rect.right()) < snap_threshold:
                target_x = avail_rect.right() - current_rect.width()
                snapped = True
                
            # 2. Sprawdzanie osi Y (Górna / Dolna krawędź)
            if abs(current_rect.top() - avail_rect.top()) < snap_threshold:
                target_y = avail_rect.top()
                snapped = True
            elif abs(current_rect.bottom() - avail_rect.bottom()) < snap_threshold:
                target_y = avail_rect.bottom() - current_rect.height()
                snapped = True
                
            # Jeśli okno złapało krawędź, wykonaj miękką animację przyciągnięcia!
            if snapped:
                self._snap_anim = QPropertyAnimation(self, b"pos")
                self._snap_anim.setDuration(150) # Bardzo szybka, ledwie zauważalna animacja (0.15 sekundy)
                self._snap_anim.setStartValue(self.pos())
                self._snap_anim.setEndValue(QPoint(target_x, target_y))
                self._snap_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self._snap_anim.start()

    def update_mini_buttons_visibility(self):
        """Dynamically manages control visibility based on mode and config."""
        config = getattr(self, '_config', {})
        
        if not self.is_expanded:
            # --- TRYB MINI ---
            self.btn_lock.setVisible(not config.get("hide_mini_lock", False))
            self.btn_toggle.setVisible(not config.get("hide_mini_toggle", False))
            
            # Przycisk źródła (guzik) pokazuje się teraz na ekranie listy ORAZ na ekranie głównym (home)
            if self._current_page in ["list", "home"]:
                self.btn_source_toggle.setVisible(not config.get("hide_mini_source", False))
            else:
                self.btn_source_toggle.hide()
                
            # Filtry roli i aspektu nadal pokazują się wyłącznie na ekranie listy
            if self._current_page == "list":
                hide_role = config.get("hide_mini_role", False)
                hide_aspect = config.get("hide_mini_aspect", False)
                self.btn_mini_role.setVisible(not hide_role)
                self.btn_mini_aspect.setVisible(not hide_aspect)
                
                # Całkowicie ukrywamy kontener filtrów, jeśli oba są wyłączone
                self.mini_header_filters.setVisible(not (hide_role and hide_aspect))
            else:
                self.mini_header_filters.hide()
        else:
            # --- TRYB EXTENDED (Domyślny wygląd) ---
            # W trybie rozszerzonym wszystko ma być zawsze widoczne
            self.btn_lock.show()
            self.btn_toggle.show()
            self.btn_source_toggle.hide()
            self.mini_header_filters.hide()
        
        # --- NOWOŚĆ: Sterowanie guzikiem Aktualizacji ---
        if getattr(self, '_has_update', False):
            # Pobieramy przetłumaczony tekst i wklejamy do niego pobraną wersję
            translated_text = _t("update_btn_ext").format(version=self._update_version)
            
            if not self.is_expanded:
                # W trybie MINI
                self.btn_update.setText("🚀")
                self.btn_update.setFixedSize(28, 28)
                self.btn_update.setMinimumWidth(28)
                self.btn_update.setMaximumWidth(28)
                self.btn_update.setToolTip(translated_text)
            else:
                # W trybie EXTENDED
                self.btn_update.setText(f"🚀 {translated_text}")
                self.btn_update.setMinimumWidth(100)
                self.btn_update.setMaximumWidth(160)
                self.btn_update.setFixedHeight(26)
                self.btn_update.setToolTip("") 
            self.btn_update.show()
        else:
            self.btn_update.hide()

    def apply_opacities(self):
        """Manages independent opacity channels (App / Background / Items)."""
        config = getattr(self, '_config', {})
        app_val = config.get("opacity_app", 1.0)
        bg_text_val = config.get("opacity_bg_text", 1.0)
        items_val = config.get("opacity_items", 1.0)

        # Kanał 1: Globalne okno (Wbudowana metoda Qt)
        self.setWindowOpacity(app_val)

        # Kanał 2: Przezroczystość tła kontenera głównego
        # Bazowy kolor tła z pliku styles.py to rgba(10, 15, 25, 245). Max alfa to 245.
        # Skalujemy maksymalną alfę przez wartość suwaka tła.
        alpha = int(bg_text_val * 245)
        self.container.setStyleSheet(f"""
            #main_container {{
                background-color: rgba(10, 15, 25, {alpha});
            }}
        """)

        # Kanał 3: Przezroczystość wszystkich ikon przedmiotów znajdujących się aktualnie na ekranie
        from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel
        icons = self.findChildren(QLabel, "item_icon")
        for icon in icons:
            effect = icon.graphicsEffect()
            if not effect or not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(icon)
                icon.setGraphicsEffect(effect)
            effect.setOpacity(items_val)

    def retranslate_ui(self):
        """Propagates translation refresh to all child screens."""
        if hasattr(self, 'home_screen'):
            self.home_screen.retranslate_ui()
        if hasattr(self, 'search_screen'):
            # Jeśli SearchScreen ma metodę resetującą/tłumaczącą, też ją tu wywołaj:
            if hasattr(self.search_screen, '_reset_status_label'):
                self.search_screen._reset_status_label()

    def _colorize_icon(self, image_path, hex_color):
        """Dynamically applies color tint to images (SVG via XML, PNG via mask)."""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
        from PyQt6.QtCore import QByteArray

        if image_path.endswith(".svg"):
            try:
                # 1. Wczytujemy plik SVG jako zwykły tekst
                with open(image_path, "r", encoding="utf-8") as f:
                    svg_data = f.read()
                
                # 2. Bezpośrednio podmieniamy biały kolor (fill / stroke) na kolor naszego motywu
                svg_data = svg_data.replace('fill="#ffffff"', f'fill="{hex_color}"')
                svg_data = svg_data.replace('stroke="#ffffff"', f'stroke="{hex_color}"')
                
                # 3. Zmieniony tekst ładujemy z powrotem jako grafikę
                pixmap = QPixmap()
                pixmap.loadFromData(QByteArray(svg_data.encode("utf-8")), "SVG")
                return QIcon(pixmap)
            except Exception as e:
                print(f"Error colorizing SVG: {e}")
                return QIcon(image_path)
        else:
            # Stara metoda (fallback) dla zwykłych plików .png
            pixmap = QPixmap(image_path)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor(hex_color))
            painter.end()
            return QIcon(pixmap)

    def _colorize_logo(self, hex_color):
        """Podmienia kolor dla elementu z id='bot-text'."""
        import re
        svg_path = resource_path("assets", "logo.svg")
        try:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_data = f.read()
            
            # Znajduje path z id="bot-text" i podmienia jego atrybut fill
            # Regex tłumaczenie: znajdź (id="bot-text".*?fill=")(#[0-9a-fA-F]+) i zamień na $1 + hex_color
            new_svg = re.sub(r'(id="bot-text"[^>]*fill=")(#[0-9a-fA-F]+)(")', rf'\g<1>{hex_color}\g<3>', svg_data)
            
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(new_svg.encode("utf-8")), "SVG")
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error colorizing Logo: {e}")
            return QIcon(svg_path)
        
    def update_logo(self):
        """Refreshes the logo according to the current theme."""
        accent = getattr(self, '_config', {}).get("theme", "gold")
        
        # PERFEKCYJNIE DOPASOWANE KOLORY Z GŁÓWNEGO CSS APLIKACJI
        theme_colors = {
            "gold": "#C5A059",      # Dokładny Smite Gold (używany dla reliktów)
            "ruby": "#EF4444",      # Czerwień (używana na przyciskach zamykania i błędach)
            "blizzard": "#3B82F6",  # Niebieski (używany dla starterów, suwaków i aktywnych checkboxów)
            "emerald": "#10B981",   # Szmaragdowy zieleń (używana dla upvote'ów)
            "void": "#8B5CF6",      # Głęboki fiolet
            "cyber": "#F472B6",     # Cyjan
            "toxic": "#A3E635",     # Toksyczna, jasna zieleń
            "abyss": "#FF003C"      # Mroczna czerwień
        }
        
        # Zmieniamy domyślny fallback na Smite Gold
        accent_hex = theme_colors.get(accent, "#C5A059")
        
        colored_logo = self._colorize_logo(accent_hex)
        # Zostawiamy dopasowanie rozmiaru
        self.god_label.setPixmap(colored_logo.pixmap(QSize(200, 50)))

    def set_status_indicator(self, state="idle"):
        """Zmienia kolor diody statusu: 'idle', 'fetching', 'error'."""
        if not hasattr(self, 'status_diode'):
            return
            
        base_style = "border-radius: 5px;" # Usunęliśmy margin
        
        if state == "fetching":
            self.status_diode.setStyleSheet(f"{base_style} background-color: #f59e0b;") 
            self.status_diode.setToolTip("Pobieranie danych...")
        elif state == "error":
            self.status_diode.setStyleSheet(f"{base_style} background-color: #ef4444;")
            self.status_diode.setToolTip("Błąd komunikacji")
        else:
            self.status_diode.setStyleSheet(f"{base_style} background-color: #10b981;")
            self.status_diode.setToolTip("Gotowy")