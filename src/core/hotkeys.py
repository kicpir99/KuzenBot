import keyboard
import time
from PyQt6.QtCore import QThread, pyqtSignal

class HotkeyListener(QThread):
    """Listens for global keyboard shortcuts system-wide."""
    toggle_overlay = pyqtSignal()
    request_god_change = pyqtSignal()
    next_build_requested = pyqtSignal()
    prev_build_requested = pyqtSignal()
    toggle_click_through = pyqtSignal()
    toggle_source = pyqtSignal()
    trigger_auto_search = pyqtSignal()
    toggle_size_mode = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.keybinds = {}
        self.running = True
        self._handlers = []

        self.action_to_signal = {
            "show_hide": self.toggle_overlay,
            "lock_unlock": self.toggle_click_through,
            "next_build": self.next_build_requested,
            "prev_build": self.prev_build_requested,
            "quick_auto_search": self.trigger_auto_search,
            "quick_search": self.request_god_change,
            "toggle_size": self.toggle_size_mode,
            "toggle_source": self.toggle_source,
        }

    def update_hotkeys(self, new_keybinds):
        """Updates shortcuts on the fly, removing old listeners."""
        self.keybinds = new_keybinds
        self._apply_hotkeys()

    def _apply_hotkeys(self):
        # Remove previous handlers
        for h in self._handlers:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._handlers.clear()

        for action, qt_seq_str in self.keybinds.items():
            if action in self.action_to_signal and qt_seq_str:
                kb_str = qt_seq_str.lower().replace("meta", "windows")
                try:
                    handler = keyboard.add_hotkey(kb_str, self.action_to_signal[action].emit)
                    self._handlers.append(handler)
                    from core.logger import logger
                    logger.info(f"[Hotkeys] Zarejestrowano skrót: '{kb_str}' dla '{action}'")
                except Exception as e:
                    from core.logger import logger
                    logger.error(f"[Hotkeys] BŁĄD rejestracji skrótu '{kb_str}': {e}. Czy aplikacja ma uprawnienia Administratora?")

    def run(self):
        while self.running:
            time.sleep(0.1)

    def stop(self):
        """Safely disable listener and remove hooks."""
        self.running = False
        try:
            import keyboard
            keyboard.unhook_all() # Kluczowe! Odczepiamy się od klawiatury Windowsa
        except Exception:
            pass
        self.wait()
