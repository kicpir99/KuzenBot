"""Settings Dialog — QDialog with General, Keybinds, Visuals tabs."""

import os
import json
import copy
import sys

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QKeySequence, QCursor, QIcon
from PyQt6.QtWidgets import (QApplication, QDialog, QTabWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QCheckBox, QSlider,
                             QPushButton, QWidget, QFrame, QGridLayout,
                             QDialogButtonBox, QGroupBox, QScrollArea,
                             QTextBrowser)
from core.translations import _t


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, current_config, overlay, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        # Używamy deepcopy, aby nie nadpisywać aktywnej konfiguracji w locie
        self._config = copy.deepcopy(current_config)
        self._original_config = copy.deepcopy(current_config)
        self._listening_for = None

        self.setWindowTitle("Settings")
        # ZMIANA: Zwiększamy wysokość z 400 do 460 dla lepszego komfortu wizualnego
        self.setFixedSize(480, 460)
        flags = Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QDialog {
                background: #0f172a;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
            }
            QTabWidget::pane {
                background: transparent;
                border: none;
                padding: 5px 0px;
            }
            QTabBar::tab {
                background: rgba(15,23,42,0.8);
                color: #94a3b8;
                font-size: 11px;
                font-weight: 800;
                padding: 8px 16px;
                border: 1px solid rgba(255,255,255,0.05);
                border-bottom: none;
                border-radius: 8px 8px 0 0;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: rgba(30,41,59,0.9);
                color: #f8fafc;
                border-color: rgba(59,130,246,0.3);
            }
            QLabel { color: #cbd5e1; font-size: 11px; font-weight: 600; }
            QComboBox {
                background: rgba(30,41,59,0.8);
                color: #f8fafc;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                min-height: 22px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(15,23,42,0.98);
                color: #f8fafc;
                border: 1px solid rgba(255,255,255,0.08);
                selection-background-color: rgba(59,130,246,0.3);
            }
            QCheckBox {
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 600;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.15);
                background: rgba(30,41,59,0.6);
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #3b82f6;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255,255,255,0.1);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 2px;
            }
                               
            /* STYLIZACJA PASKA PRZEWIJANIA (Zgodna z premium look aplikacji) */
            QScrollBar:vertical {
                border: none;
                background: rgba(15, 23, 42, 0.2);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(197, 160, 89, 0.3);
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(197, 160, 89, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                height: 0px;
                width: 0px;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Title bar
        title_row = QHBoxLayout()
        title = QLabel(_t("settings_title"))
        title.setStyleSheet("font-size: 14px; font-weight: 900; color: #f8fafc; letter-spacing: 1px;")
        title_row.addWidget(title)
        title_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.15);
                color: #f87171;
                border: none;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.3);
                color: #ef4444;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        main_layout.addLayout(title_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), _t("tab_general"))
        self.tabs.addTab(self._build_keybinds_tab(), _t("tab_keybinds"))
        self.tabs.addTab(self._build_visuals_tab(), _t("tab_visuals"))
        
        self.tab_about = QWidget()
        about_layout = QVBoxLayout(self.tab_about)
        about_layout.setContentsMargins(20, 20, 20, 20)
        about_layout.setSpacing(15)
        
        # 2. Nagłówek aplikacji (Wersja i Tytuł)
        app_title = QLabel("KuzenBot - Smite 2 Overlay")
        app_title.setStyleSheet("font-size: 18px; font-weight: 900; color: #C5A059;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(app_title)

        app_version = QLabel(_t("app_version_text").format(version="1.0.0 Alpha"))
        app_version.setStyleSheet("font-size: 11px; color: #94a3b8;")
        app_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(app_version)

        # Zmiana 2: Tłumaczony tekst kontaktu używając f-stringów i _t()
        contact_label = QLabel(
            f"<div style='margin-top: 10px;'>"
            f"<span style='color: #cbd5e1; font-weight: bold;'>{_t('support_title')}:</span><br>"
            f"<span style='color: #94a3b8;'>Discord:</span> lukaszkozaczekv.2.0<br>"
            f"<span style='color: #94a3b8;'>E-mail:</span> <a href='mailto:kicpir99@wp.pl' style='color: #3b82f6; text-decoration: none;'>kicpir99@wp.pl</a>"
            f"</div>"
        )
        contact_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contact_label.setTextFormat(Qt.TextFormat.RichText)
        contact_label.setOpenExternalLinks(True)
        contact_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        about_layout.addWidget(contact_label)
        # ------------------------------
        
        # 3. Tytuł naszej "Umowy Prawnej"
        eula_title = QLabel(_t("eula_title"))
        eula_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #f8fafc; margin-top: 10px;")
        eula_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(eula_title)
        
        # 4. Tworzymy pole tekstowe do czytania (QTextBrowser)
        self.eula_box = QTextBrowser()
        self.eula_box.setOpenExternalLinks(True)
        self.eula_box.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                padding: 10px;
                color: #cbd5e1;
                font-size: 11px;
                line-height: 1.5;
            }
        """)
        
        # 5. Generujemy treść EULA
        funny_rules = _t("eula_rules")
        eula_content = ""
        for i, rule in enumerate(funny_rules, 1):
            clean_rule = rule.replace('\n', ' ')
            eula_content += f"<b>§ {i}.</b> {clean_rule}<br><br>"
            
        # Dodajemy stopkę
        eula_content += "<hr><br><i>By continuing to use this application, you implicitly agree to all the ridiculous terms stated above. Have fun!</i>"

        self.eula_box.setHtml(eula_content)
        about_layout.addWidget(self.eula_box)
        
        # 6. Dodajemy zakładkę do głównego widżetu
        self.tabs.addTab(self.tab_about, _t("tab_about"))
        
        main_layout.addWidget(self.tabs)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton(_t("btn_save"))
        ok_btn.setFixedSize(80, 30)
        ok_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        main_layout.addLayout(btn_row)

        # Aplikujemy łatkę zabezpieczającą scrollowanie
        self._fix_scrolling()

    def _fix_scrolling(self):
        """Finds all combo boxes and sliders to apply mouse wheel blocking."""
        for widget in self.findChildren(QComboBox) + self.findChildren(QSlider):
            self._apply_scroll_fix(widget)

    def _apply_scroll_fix(self, widget):
        """Overrides mouse wheel event — value changes only when focused."""
        original_wheel_event = widget.wheelEvent
        
        def custom_wheel_event(event):
            # Jeśli element został wcześniej kliknięty i ma focus - pozwól na scrollowanie wartości
            if widget.hasFocus():
                original_wheel_event(event)
            # W przeciwnym razie zignoruj scroll, pozwalając oknu głównemu (QScrollArea) na swobodne przewijanie
            else:
                event.ignore()
                
        # Podmieniamy oryginalną metodę na naszą bezpieczną
        widget.wheelEvent = custom_wheel_event
        # Odbieramy elementom "WheelFocus", wymuszając kliknięcie (StrongFocus) do przejęcia kontroli
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _wrap_in_scroll_area(self, content_widget):
        """Helper wrapping a tab in a transparent scrollable container."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content_widget.setStyleSheet("background: transparent;")
        scroll.setWidget(content_widget)
        return scroll

    # ── General tab ──────────────────────────────────────────────
    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 5, 5, 5)
        layout.setSpacing(12)

        # LANGUAGE SELECTOR
        lang_group = QGroupBox(_t("language"))
        lang_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        lang_layout = QVBoxLayout(lang_group)
        self.lang_cb = QComboBox()
        if hasattr(self, 'lang_cb'):
            self.lang_cb.currentIndexChanged.connect(self._show_restart_notice)
        
        # Klucze techniczne i ich wyświetlane nazwy
        self.lang_options = [
            ("en", "English (EN)"),
            ("pl", "Polski (PL)"),
            ("fr", "Français (FR)"),
            ("de", "Deutsch (DE)"),
            ("es", "Español (ES)"),
            ("ru", "Русский (RU)"),
            ("uk", "Українська (UK)"),
            ("pt", "Português (PT)"),
            ("zh", "中文 (ZH)")
        ]
        
        for code, name in self.lang_options:
            self.lang_cb.addItem(name, code)
            
        # Ustaw aktywny język
        current_lang = self._config.get("language", "en")
        idx = self.lang_cb.findData(current_lang)
        if idx >= 0:
            self.lang_cb.setCurrentIndex(idx)
            
        self.lang_cb.currentIndexChanged.connect(self._on_lang_changed)
        lang_layout.addWidget(self.lang_cb)
        layout.addWidget(lang_group)

        # Build Source
        src_group = QGroupBox(_t("build_source"))
        src_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; padding: 0 6px;
            }
        """)
        src_layout = QVBoxLayout(src_group)
        self.build_source_cb = QComboBox()
        self.build_source_cb.addItems([_t("comm_builds"), _t("stat_builds"), _t("last_used")])
        val = self._config.get("build_source", "builds")
        if val == "stats":
            self.build_source_cb.setCurrentIndex(1)
        elif val == "last_used":
            self.build_source_cb.setCurrentIndex(2)
        else:
            self.build_source_cb.setCurrentIndex(0)
        self.build_source_cb.currentIndexChanged.connect(self._on_source_changed)
        src_layout.addWidget(self.build_source_cb)
        layout.addWidget(src_group)

        # Close behavior
        close_group = QGroupBox(_t("close_behavior"))
        close_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        close_layout = QVBoxLayout(close_group)
        x_row = QHBoxLayout()
        x_row.addWidget(QLabel(_t("when_clicking_x")))
        self.close_action_cb = QComboBox()
        self.close_action_cb.addItems([_t("close_app"), _t("min_tray")])
        self.close_action_cb.setCurrentIndex(1 if self._config.get("close_to_tray", False) else 0)
        self.close_action_cb.currentIndexChanged.connect(self._on_close_action_changed)
        x_row.addWidget(self.close_action_cb)
        x_row.addStretch()
        close_layout.addLayout(x_row)
        layout.addWidget(close_group)

        # --- 2. NOWA GRUPA: Ustawienia Systemowe ---
        system_group = QGroupBox(_t("system_settings"))
        system_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        system_layout = QVBoxLayout(system_group)
        
        # Tworzymy czysty checkbox - globalny styl z góry pliku zajmie się resztą!
        self.auto_start_cb = QCheckBox(_t("auto_start")) 
        self.auto_start_cb.setMinimumHeight(22)
        self.auto_start_cb.setChecked(self._config.get("auto_start", False))
        self.auto_start_cb.toggled.connect(self._on_auto_start_changed)
        
        system_layout.addWidget(self.auto_start_cb)
        layout.addWidget(system_group)

        # Reszta układu
        layout.addStretch()
        
        # === POPRAWNY BLOK KOMUNIKATU O RESTARCIE ===
        self.restart_notice = QLabel(_t("restart_notice"))
        self.restart_notice.setStyleSheet("color: #cbd5e1; font-size: 11px; font-style: italic; font-weight: bold; margin-top: 5px;")
        self.restart_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.restart_notice.hide()
        layout.addWidget(self.restart_notice)

        return self._wrap_in_scroll_area(tab)

    # ── Keybinds tab ─────────────────────────────────────────────
    def _build_keybinds_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 5, 10, 5) # Zapas z prawej strony na pasek przewijania
        layout.setSpacing(10)

        info = QLabel(_t("press_key"))
        info.setStyleSheet("color: #64748b; font-size: 9px; font-style: italic;")
        layout.addWidget(info)

        # Keybind entries
        self._keybind_widgets = {}
        keybinds = self._config.get("keybinds", {})
        actions = [
            ("show_hide", _t("key_show_hide")),
            ("lock_unlock", _t("key_lock")),
            ("next_build", _t("key_next")),
            ("prev_build", _t("key_prev")),
            ("quick_search", _t("key_search")),
            ("toggle_source", _t("key_toggle")),
        ]
        for action_key, action_label in actions:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)

            name_lbl = QLabel(action_label)
            name_lbl.setFixedWidth(160)
            rl.addWidget(name_lbl)

            seq = keybinds.get(action_key, self._default_keybind(action_key))
            seq_label = QLabel(seq)
            seq_label.setStyleSheet("""
                background: rgba(30,41,59,0.8);
                color: #f8fafc;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-family: monospace;
                min-width: 100px;
            """)
            rl.addWidget(seq_label)

            change_btn = QPushButton(_t("btn_change"))
            # ZMIANA: Zwiększamy wysokość z 26 na 28 i zerujemy wewnętrzny padding, chroniąc przed ucinaniem czcionki
            change_btn.setFixedSize(70, 28)
            change_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            change_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(59,130,246,0.15);
                    color: #60a5fa;
                    border: 1px solid rgba(59,130,246,0.2);
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 800;
                    padding: 0px;
                }
                QPushButton:hover { background: rgba(59,130,246,0.25); }
            """)
            change_btn.clicked.connect(lambda checked, k=action_key, lbl=seq_label: self._start_listening(k, lbl))
            rl.addWidget(change_btn)
            rl.addStretch()

            self._keybind_widgets[action_key] = {"label": seq_label, "current": seq}
            layout.addWidget(row)

        # Reset keybinds button
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_btn = QPushButton(_t("btn_reset_keys"))
        reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.1);
                color: #f87171;
                border: 1px solid rgba(239,68,68,0.2);
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 5px 14px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.2); }
        """)
        reset_btn.clicked.connect(self._reset_keybinds)
        reset_row.addWidget(reset_btn)
        layout.addLayout(reset_row)

        # Warning label for duplicate shortcuts
        self._kb_warning = QLabel("")
        self._kb_warning.setStyleSheet("color: #f87171; font-size: 10px; font-weight: 600; padding: 2px 0;")
        self._kb_warning.hide()
        layout.addWidget(self._kb_warning)

        layout.addStretch()
        # ZMIANA: Zwracamy zakładkę opakowaną w ScrollArea
        return self._wrap_in_scroll_area(tab)

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

    _key_capture_installed = False

    def _start_listening(self, action_key, label_widget):
        if self._listening_for:
            return
        self._listening_for = action_key
        label_widget.setText("Press a key...")
        label_widget.setStyleSheet("""
            background: rgba(59,130,246,0.2);
            color: #f8fafc;
            border: 1px solid #3b82f6;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-family: monospace;
            min-width: 100px;
        """)
        self._keybind_target = (action_key, label_widget)
        # Global event filter to capture keys regardless of focus
        if not self._key_capture_installed:
            QApplication.instance().installEventFilter(self)
            self._key_capture_installed = True

    def _get_key_sequence(self, key, mods):
        combined = key
        if mods & Qt.KeyboardModifier.ControlModifier: combined |= Qt.KeyboardModifier.ControlModifier.value
        if mods & Qt.KeyboardModifier.ShiftModifier:   combined |= Qt.KeyboardModifier.ShiftModifier.value
        if mods & Qt.KeyboardModifier.AltModifier:     combined |= Qt.KeyboardModifier.AltModifier.value
        if mods & Qt.KeyboardModifier.MetaModifier:    combined |= Qt.KeyboardModifier.MetaModifier.value
        return QKeySequence(combined).toString(QKeySequence.SequenceFormat.PortableText)

    def eventFilter(self, obj, event):
        if self._listening_for and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                return True
            seq = self._get_key_sequence(key, event.modifiers())
            if seq:
                self._finish_listening(seq)
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if self._listening_for:
            key = event.key()
            if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                return
            seq = self._get_key_sequence(key, event.modifiers())
            if seq:
                self._finish_listening(seq)
            return
        super().keyPressEvent(event)

    def _finish_listening(self, seq):
        action_key, label_widget = self._keybind_target

        # Sprawdź czy skrót nie jest już używany przez inną akcję
        for other_key, data in self._keybind_widgets.items():
            if other_key != action_key and data["current"] == seq:
                self._kb_warning.setText(_t("shortcut_assigned").format(seq=seq, other_key=other_key))
                self._kb_warning.show()
                # Wróć do poprzedniej wartości tej akcji
                prev = self._keybind_widgets[action_key]["current"]
                label_widget.setText(prev)
                label_widget.setStyleSheet("""
                    background: rgba(30,41,59,0.8);
                    color: #f8fafc;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-family: monospace;
                    min-width: 100px;
                """)
                self._listening_for = None
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(3000, self._kb_warning.hide)
                return

        self._kb_warning.hide()
        self._listening_for = None
        label_widget.setText(seq)
        label_widget.setStyleSheet("""
            background: rgba(30,41,59,0.8);
            color: #f8fafc;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-family: monospace;
            min-width: 100px;
        """)
        self._keybind_widgets[action_key]["current"] = seq
        self._config.setdefault("keybinds", {})[action_key] = seq

    def _reset_keybinds(self):
        for action_key, data in self._keybind_widgets.items():
            default = self._default_keybind(action_key)
            data["current"] = default
            data["label"].setText(default)
            self._config.setdefault("keybinds", {})[action_key] = default

    # ── Visuals tab ──────────────────────────────────────────────
    def _build_visuals_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        theme_group = QGroupBox(_t("theme_colors"))
        theme_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 4px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_cb = QComboBox()
        # Wyświetlane nazwy dla użytkownika oraz ukryte klucze techniczne dla słownika THEMES
        self.theme_cb.addItem("🌟 Divine Gold", "gold")
        self.theme_cb.addItem("🌋 Ruby Rage", "ruby")
        self.theme_cb.addItem("⚡ Sapphire Blizzard", "blizzard")
        self.theme_cb.addItem("🌿 Emerald Poison", "emerald")
        self.theme_cb.addItem("🔮 Shadow Void", "void")
        self.theme_cb.addItem("👾 Cyber-Night", "cyber")
        self.theme_cb.addItem("☢️ Toxic Waste", "toxic")
        self.theme_cb.addItem("🩸 Abyss Alarm", "abyss")
        
        # Ustawiamy aktualny indeks na podstawie configu
        current_theme = self._config.get("theme", "gold")
        idx = self.theme_cb.findData(current_theme)
        if idx >= 0:
            self.theme_cb.setCurrentIndex(idx)
            
        self.theme_cb.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_cb)
        layout.addWidget(theme_group)
        font_group = QGroupBox(_t("font_style"))
        font_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 4px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        font_layout = QVBoxLayout(font_group)
        self.font_cb = QComboBox()
        self.font_cb.addItem(_t("font_standard"), "standard")
        self.font_cb.addItem(_t("font_terminal"), "terminal")
        self.font_cb.addItem(_t("font_heavy"), "heavy")
        self.font_cb.addItem(_t("font_gothic"), "gothic")
        
        current_font = self._config.get("font_style", "standard")
        idx = self.font_cb.findData(current_font)
        if idx >= 0:
            self.font_cb.setCurrentIndex(idx)
            
        self.font_cb.currentIndexChanged.connect(self._on_visuals_changed)
        font_layout.addWidget(self.font_cb)
        layout.addWidget(font_group)
        layout.setContentsMargins(0, 5, 10, 5) # Zapas z prawej strony na pasek przewijania
        layout.setSpacing(12)

        # Opacity
        op_group = QGroupBox(_t("opacity"))
        op_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        # Potrójna przezroczystość (Split Opacity System)
        op_group = QGroupBox(_t("adv_opacity"))
        op_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        op_layout = QVBoxLayout(op_group)
        op_layout.setSpacing(8)

        # 1. Cała aplikacja
        app_row = QHBoxLayout()
        app_row.addWidget(QLabel(_t("op_app")))
        self.opacity_app_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_app_slider.setRange(10, 100)
        app_val = int(self._config.get("opacity_app", 1.0) * 100)
        self.opacity_app_slider.setValue(app_val)
        self.opacity_app_label = QLabel(f"{app_val}%")
        self.opacity_app_label.setFixedWidth(40)
        self.opacity_app_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.opacity_app_slider.valueChanged.connect(
            lambda val: self._on_opacity_slider_changed("opacity_app", val, self.opacity_app_label)
        )
        app_row.addWidget(self.opacity_app_slider)
        app_row.addWidget(self.opacity_app_label)
        op_layout.addLayout(app_row)

        # 2. Samo tło i napisy
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel(_t("op_bg")))
        self.opacity_bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_bg_slider.setRange(10, 100)
        bg_val = int(self._config.get("opacity_bg_text", 1.0) * 100)
        self.opacity_bg_slider.setValue(bg_val)
        self.opacity_bg_label = QLabel(f"{bg_val}%")
        self.opacity_bg_label.setFixedWidth(40)
        self.opacity_bg_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.opacity_bg_slider.valueChanged.connect(
            lambda val: self._on_opacity_slider_changed("opacity_bg_text", val, self.opacity_bg_label)
        )
        bg_row.addWidget(self.opacity_bg_slider)
        bg_row.addWidget(self.opacity_bg_label)
        op_layout.addLayout(bg_row)

        # 3. Ikony przedmiotów
        items_row = QHBoxLayout()
        items_row.addWidget(QLabel(_t("op_items")))
        self.opacity_items_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_items_slider.setRange(10, 100)
        items_val = int(self._config.get("opacity_items", 1.0) * 100)
        self.opacity_items_slider.setValue(items_val)
        self.opacity_items_label = QLabel(f"{items_val}%")
        self.opacity_items_label.setFixedWidth(40)
        self.opacity_items_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.opacity_items_slider.valueChanged.connect(
            lambda val: self._on_opacity_slider_changed("opacity_items", val, self.opacity_items_label)
        )
        items_row.addWidget(self.opacity_items_slider)
        items_row.addWidget(self.opacity_items_label)
        op_layout.addLayout(items_row)

        layout.addWidget(op_group)

        # Always on Top
        top_group = QGroupBox(_t("win_behavior"))
        top_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        top_layout = QVBoxLayout(top_group)
        self.always_top_cb = QCheckBox(_t("always_top"))
        self.always_top_cb.setChecked(self._config.get("always_on_top", True))
        self.always_top_cb.toggled.connect(self._on_always_top_changed)
        top_layout.addWidget(self.always_top_cb)
        layout.addWidget(top_group)

        # Monitor selection
        mon_group = QGroupBox(_t("display_mon"))
        mon_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        mon_layout = QVBoxLayout(mon_group)
        mon_row = QHBoxLayout()
        mon_row.addWidget(QLabel(_t("start_mon")))
        self.monitor_cb = QComboBox()
        self._populate_monitors()
        mon_row.addWidget(self.monitor_cb)
        mon_row.addStretch()
        mon_layout.addLayout(mon_row)
        layout.addWidget(mon_group)

        # Customizacja trybu Mini (Ustawienia ultra-minimalizmu)
        mini_group = QGroupBox(_t("mini_header"))
        mini_group.setStyleSheet("""
            QGroupBox {
                color: #94a3b8; font-size: 10px; font-weight: 800;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 14px 10px 8px; margin-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)
        mini_layout = QVBoxLayout(mini_group)
        mini_layout.setSpacing(8) # Zwiększyłem lekko spacing dla lepszego ułożenia ikon

        self.hide_source_cb = QCheckBox(_t("hide_source"))
        self.hide_source_cb.setIcon(self._colorize_icon(resource_path("assets", "community_mask.svg"), "#94a3b8"))
        self.hide_source_cb.setIconSize(QSize(16, 16))
        self.hide_source_cb.setChecked(self._config.get("hide_mini_source", False))
        self.hide_source_cb.toggled.connect(lambda checked: self._on_mini_hide_changed("hide_mini_source", checked))

        self.hide_role_cb = QCheckBox(_t("hide_role"))
        self.hide_role_cb.setIcon(self._colorize_icon(resource_path("assets", "role_any_mask.svg"), "#94a3b8"))
        self.hide_role_cb.setIconSize(QSize(16, 16))
        self.hide_role_cb.setChecked(self._config.get("hide_mini_role", False))
        self.hide_role_cb.toggled.connect(lambda checked: self._on_mini_hide_changed("hide_mini_role", checked))

        self.hide_aspect_cb = QCheckBox(_t("hide_aspect"))
        self.hide_aspect_cb.setIcon(self._colorize_icon(resource_path("assets", "aspect_mask.png"), "#94a3b8"))
        self.hide_aspect_cb.setIconSize(QSize(16, 16))
        self.hide_aspect_cb.setChecked(self._config.get("hide_mini_aspect", False))
        self.hide_aspect_cb.toggled.connect(lambda checked: self._on_mini_hide_changed("hide_mini_aspect", checked))

        self.hide_toggle_cb = QCheckBox(_t("hide_toggle"))
        self.hide_toggle_cb.setIcon(self._colorize_icon(resource_path("assets", "collapse_mask.svg"), "#94a3b8"))
        self.hide_toggle_cb.setIconSize(QSize(16, 16))
        self.hide_toggle_cb.setChecked(self._config.get("hide_mini_toggle", False))
        self.hide_toggle_cb.toggled.connect(lambda checked: self._on_mini_hide_changed("hide_mini_toggle", checked))

        self.hide_lock_cb = QCheckBox(_t("hide_lock"))
        self.hide_lock_cb.setIcon(self._colorize_icon(resource_path("assets", "unlock_mask.svg"), "#94a3b8"))
        self.hide_lock_cb.setIconSize(QSize(16, 16))
        self.hide_lock_cb.setChecked(self._config.get("hide_mini_lock", False))
        self.hide_lock_cb.toggled.connect(lambda checked: self._on_mini_hide_changed("hide_mini_lock", checked))

        mini_layout.addWidget(self.hide_source_cb)
        mini_layout.addWidget(self.hide_role_cb)
        mini_layout.addWidget(self.hide_aspect_cb)
        mini_layout.addWidget(self.hide_toggle_cb)
        mini_layout.addWidget(self.hide_lock_cb)
        layout.addWidget(mini_group)

        # Reset visuals
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_btn = QPushButton(_t("btn_reset_vis"))
        reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.1);
                color: #f87171;
                border: 1px solid rgba(239,68,68,0.2);
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 6px 14px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.2); }
        """)
        reset_btn.clicked.connect(self._reset_visuals)
        reset_row.addWidget(reset_btn)
        layout.addLayout(reset_row)

        layout.addStretch()
        # ZMIANA: Zwracamy zakładkę opakowaną w ScrollArea
        return self._wrap_in_scroll_area(tab)

    def _populate_monitors(self):
        from PyQt6.QtGui import QGuiApplication
        screens = QGuiApplication.screens()
        selected = self._config.get("monitor_id", 0)
        for i, screen in enumerate(screens):
            name = screen.name() or f"Monitor {i+1}"
            geo = screen.geometry()
            self.monitor_cb.addItem(f"{name} ({geo.width()}x{geo.height()})", i)
        if 0 <= selected < self.monitor_cb.count():
            self.monitor_cb.setCurrentIndex(selected)

    # ── Callbacks ────────────────────────────────────────────────
    def _on_opacity_changed(self, val):
        pct = val / 100.0
        self.opacity_label.setText(f"{val}%")
        self._config["opacity"] = pct
        if self.overlay:
            self.overlay.set_opacity(pct)

    def _on_always_top_changed(self, checked):
        self._config["always_on_top"] = checked
        if self.overlay:
            self.overlay.set_always_on_top(checked)

    def _on_source_changed(self, idx):
        mapping = {0: "builds", 1: "stats", 2: "last_used"}
        self._config["build_source"] = mapping.get(idx, "builds")

    def _on_close_action_changed(self, idx):
        self._config["close_to_tray"] = (idx == 1)

    def _on_auto_start_changed(self, checked):
        self._config["auto_start"] = checked

    def _on_mini_hide_changed(self, key, checked):
        """Updates configuration and emits a background refresh signal."""
        self._config[key] = checked
        if self.overlay:
            self.overlay._config = self._config
            if hasattr(self.overlay, "update_mini_buttons_visibility"):
                self.overlay.update_mini_buttons_visibility()

    def _on_ok(self):
        self.settings_changed.emit(self._config)
        self._remove_global_filter()
        self.accept()

    def reject(self):
        self._remove_global_filter()
        
        # Jeśli użytkownik zamknął okno iksem, cofamy wszystkie zmiany z podglądu na żywo
        if self.overlay:
            # Przywracamy oryginalną konfigurację do pamięci podręcznej nakładki
            self.overlay._config = copy.deepcopy(self._original_config)
            
            # 1. Cofnięcie zmian językowych
            from core.translations import Translator
            orig_lang = self._original_config.get("language", "en")
            Translator.set_language(orig_lang)
            self.overlay.retranslate_ui()
            
            # 2. Cofnięcie zmian motywu i stylu czcionki
            from ui.styles import get_stylesheet
            orig_theme = self._original_config.get("theme", "gold")
            orig_font = self._original_config.get("font_style", "standard")
            self.overlay.setStyleSheet(get_stylesheet(orig_theme, orig_font))
            
            # --- DODAJEMY TEN BLOK: Cofnięcie przełączników i logo ---
            if hasattr(self.overlay, "home_screen") and hasattr(self.overlay.home_screen, "toggle"):
                self.overlay.home_screen.toggle.set_theme(orig_theme)
            if hasattr(self.overlay, "list_screen") and hasattr(self.overlay.list_screen, "toggle"):
                self.overlay.list_screen.toggle.set_theme(orig_theme)
            if hasattr(self.overlay, "update_logo"):
                self.overlay.update_logo()
            # ---------------------------------------------------------
            
            # 3. Cofnięcie potrójnej przezroczystości
            if hasattr(self.overlay, "apply_opacities"):
                self.overlay.apply_opacities()
                
            # 4. Cofnięcie widoczności ukrytych przycisków w trybie Mini
            if hasattr(self.overlay, "update_mini_buttons_visibility"):
                self.overlay.update_mini_buttons_visibility()
                
        # Uruchamiamy standardowe odrzucenie zmian w oknie Qt
        super().reject()

    def _remove_global_filter(self):
        if self._key_capture_installed:
            QApplication.instance().removeEventFilter(self)
            self._key_capture_installed = False

    def _on_opacity_slider_changed(self, key, val, label_widget):
        """Unified handler for all three opacity sliders."""
        pct = val / 100.0
        label_widget.setText(f"{val}%")
        self._config[key] = pct
        if self.overlay:
            self.overlay._config = self._config
            if hasattr(self.overlay, "apply_opacities"):
                self.overlay.apply_opacities()

    def _reset_visuals(self):
        self._config["theme"] = "gold"
        self._config["font_style"] = "standard"
        self.font_cb.setCurrentIndex(0)
        self._config["opacity_app"] = 1.0
        self._config["opacity_app"] = 1.0
        self._config["opacity_bg_text"] = 1.0
        self._config["opacity_items"] = 1.0
        self._config["opacity"] = 1.0
        self._config["always_on_top"] = True
        self._config["monitor_id"] = 0
        self._config["hide_mini_source"] = False
        self._config["hide_mini_role"] = False
        self._config["hide_mini_aspect"] = False
        self._config["hide_mini_toggle"] = False
        self._config["hide_mini_lock"] = False
        
        self.opacity_app_slider.setValue(100)
        self.opacity_bg_slider.setValue(100)
        self.opacity_items_slider.setValue(100)

        # Reset indeksu ComboBoxa motywu na pozycję 0 (Gold)
        self.theme_cb.setCurrentIndex(0)
        
        self.opacity_app_slider.setValue(100)
        
        if self.overlay and hasattr(self.overlay, "apply_opacities"):
            self.overlay.apply_opacities()
        self.always_top_cb.setChecked(True)
        if self.monitor_cb.count() > 0:
            self.monitor_cb.setCurrentIndex(0)
            
        self.hide_source_cb.setChecked(False)
        self.hide_role_cb.setChecked(False)
        self.hide_aspect_cb.setChecked(False)
        self.hide_toggle_cb.setChecked(False)
        self.hide_lock_cb.setChecked(False)

        if self.overlay:
            self.overlay.set_opacity(1.0)
            self.overlay.set_always_on_top(True)

    def get_config(self):
        return dict(self._config)

    # ============================================================ WINDOW DRAGGING
    _drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            event.accept()

    def _on_theme_changed(self, idx):
        self._config["theme"] = self.theme_cb.itemData(idx)
        self._update_overlay_stylesheet()

    def _on_visuals_changed(self, idx):
        self._config["font_style"] = self.font_cb.itemData(idx)
        self._update_overlay_stylesheet()

    def _update_overlay_stylesheet(self):
        if self.overlay:
            # === DODAJ TĘ LINIJKĘ: Wymuszamy przekazanie nowej konfiguracji do overlay'a ===
            self.overlay._config = self._config
            
            from ui.styles import get_stylesheet
            theme_key = self._config.get("theme", "gold")
            font_key = self._config.get("font_style", "standard")
            self.overlay.setStyleSheet(get_stylesheet(theme_key, font_key))
            if hasattr(self.overlay, "apply_opacities"):
                self.overlay.apply_opacities()
                
            # --- DODAJ TEN FRAGMENT, ABY ZMIENIAĆ KOLOR PRZEŁĄCZNIKÓW ---
            if hasattr(self.overlay, "home_screen") and hasattr(self.overlay.home_screen, "toggle"):
                self.overlay.home_screen.toggle.set_theme(theme_key)
            if hasattr(self.overlay, "list_screen") and hasattr(self.overlay.list_screen, "toggle"):
                self.overlay.list_screen.toggle.set_theme(theme_key)
                
            # === ODŚWIEŻENIE LOGO ===
            if hasattr(self.overlay, "update_logo"):
                self.overlay.update_logo()

    def _on_lang_changed(self, idx):
        lang_code = self.lang_cb.itemData(idx)
        self._config["language"] = lang_code
        # Ustawiamy od razu w silniku
        from core.translations import Translator
        Translator.set_language(lang_code)
        if self.overlay and hasattr(self.overlay, "retranslate_ui"):
            self.overlay.retranslate_ui()

    def _show_restart_notice(self):
        """Shows a message informing about required application restart."""
        if hasattr(self, 'restart_notice'):
            self.restart_notice.show()

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