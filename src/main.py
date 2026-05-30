import sys
import os
import requests
import dataclasses
import json
import psutil
import time
import urllib.request
import tempfile
import subprocess

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

from core.translations import Translator, _t
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

CURRENT_VERSION = "1.0.0"

STATE_LOADING = "loading"
STATE_DATA = "data"
STATE_ERROR = "error"
STATE_EMPTY = "empty"

if "SSLKEYLOGFILE" in os.environ:
    del os.environ["SSLKEYLOGFILE"]

from PyQt6.QtWidgets import (QApplication, QInputDialog, QLineEdit,
                             QSystemTrayIcon, QMenu, QDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QObject, QTimer, QPoint
from PyQt6.QtGui import QGuiApplication, QIcon

def parse_god_data(json_data: dict) -> GodData:
    builds = []
    seen_stats_roles = {}

    for b in json_data.get('builds', []):
        build = SmiteBuild(**b)
        
        if build.is_valid():
            if getattr(build, 'is_stats', False):
                role = build.roles[0] if build.roles else "Unknown"
                aspect = getattr(build, 'is_aspect', False)
                key = f"{role}_{aspect}"
                
                if key not in seen_stats_roles:
                    seen_stats_roles[key] = build
                else:
                    existing = seen_stats_roles[key]
                    new_insufficient = getattr(build, 'insufficient_data', False)
                    old_insufficient = getattr(existing, 'insufficient_data', False)
                    
                    if not new_insufficient and old_insufficient:
                        seen_stats_roles[key] = build
                    elif not new_insufficient and not old_insufficient:
                        if getattr(build, 'upvotes', 0) > getattr(existing, 'upvotes', 0):
                            seen_stats_roles[key] = build
            else:
                builds.append(build)
        else:
            print(f"[Data] Skipped incomplete build: {b.get('title', 'Untitled')}")
    
    builds.extend(seen_stats_roles.values())
    
    builds.sort(key=lambda x: (1 if getattr(x, 'insufficient_data', False) else 0, -getattr(x, 'upvotes', 0)))

    return GodData(
        god_name=json_data.get('god_name', 'Unknown'),
        current_patch=json_data.get('current_patch', 'Unknown'),
        builds=builds,
        error=json_data.get('error')
    )

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.logger import setup_logging, logger
setup_logging()

from core.hotkeys import HotkeyListener
from ui.overlay import SmiteOverlay
from ui.settings_dialog import SettingsDialog
from core.scanner import GameScanner
from data.models import GodData, SmiteBuild
from core.image_manager import ImageManager

class BuildFetchWorker(QThread):
    """Fetches build data from the remote API in a background thread."""
    list_ready = pyqtSignal(object)
    details_ready = pyqtSignal(object)

    def __init__(self, god_name, source="builds"):
        super().__init__()
        self.god_name = god_name
        self.source = source

    def run(self):
        try:
            if getattr(self, 'is_obsolete', False): return
            
            base_url = "http://92.5.91.226:8000/api/v1"
            endpoint = f"{base_url}/stats/{self.god_name}" if self.source == "stats" else f"{base_url}/builds/{self.god_name}"

            print(f"[API] Fetching from: {endpoint}")
            response = requests.get(endpoint, timeout=15)
            
            if getattr(self, 'is_obsolete', False): return
            
            if response.status_code == 200:
                json_data = response.json()
                god_data = parse_god_data(json_data)
                
                if not god_data.builds:
                    self.list_ready.emit(STATE_EMPTY)
                else:
                    self.list_ready.emit(god_data)
            elif response.status_code == 404:
                print(f"[API] No data available for: {self.god_name}")
                self.list_ready.emit(STATE_EMPTY)
            else:
                print(f"[API] Server error: {response.status_code}")
                self.list_ready.emit(STATE_ERROR)
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"[API] Connection error: {e}")
            self.list_ready.emit(STATE_ERROR)
        except Exception as e:
            print(f"[API] Unexpected error: {e}")
            self.list_ready.emit(STATE_ERROR)


class DetailsFetchWorker(QThread):
    """Fetches build details (abilities, swaps) from the remote API."""
    details_ready = pyqtSignal(object)
    
    def __init__(self, build_obj):
        super().__init__()
        self.build_obj = build_obj
        
    def run(self):
        if getattr(self.build_obj, 'is_stats', False):
            self.details_ready.emit(self.build_obj)
        else:
            try:
                payload = dataclasses.asdict(self.build_obj)
                response = requests.post("http://92.5.91.226:8000/api/v1/details", json=payload, timeout=10)
                
                if response.status_code == 200:
                    updated_build = SmiteBuild(**response.json())
                    self.details_ready.emit(updated_build)
                else:
                    print(f"⚠️ [API Details] Server rejected request! HTTP: {response.status_code}")
                    print(f"Response body: {response.text}")
                    self.details_ready.emit(self.build_obj)
            except Exception as e:
                print(f"❌ [API Error] Failed to fetch details: {e}")
                self.details_ready.emit(self.build_obj)

class PortraitFetchWorker(QThread):
    """Resolved immediately — portraits are handled by ImageManager."""
    finished = pyqtSignal()

    def __init__(self, god_names):
        super().__init__()
        self.god_names = god_names

    def run(self):
        self.finished.emit()

class ProcessMonitorWorker(QThread):
    """Background thread monitoring game process start/stop."""
    game_started = pyqtSignal()
    game_stopped = pyqtSignal()
    
    def __init__(self, target_process="hemingway"):
        super().__init__()
        self.target_process = target_process.lower()
        self._is_running = None

    def run(self):
        time.sleep(1.5)
        
        while True:
            found = False
            for p in psutil.process_iter():
                try:
                    if self.target_process in p.name().lower():
                        found = True
                        break
                except Exception:
                    pass

            if found and self._is_running is not True:
                self._is_running = True
                self.game_started.emit()
            elif not found and self._is_running is not False:
                self._is_running = False
                self.game_stopped.emit()

            time.sleep(3)

class UpdateCheckerWorker(QThread):
    """Asynchronously checks for new versions on GitHub."""
    update_available = pyqtSignal(str, str)

    def run(self):
        url = "https://raw.githubusercontent.com/kicpir99/KuzenBot/main/version.json"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'KuzenBot-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get("version", "1.0.0")
                download_url = data.get("url", "https://github.com/kicpir99/KuzenBot/releases")
                
                curr_parts = [int(x) for x in CURRENT_VERSION.split(".")]
                latest_parts = [int(x) for x in latest_version.split(".")]
                
                if latest_parts > curr_parts:
                    self.update_available.emit(latest_version, download_url)
                    
        except Exception as e:
            print(f"⚠️ [Updater] Failed to check for updates: {e}")

class UpdateDownloaderWorker(QThread):
    """Downloads the installer in the background and runs it silently."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "KuzenBot_Update.exe")
            
            def report_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = int(block_num * block_size * 100 / total_size)
                    self.progress.emit(min(percent, 100))

            print(f"📥 [Updater] Downloading update from: {self.download_url}")
            urllib.request.urlretrieve(self.download_url, installer_path, reporthook=report_hook)
            self.finished.emit(installer_path)
        except Exception as e:
            self.error.emit(str(e))

class SmiteController(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("KuzenBot")
        self.app.setQuitOnLastWindowClosed(False)
        self.server_name = "KuzenBot_SingleInstanceServer"
        self.socket = QLocalSocket()
        self.socket.connectToServer(self.server_name)
        
        if self.socket.waitForConnected(500):
            print("⚠️ Application already running. Sending wake signal and exiting.")
            self.socket.write(b"WAKEUP")
            self.socket.flush()
            self.socket.waitForBytesWritten(500)
            sys.exit(0)
            
        self.server = QLocalServer()
        self.server.removeServer(self.server_name)
        self.server.listen(self.server_name)
        self.server.newConnection.connect(self._handle_new_connection)
        
        icon_path = resource_path("assets", "logo.ico")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))
        self._config = self._load_config()
        Translator.set_language(self._config.get("language", "en"))
        self.overlay = SmiteOverlay()
        self.image_manager = ImageManager()
        
        self.current_god_data = None
        self.all_builds = []
        self.current_index = 0
        self.data_cache = {"builds": None, "stats": None}
        self.last_fetched_source = "builds"
        self.mode = "AUTO"
        self._config = self._load_config()
        self.build_source = self._resolve_build_source()
        self.hotkey_listener = HotkeyListener()
        self._current_monitor_id = self._config.get("monitor_id", 0)

        self.overlay._config = self._config

        self.scanner = GameScanner()
        self._active_threads = set()
        self.process_monitor = ProcessMonitorWorker("hemingway")

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)
        self.pending_god = None

        self._setup_tray_icon()
        self._setup_connections()
        self._apply_config(self._config)
        self.updater = UpdateCheckerWorker()
        self.updater.update_available.connect(self.on_update_available)
        self._start_services()
        
        self.overlay.navigate_to("home")
        try:
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            pass

    def _handle_new_connection(self):
        """Handles a second instance trying to start — brings this window to front."""
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(500):
            msg = socket.readAll().data()
            if msg == b"WAKEUP":
                print("🔔 Received wake signal from second instance. Bringing window to front.")
                self._show_from_tray()
        socket.disconnectFromServer()

    def _setup_connections(self):
        # Scanner logów (Hemingway.log)
        self.scanner.god_detected.connect(self.on_god_detected)
        self.scanner.lobby_joined.connect(self.on_lobby_joined)
        self.process_monitor.game_started.connect(self.on_game_started)
        self.process_monitor.game_stopped.connect(self.on_game_stopped)
        
        # Nawigacja w overlay
        self.overlay.next_build_requested.connect(self.next_build)
        self.overlay.prev_build_requested.connect(self.prev_build)
        self.overlay.build_selected.connect(self.on_build_card_clicked)
        self.overlay.filter_changed.connect(self.apply_filter)
        
        # Home / Mode / Search signals
        self.overlay.auto_mode_selected.connect(self.on_auto_mode_selected)
        self.overlay.manual_mode_selected.connect(self.on_manual_mode_selected)
        self.overlay.search_requested.connect(self.on_search_requested)

        # Settings from header gear icon
        self.overlay.settings_requested.connect(self._open_settings)
        self.overlay.returned_to_auto_wait.connect(self._on_returned_to_auto_wait)
        
        # Engine source segmented toggles connections
        self.overlay.home_screen.toggle.valueChanged.connect(self.set_build_source)
        self.overlay.list_screen.toggle.valueChanged.connect(self.set_build_source)
        
        # Retry button on error screen
        self.overlay.list_screen.retry_requested.connect(
            lambda: self.start_build_fetch(self._current_god_being_fetched) if hasattr(self, '_current_god_being_fetched') and self._current_god_being_fetched else None
        )
        
        # Synchronize initial values to UI
        self.overlay.home_screen.toggle.set_value(self.build_source, animate=False)
        self.overlay.list_screen.toggle.set_value(self.build_source, animate=False)
        self.overlay.set_source_button(self.build_source)

        # Globalne skróty klawiszowe
        self.hotkey_listener.toggle_overlay.connect(self.toggle_visibility)
        self.hotkey_listener.toggle_click_through.connect(self.overlay.toggle_click_through)
        self.hotkey_listener.next_build_requested.connect(self.next_build)
        self.hotkey_listener.prev_build_requested.connect(self.prev_build)
        self.hotkey_listener.request_god_change.connect(lambda: self.overlay.navigate_to("search"))
        self.hotkey_listener.toggle_source.connect(self.overlay._toggle_build_source)
        self._rebuild_shortcuts(self._config)
        self.app.aboutToQuit.connect(self._on_app_quit)

        self.overlay.update_accepted.connect(self.start_auto_update)
        
    def _on_thread_finished(self):
        thread = self.sender()
        if thread in self._active_threads:
            self._active_threads.discard(thread)
            print(f"[Controller] Thread {thread.__class__.__name__} finished. Active threads: {len(self._active_threads)}")
        thread.deleteLater()

    def _start_services(self):
        self.scanner.start()
        self.hotkey_listener.start()
        self.process_monitor.start()
        self.updater.start()
        
        from PyQt6.QtCore import QTimer
        self.sig_timer = QTimer()
        self.sig_timer.setInterval(200)
        self.sig_timer.timeout.connect(lambda: None)
        self.sig_timer.start()

        self._restore_window_position()
        
        if self.scanner.english_gods:
            self.overlay.set_god_list(self.scanner.english_gods, self.scanner.new_gods)
            self.portrait_worker = PortraitFetchWorker(self.scanner.english_gods)
            self._active_threads.add(self.portrait_worker)
            self.portrait_worker.finished.connect(self._on_thread_finished)
            self.portrait_worker.finished.connect(self.on_portraits_fetched)
            self.portrait_worker.start()

    def on_update_available(self, version, url):
        """Called when a new version is detected by the update checker."""
        print(f"🌟 [Updater] New version found: {version}")
        self.overlay.show_update_button(version, url)

    # ============================================================ SETTINGS
    def _open_settings(self):
        """Open the SettingsDialog."""
        dialog = SettingsDialog(self._config, self.overlay)
        overlay_geo = self.overlay.geometry()
        dx = (overlay_geo.width() - 480) // 2
        dy = (overlay_geo.height() - 400) // 2
        dialog.move(overlay_geo.topLeft() + QPoint(dx, dy))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            self._config = new_config
            self.overlay._config = new_config
            self._apply_config(new_config)
            self._save_config()
            if not self.overlay.isVisible():
                self.overlay.show()

    def _apply_config(self, config):
        """Apply config settings to overlay and shortcuts."""
        theme = config.get("theme", "gold")
        font_style = config.get("font_style", "standard")
        from ui.styles import get_stylesheet
        self.overlay.setStyleSheet(get_stylesheet(theme, font_style))
        
        always_top = config.get("always_on_top", True)
        self.overlay.set_always_on_top(always_top)

        monitor_id = config.get("monitor_id", 0)
        if monitor_id != self._current_monitor_id:
            self._current_monitor_id = monitor_id
            self._move_to_monitor(monitor_id)

        if config.get("minimize_to_tray", False) or config.get("close_to_tray", False):
            self.tray_icon.show()
        else:
            self.tray_icon.hide()

        autostart_enabled = config.get("auto_start", False)
        self._set_autostart(autostart_enabled)

        source = self._resolve_build_source()
        if source != self.build_source:
            self.set_build_source(source)

        self._rebuild_shortcuts(config)

        if hasattr(self.overlay, "update_mini_buttons_visibility"):
            self.overlay.update_mini_buttons_visibility()

        if hasattr(self.overlay, "apply_opacities"):
            self.overlay.apply_opacities()

        if hasattr(self.overlay, "home_screen") and hasattr(self.overlay.home_screen, "toggle"):
            self.overlay.home_screen.toggle.set_theme(theme)
        if hasattr(self.overlay, "list_screen") and hasattr(self.overlay.list_screen, "toggle"):
            self.overlay.list_screen.toggle.set_theme(theme)

    def _rebuild_shortcuts(self, config):
        """Passes new keyboard shortcuts to the global hotkey listener."""
        keybinds = config.get("keybinds", {})

        # Lista wszystkich akcji, które obsługuje nasza aplikacja
        expected_actions = [
            "show_hide", "lock_unlock", "next_build", 
            "prev_build", "quick_search", "toggle_source"
        ]
        
        # Sprawdzamy czy w configu brakuje jakichś wartości i dodajemy domyślne
        for action in expected_actions:
            if action not in keybinds:
                keybinds[action] = self._default_keybind(action)
                
        self.hotkey_listener.update_hotkeys(keybinds)

    def _resolve_build_source(self):
        """Resolve the build_source value, handling 'last_used'."""
        raw = self._config.get("build_source", "builds")
        if raw == "last_used":
            return self._config.get("last_used_source", "builds")
        return raw

    def _default_keybind(self, action):
        defaults = {
            "show_hide": "Alt+S",
            "lock_unlock": "Alt+L",
            "next_build": "Alt+Right",
            "prev_build": "Alt+Left",
            "quick_search": "Alt+D",
            "toggle_source": "Alt+Q",
        }
        return defaults.get(action, "")

    def _setup_tray_icon(self):
        """Create system tray icon with context menu."""
        self.tray_icon = QSystemTrayIcon(self.overlay)
        
        # PODMIANA: Używamy naszego logo zamiast SP_ComputerIcon
        icon_path = resource_path("assets", "logo.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.overlay.style().standardIcon(
                self.overlay.style().StandardPixmap.SP_ComputerIcon
            ))
            
        self.tray_icon.setToolTip("KuzenBot")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Overlay")
        show_action.triggered.connect(self._show_from_tray)
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self._exit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _show_from_tray(self):
        # Zerujemy przezroczystość ZANIM okno się pojawi (zapobiega mruganiu)
        self.overlay.setWindowOpacity(0.0) 
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _exit_app(self):
        self.hotkey_listener.stop()
        QApplication.instance().quit()

    def _on_app_quit(self):
        """Saves window position to config before quitting the application."""
        pos = self.overlay.pos()
        self._config["window_x"] = pos.x()
        self._config["window_y"] = pos.y()
        self._save_config()
        print("💾 [Controller] Zapisano pozycję okna na ekranie.")

    def _restore_window_position(self):
        """Restores window position with safety check for disconnected monitors."""
        x = self._config.get("window_x")
        y = self._config.get("window_y")
        
        if x is not None and y is not None:
            from PyQt6.QtCore import QRect
            # Tworzymy wirtualny kwadrat tam, gdzie okno ma się pojawić
            target_rect = QRect(x, y, self.overlay.width(), self.overlay.height())
            
            # Sprawdzamy czy ten kwadrat przecina się z JAKIMKOLWIEK fizycznym ekranem
            is_visible = any(screen.availableGeometry().intersects(target_rect) for screen in QGuiApplication.screens())
            
            if is_visible:
                self.overlay.move(x, y)
            else:
                print("⚠️ [Controller] Zapisana pozycja jest poza ekranem! Wracam na główny monitor.")
                self._move_to_monitor(self._config.get("monitor_id", 0))
        else:
            # Pierwsze uruchomienie (brak configu)
            self._move_to_monitor(self._config.get("monitor_id", 0))

    def _move_to_monitor(self, monitor_id):
        """Move overlay to the specified monitor on startup."""
        screens = QGuiApplication.screens()
        if 0 <= monitor_id < len(screens):
            target = screens[monitor_id].availableGeometry()
            self.overlay.move(target.topLeft())

    def on_portraits_fetched(self):
        """Called on the main thread after god portraits have been downloaded."""
        from PyQt6.QtCore import QTimer
        if self.scanner.english_gods:
            QTimer.singleShot(0, lambda: self.overlay.set_god_list(self.scanner.english_gods, self.scanner.new_gods))

    def on_god_detected(self, god_name):
        """Handles god detection from Hemingway.log with debouncing."""
        if self.mode == "AUTO":
            print(f"🤖 Automat: Zauważyłem kliknięcie -> {god_name}. Ustawiam stoper...")
            self.pending_god = god_name
            self.debounce_timer.start(1500) # Czas w milisekundach (1.5 sekundy)
            
            # Odświeżenie UI "na żywo", aby gracz wiedział, że bot nie "zaciął się", tylko czeka
            if self.overlay._current_page == "auto_wait":
                self.overlay.auto_wait_screen.status_lbl.setText(f"WYKRYTO: {god_name.upper()}...")

    def _on_debounce_timeout(self):
        """Called when the debounce timer expires — final god selection confirmed."""
        if self.pending_god and self.mode == "AUTO":
            print(f"🚀 Automat: Ostateczny pick to -> {self.pending_god}. Pobieram dane!")
            self.start_build_fetch(self.pending_god)
            self.pending_god = None

    def on_lobby_joined(self):
        """Handles lobby entry event."""
        if self.mode == "AUTO":
            print("🤖 Automat: Wykryto wejście do lobby.")
            
            # Zatrzymujemy ewentualne odliczanie
            self.debounce_timer.stop() 
            self.pending_god = None
            
            self.overlay.auto_wait_screen.show_lobby_waiting()
            self.overlay.navigate_to("auto_wait")

    def prompt_for_god(self):
        """Prompts for manual god name input."""
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        
        god, ok = QInputDialog.getText(self.overlay, "Manual", "God Name:", QLineEdit.EchoMode.Normal)
        if ok and god:
            self.mode = "MANUAL"
            self.start_build_fetch(god)

    def on_auto_mode_selected(self):
        print("🤖 Tryb AUTO aktywowany.")
        self.mode = "AUTO"
        
        # ZMIANA: Pobieramy ostatnią postać używając nowej, dokładnej zmiennej ze skanera
        last_god = getattr(self.scanner, 'last_emitted_god', None)
        
        # Jeśli mamy zapamiętaną postać, pytamy użytkownika co zrobić
        if last_god:
            self.overlay.auto_wait_screen.show_choice(
                last_god,
                yes_cb=self.continue_active_session,
                no_cb=self.reset_active_session
            )
            self.overlay.navigate_to("auto_wait")
        else:
            # Pokaż stan oczekiwania (nowy ekran z animacją)
            self.overlay.auto_wait_screen.show_waiting()
            self.overlay.navigate_to("auto_wait")

    def continue_active_session(self):
        # ZMIANA: Kontynuujemy w oparciu o nową zmienną
        last_god = getattr(self.scanner, 'last_emitted_god', None)
        if last_god:
            print(f"🤖 Kontynuacja sesji dla: {last_god}")
            self.start_build_fetch(last_god)
            
    def reset_active_session(self):
        print("🤖 Resetowanie sesji trybu Auto.")
        # ZMIANA: Resetujemy nową zmienną
        if hasattr(self.scanner, 'last_emitted_god'):
            self.scanner.last_emitted_god = None
        self.overlay.auto_wait_screen.show_waiting()

    def on_manual_mode_selected(self):
        print("🔍 Tryb MANUAL aktywowany.")
        self.mode = "MANUAL"

    def on_search_requested(self, god_name):
        print(f"🔍 Ręczne wyszukiwanie: {god_name}")
        self.start_build_fetch(god_name)

    def start_build_fetch(self, god_name):
        print(f"🚀 [Controller] Rozpoczynam pobieranie dla: {god_name} (Źródło: {self.build_source})")
        if not hasattr(self, '_last_fetched_god') or self._last_fetched_god != god_name.upper():
            self.data_cache = {"builds": None, "stats": None}
            self._last_fetched_god = god_name.upper()
        self._current_god_being_fetched = god_name
        self.last_fetched_source = self.build_source
        self.overlay.set_status_indicator("fetching")
        
        # 1. PRÓBA ŁADOWANIA Z CACHE (Offline-first)
        cached_data = self._load_from_cache(god_name)
        if cached_data:
            print(f"⚡ [Cache] Znaleziono lokalne dane dla: {god_name}")
            data = parse_god_data(cached_data)
            
            
            self.overlay.navigate_to("list")
            self.on_list_ready(data) 
        else:
            # Jeśli brak cache - pokazujemy szkielet (wewnątrz jest już wbudowane przejście do "list")
            self.overlay.show_list_skeleton(god_name)
        
        # 2. CZYSZCZENIE STARYCH WĄTKÓW (bez zmian)
        for thread in list(self._active_threads):
            if isinstance(thread, BuildFetchWorker):
                thread.is_obsolete = True
                thread.quit()
        
        # 3. POBIERANIE Z SERWERA (w tle dla aktualizacji cache)
        worker = BuildFetchWorker(god_name, self.build_source)
        worker.is_obsolete = False
        worker.list_ready.connect(self.on_list_ready)
        worker.details_ready.connect(self.on_details_ready)
        worker.finished.connect(self._on_thread_finished)
        self._active_threads.add(worker)
        worker.start()

    def on_list_ready(self, data):
        sender_worker = self.sender()
        if isinstance(sender_worker, BuildFetchWorker):
            if hasattr(self, '_current_god_being_fetched') and sender_worker.god_name.upper() != self._current_god_being_fetched.upper():
                print(f"⚠️ [Controller] Zignorowano stare dane dla: {sender_worker.god_name}")
                return

        # 1. OBSŁUGA BŁĘDÓW / STANÓW PUSTYCH
        if isinstance(data, str):
            if data == STATE_ERROR:
                self.overlay.list_screen.show_error_screen(_t("err_conn_title"), _t("err_conn_sub"))
                
                self.overlay.set_status_indicator("error")
            elif data == STATE_EMPTY:
                self.overlay.list_screen.show_empty_state()
                # Przy pustym stanie bot nadal działa, więc dajemy zieloną
                self.overlay.set_status_indicator("idle")
            
            self.overlay.navigate_to("list")
            return

        # 2. SUKCES: DANE SĄ OBIEKTEM GODDATA
        print(f"✅ [Controller] Dane odebrane! Liczba buildów: {len(data.builds)}")
        
        
        self.overlay.set_status_indicator("idle")
        
        # Zapis do cache
        self._save_to_cache(data.god_name, dataclasses.asdict(data))
        
        self.current_god_data = data
        self.all_builds = data.builds.copy()
        self.data_cache[self.last_fetched_source] = data
        
        self.overlay.reset_filters()

        # 3. AKTUALIZACJA UI
        if self.overlay._current_page != "list" and self.overlay._current_page != "detail":
            print("⚠️ [Controller] Użytkownik zmienił stronę, nie przełączam widoku na siłę.")
            self.overlay.list_screen.populate(data.builds, data.god_name, data.current_patch)
            return

        self.apply_filter()

        if not self.overlay.isVisible():
            self.overlay.show()


    def on_build_card_clicked(self, index):
        """Handles user clicking a build card in the list."""
        if self.current_god_data and 0 <= index < len(self.current_god_data.builds):
            self.current_index = index
            build = self.current_god_data.builds[index]
            
            # Sprawdź czy mamy już pobrane detale (swapy lub priorytet skilli)
            if build.swap_items or (hasattr(build, 'ability_priority') and build.ability_priority):
                self.update_ui()
            else:
                self.overlay.show_details_skeleton()
                self._fetch_current_details()

    def apply_filter(self):
        if not self.current_god_data or not self.all_builds: return
        
        filtered = self.all_builds
        
        # Filtr aspektu
        aspect = getattr(self.overlay, '_aspect_filter', 0)
        if aspect == 1:  # Normal
            # Używamy bezpiecznego getattr, by zapobiec błędom AttributeError
            filtered = [b for b in filtered if not getattr(b, 'is_aspect', False)]
        elif aspect == 2:  # Aspect
            filtered = [b for b in filtered if getattr(b, 'is_aspect', False)]
        
        # Filtr roli
        role = getattr(self.overlay, '_role_filter', "Any")
        if role != "Any":
            filtered = [
                b for b in filtered 
                if any(role.lower() == r.lower() for r in (getattr(b, 'roles', []) or []))
            ]
            
        # Sortowanie: dla stats → green (current) → yellow (older) → red (insufficient),
        # w każdej grupie po games malejąco. Dla community → po patchu (najnowszy) i upvotes.
        import re
        current_patch_num = 0
        if self.current_god_data and self.current_god_data.current_patch:
            m = re.search(r'OB(\d+)', self.current_god_data.current_patch.upper())
            if m:
                current_patch_num = int(m.group(1))
        def sort_key(b):
            patch_m = re.search(r'OB(\d+)', b.patch.upper()) if b.patch else None
            bpn = int(patch_m.group(1)) if patch_m else 0
            insufficient = getattr(b, 'insufficient_data', False)
            is_stats = getattr(b, 'is_stats', False)
            if is_stats:
                tier = 2 if insufficient else (1 if bpn < current_patch_num else 0)
                return (0, tier, -getattr(b, 'upvotes', 0))
            else:
                return (1, -bpn, -getattr(b, 'upvotes', 0))
        filtered.sort(key=sort_key)
        
        self.current_god_data.builds = filtered
        self.current_index = 0
        
        god_name = self.current_god_data.god_name if self.current_god_data else ""
        patch = self.current_god_data.current_patch if self.current_god_data else None
        self.overlay.show_builds_list(self.current_god_data.builds, god_name, patch)
        
        # USUNIĘTO AUTOMATYCZNE PRZESKAKIWANIE DO DETALI W TRYBIE MINI
        # Chcemy pokazać Mini Listę!

    def on_details_ready(self, updated_build):
        sender_worker = self.sender()
        if isinstance(sender_worker, BuildFetchWorker):
            if hasattr(self, '_current_god_being_fetched') and sender_worker.god_name.upper() != self._current_god_being_fetched.upper():
                print(f"⚠️ [Controller] Zignorowano stary build details w tle dla: {sender_worker.god_name}")
                return
        elif isinstance(sender_worker, DetailsFetchWorker):
            if self.current_god_data and 0 <= self.current_index < len(self.current_god_data.builds):
                current_build = self.current_god_data.builds[self.current_index]
                if sender_worker.build_obj.build_url != current_build.build_url:
                    print(f"⚠️ [Controller] Zignorowano stary build details dla: {sender_worker.build_obj.title}")
                    return

        if not updated_build:
            return

        # Aktualizujemy dane w tle (swapy itp.)
        if self.current_god_data and 0 <= self.current_index < len(self.current_god_data.builds):
            if self.current_god_data.builds[self.current_index].build_url == updated_build.build_url:
                self.current_god_data.builds[self.current_index] = updated_build
                
                # --- 🔥 DODAJ TĘ LINIJKĘ: Zapisujemy świeżo pobrane detale do cache'u! ---
                self._save_to_cache(self.current_god_data.god_name, dataclasses.asdict(self.current_god_data))
                # -----------------------------------------------------------------------
                
                # Aktualizuj UI TYLKO wtedy, gdy użytkownik faktycznie ogląda detale tego buildu
                if self.overlay._current_page == "detail":
                    self.update_ui()


    def _fetch_current_details(self):
        if not self.current_god_data or not self.current_god_data.builds:
            return
        build = self.current_god_data.builds[self.current_index]
        # Pobierz detale jeśli jeszcze nie mamy swapów ani priorytetu umiejętności
        if not build.swap_items and not build.ability_priority:
            worker = DetailsFetchWorker(build)
            worker.details_ready.connect(self.on_details_ready)
            worker.finished.connect(self._on_thread_finished)
            self._active_threads.add(worker)
            worker.start()

    def next_build(self):
        # 1. Skrót działa TYLKO jeśli jesteśmy na ekranie "detail" (w trybie Mini lub Extended)
        if self.overlay._current_page != "detail":
            return

        if self.current_god_data and self.current_god_data.builds:
            # 2. Blokada dla Stats: Szukamy kolejnego "ważnego" buildu
            if self.build_source == "stats":
                next_idx = self.current_index + 1
                while next_idx < len(self.current_god_data.builds):
                    # Sprawdzamy czy build nie jest "pusty" (insufficient_data)
                    if not getattr(self.current_god_data.builds[next_idx], 'insufficient_data', False):
                        self.current_index = next_idx
                        self.update_ui()
                        self._fetch_current_details()
                        return
                    next_idx += 1
                # Jeśli doszliśmy do końca i nie znaleźliśmy, nic nie robimy (blokada na końcu)
                return

            # 3. Blokada dla Community: Zatrzymujemy się na ostatnim buildzie
            if self.current_index < len(self.current_god_data.builds) - 1:
                self.current_index += 1
                self.update_ui()
                self._fetch_current_details()

    def prev_build(self):
        # 1. Skrót działa TYLKO jeśli jesteśmy na ekranie "detail" (w trybie Mini lub Extended)
        if self.overlay._current_page != "detail":
            return

        if self.current_god_data and self.current_god_data.builds:
            # 2. Blokada dla Stats: Szukamy poprzedniego "ważnego" buildu
            if self.build_source == "stats":
                prev_idx = self.current_index - 1
                while prev_idx >= 0:
                    if not getattr(self.current_god_data.builds[prev_idx], 'insufficient_data', False):
                        self.current_index = prev_idx
                        self.update_ui()
                        self._fetch_current_details()
                        return
                    prev_idx -= 1
                # Jeśli doszliśmy do początku, nic nie robimy
                return

            # 3. Blokada dla Community: Zatrzymujemy się na pierwszym buildzie (index 0)
            if self.current_index > 0:
                self.current_index -= 1
                self.update_ui()
                self._fetch_current_details()

    def update_ui(self):
        if self.current_god_data and self.current_god_data.builds:
            if 0 <= self.current_index < len(self.current_god_data.builds):
                build = self.current_god_data.builds[self.current_index]
                self.overlay.update_build(build, self.current_index, len(self.current_god_data.builds))

    def toggle_visibility(self):
        if self.overlay.isVisible():
            self.overlay.hide()
            if not self.tray_icon.isVisible():
                self.tray_icon.show()
        else:
            # Pre-hide trick przed pokazaniem
            self.overlay.setWindowOpacity(0.0)
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()

    def handle_quick_search(self):
        """Global shortcut: Immediately opens the search window."""
        print("[Controller] Globalny skrót: Aktywacja szybkiego wyszukiwania.")
        self.mode = "MANUAL"
        self.overlay.navigate_to("search")
        
        # Wymuszamy pokazanie okna (z pre-hide trickiem)
        if not self.overlay.isVisible():
            self.overlay.setWindowOpacity(0.0)
            self.overlay.show()
            
        self.overlay.raise_()
        self.overlay.activateWindow()
        
        if hasattr(self.overlay.search_screen, "search_input"):
            self.overlay.search_screen.search_input.setFocus()
            self.overlay.search_screen.search_input.selectAll()

    def handle_toggle_source(self):
        """Global shortcut: Toggles between Community and Stats build sources."""
        # Jeśli aktualnie mamy builds -> zmieniamy na stats, i odwrotnie
        new_source = "stats" if self.build_source == "builds" else "builds"
        
        print(f"[Controller] Globalny skrót: Przełączanie źródła buildów na -> {new_source}")
        
        # Wywołujemy Twoją potężną metodę, która podmienia dane, obsługuje cache i odświeża UI!
        self.set_build_source(new_source)

    def _load_config(self) -> dict:
        import json
        config_path = os.path.join(get_project_root(), "assets", "config.json")
        defaults = {
            "language": "en",
            "build_source": "builds",
            "last_used_source": "builds",
            "opacity_app": 1.0,        # Cała aplikacja globalnie
            "opacity_bg_text": 1.0,    # Tylko czarne tło kontenera
            "opacity_items": 1.0,
            "always_on_top": True,
            "monitor_id": 0,
            "minimize_to_tray": False,
            "close_to_tray": False,
            "auto_start": False,
            # --- NOWE OPCJE CUSTOMIZACJI MINI ---
            "hide_mini_source": False,
            "hide_mini_role": False,
            "hide_mini_aspect": False,
            "hide_mini_toggle": False,
            "hide_mini_lock": False,
            "keybinds": {
                "show_hide": "Alt+S",
                "lock_unlock": "Alt+L",
                "next_build": "Alt+Right",
                "prev_build": "Alt+Left",
                "quick_search": "Alt+D",
                "toggle_source": "Alt+Q",
            },
            "theme": "gold",
            "opacity_app": 1.0,
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Merge with defaults (saved values take precedence)
                result = dict(defaults)
                result.update(saved)
                # Ensure keybinds sub-dict is merged
                if "keybinds" in saved:
                    result["keybinds"] = dict(defaults["keybinds"])
                    result["keybinds"].update(saved["keybinds"])
                return result
            except:
                pass
        return defaults

    def _save_config(self):
        import json
        assets_dir = os.path.join(get_project_root(), "assets")
        os.makedirs(assets_dir, exist_ok=True)
        config_path = os.path.join(assets_dir, "config.json")
        try:
            self._config["last_used_source"] = self.build_source
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"DEBUG: Error saving config: {e}")
            pass

    def set_build_source(self, source):
        if self.build_source == source:
            return

        # Cache current before switching
        if self.current_god_data:
            # --- NAPRAWA 1: Zabezpieczenie przed "zatruciem" RAM-u ---
            # Przywracamy czystą, nieprzefiltrowaną listę buildów zanim schowamy ją do pamięci.
            if hasattr(self, 'all_builds') and self.all_builds:
                self.current_god_data.builds = self.all_builds.copy()
            self.data_cache[self.build_source] = self.current_god_data
            
        self.build_source = source
        print(f"🔄 [Controller] Silnik buildów zmieniony na: {source}")
        
        # Save config persistently
        self._save_config()

        # --- Bezpieczne odłączanie sygnałów ---
        try:
            self.overlay.home_screen.toggle.valueChanged.disconnect(self.set_build_source)
        except TypeError:
            pass
            
        try:
            self.overlay.list_screen.toggle.valueChanged.disconnect(self.set_build_source)
        except TypeError:
            pass
            
        # Aktualizacja wizualna przełączników
        self.overlay.home_screen.toggle.set_value(source, animate=False)
        self.overlay.list_screen.toggle.set_value(source, animate=False)
        
        # Ponowne podłączenie sygnałów
        self.overlay.home_screen.toggle.valueChanged.connect(self.set_build_source)
        self.overlay.list_screen.toggle.valueChanged.connect(self.set_build_source)

        # Re-fetch or use cache
        if self.data_cache.get(source):
            print(f"⚡ [Controller] Używam danych z pamięci podręcznej dla: {source}")
            self.current_god_data = self.data_cache[source]
            self.all_builds = self.current_god_data.builds.copy()
            
            self.overlay.set_status_indicator("idle")
            
            # --- NAPRAWA 2: Pełny, natywny reset z Overlayu! ---
            # Zamiast hakować wygląd ręcznie, ta metoda zresetuje 
            # zarówno grafiki, teksty, jak i same "liczniki" kliknięć wewnątrz overlayu.
            if hasattr(self.overlay, 'reset_filters'):
                self.overlay.reset_filters()
            
            if self.overlay._current_page in ["list", "detail"]:
                self.apply_filter()
        else:
            self.current_god_data = None
            self.all_builds = []

            if self.overlay._current_page in ["list", "detail"] and hasattr(self.overlay, '_current_god_name') and self.overlay._current_god_name:
                self.overlay.show_list_skeleton(self.overlay._current_god_name)
                self.start_build_fetch(self.overlay._current_god_name)

    def _save_to_cache(self, god_name, json_data):
        """Saves build data to a local JSON file, scoped by source type."""
        cache_dir = os.path.join("assets", "cache")
        os.makedirs(cache_dir, exist_ok=True)
            
        slug = god_name.lower().strip().replace(" ", "_").replace("'", "")
        
        
        filepath = os.path.join(cache_dir, f"{slug}_{self.build_source}.json")
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(f"[Cache] Zapisano dane dla: {god_name} ({self.build_source})")

    def _load_from_cache(self, god_name):
        """Loads build data from local JSON cache if available and not expired."""
        import time
        import os
        import json
        
        slug = god_name.lower().strip().replace(" ", "_").replace("'", "")
        filepath = os.path.join("assets", "cache", f"{slug}_{self.build_source}.json")
            
        if os.path.exists(filepath):
            # --- NOWOŚĆ: Sprawdzamy wiek pliku (TTL) ---
            file_age_seconds = time.time() - os.path.getmtime(filepath)
            max_age_seconds = 4 * 3600  # 4 godziny (możesz dowolnie zmienić)
            
            if file_age_seconds > max_age_seconds:
                print(f"[Cache] Dane dla {god_name} ({self.build_source}) wygasły (mają ponad 4h). Pobieram świeże z sieci.")
                return None  # Zwracamy None, wymuszając na bocie pobranie nowych danych
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Cache] Błąd odczytu cache dla {god_name}: {e}")
                
        return None
    
    def _set_autostart(self, enable: bool):
        """Adds or removes the application from Windows startup."""
        if os.name != 'nt':
            return  # Zabezpieczenie: funkcja działa tylko na Windowsie
        
        import winreg
        
        # Sprawdzamy, czy aplikacja jest skompilowana do .exe, czy uruchamiana ze skryptu .py
        if getattr(sys, 'frozen', False):
            app_path = f'"{sys.executable}"'
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Smite2KuzenBot" # Unikalna nazwa w rejestrze
        
        try:
            # Otwieramy klucz rejestru z prawami do zapisu
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                print("🚀 [System] Włączono uruchamianie aplikacji z systemem Windows.")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    print("🛑 [System] Wyłączono uruchamianie aplikacji z systemem Windows.")
                except FileNotFoundError:
                    pass # Jeśli klucza nie było, to znaczy, że już jest usunięty
                    
            winreg.CloseKey(key)
        except Exception as e:
            print(f"⚠️ [System] Błąd podczas modyfikacji autostartu: {e}")

    def on_game_started(self):
        """Called when the game process is detected."""
        print("🎮 [ProcessMonitor] Wykryto proces gry! Pokazuję nakładkę.")
        if not self.overlay.isVisible():
            # ZMIANA: Twarde 0.0! Animacja w overlay_5.py sama pobierze target_opacity i płynnie się wyłoni
            self.overlay.setWindowOpacity(0.0)
            
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()

    def on_game_stopped(self):
        """Called when the Smite 2 process has exited."""
        print("🛑 [ProcessMonitor] Brak procesu gry. Ukrywam aplikację do zasobnika.")
        if self.overlay.isVisible():
            self.overlay.hide()
            
        # Niezależnie od tego czy overlay był widoczny, wymuszamy pokazanie ikony w trayu
        if not self.tray_icon.isVisible():
            self.tray_icon.show()

    def _on_returned_to_auto_wait(self):
        """Called when the user navigates back to Auto mode."""
        last_god = getattr(self.scanner, 'last_emitted_god', None)
        if last_god:
            self.overlay.auto_wait_screen.show_choice(
                last_god,
                yes_cb=self.continue_active_session,
                no_cb=self.reset_active_session
            )
        else:
            self.overlay.auto_wait_screen.show_waiting()

    def start_auto_update(self):
        """Triggered by the UI update button. Starts downloading the new version."""
        print("🚀 Rozpoczynam pobieranie nowej wersji...")
        
        # Zapobiegamy wielokrotnemu kliknięciu
        if hasattr(self, 'update_downloader') and self.update_downloader.isRunning():
            return
            
        url = getattr(self.overlay, '_update_url', None)
        if not url: return

        self.update_downloader = UpdateDownloaderWorker(url)
        self.update_downloader.progress.connect(self._on_update_progress)
        self.update_downloader.finished.connect(self._on_update_downloaded)
        self.update_downloader.error.connect(lambda e: print(f"⚠️ [Updater] Błąd pobierania: {e}"))
        self.update_downloader.start()

    def _on_update_progress(self, percent):
        """Updates the button text with download progress."""
        if self.overlay.is_expanded:
            self.overlay.btn_update.setText(f"🚀 Pobieranie: {percent}%")
        else:
            self.overlay.btn_update.setText(f"{percent}%")

    def _on_update_downloaded(self, installer_path):
        """Launches the silent installer and shuts down the current app."""
        print(f"✅ [Updater] Pobrane! Uruchamiam instalator z: {installer_path}")
        self.overlay.btn_update.setText("🚀 Instalowanie...")
        
        # Otwiera instalator z wbudowaną dla Inno Setup flagą /SILENT 
        subprocess.Popen([installer_path, '/SILENT', '/SP-'])
        
        # Zamykamy aplikację, aby instalator mógł nadpisać pliki!
        self._exit_app()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    import signal
    import traceback 
    
    # 1. Definiujemy безопасный sys.excepthook
    def safe_excepthook(exctype, value, traceback_obj):
        err_msg = "".join(traceback.format_exception(exctype, value, traceback_obj))
        
        if issubclass(exctype, KeyboardInterrupt):
            logger.warning(f"[!] Przechwycono KeyboardInterrupt в pętli Qt. Ignorowanie и kontynuacja.")
            return
            
        # ZAPIS CRASHA DO LOGÓW Z POZIOMEM CRITICAL
        logger.critical(f"FATAL UNHANDLED EXCEPTION:\n{err_msg}")
        
        try:
            # Twój oryginalny zapis na wypadek gdyby logger zawiódł
            sys.stderr.write(f"[SafeExcepthook] Необработанное исключение:\n{err_msg}\n")
        except:
            pass

    sys.excepthook = safe_excepthook

    # 2. Ignorujemy sygnał Ctrl+C, aby zapobiec zamykaniu aplikacji (np. przy kopiowaniu tekstu)
    def sigint_handler(signum, frame):
        try:
            logger.info("[!] Przechwycono sygnał zamknięcia (Ctrl+C). Ignorowanie sygnału, aby zapobiec przypadkowemu zamknięciu aplikacji.")
            print("\n[!] Zignorowano Ctrl+C. Użyj 'X' w oknie lub zamknij proces w menedżerze zadań, aby wyłączyć aplikację.")
        except:
            pass

    signal.signal(signal.SIGINT, sigint_handler)

    controller = SmiteController()
    controller.run()