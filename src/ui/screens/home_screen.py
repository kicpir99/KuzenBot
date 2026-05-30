"""Home Screen — mode selection (Auto / Manual)."""

import os, sys
import random

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QPushButton, QSizePolicy)
from core.translations import _t, _t_random, TRANSLATIONS, Translator

class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class HomeScreen(QWidget):
    """Ekran startowy z dwoma kafelkami wyboru trybu."""

    auto_mode_selected = pyqtSignal()
    manual_mode_selected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        lang = Translator._lang if hasattr(Translator, '_lang') else "pl"
        
        # Pobieramy słownik dla tego języka
        data = TRANSLATIONS.get(lang, TRANSLATIONS["pl"])
        
        # Łączymy obie listy z pliku translations.py
        all_texts = data.get("welcome_subtitle", []) + data.get("eula_rules", [])
        
        # Losujemy
        self.current_splash_text = random.choice(all_texts) if all_texts else "KuzenBot Ready"
        
        self._build_ui()

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)
        self._root.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Welcome section (expanded only) ---
        self.welcome_sec = QWidget()
        wl = QVBoxLayout(self.welcome_sec)
        wl.setContentsMargins(0, 40, 0, 20)
        wl.setSpacing(5)
        self.welcome_title_lbl = QLabel()
        self.welcome_title_lbl.setObjectName("welcome_title")
        self.welcome_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self.welcome_title_lbl)

        self.welcome_sub_lbl = QLabel()
        self.welcome_sub_lbl.setObjectName("welcome_subtitle")
        self.welcome_sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_sub_lbl.setWordWrap(True)                   # Kluczowe: włącza zawijanie
        self.welcome_sub_lbl.setSizePolicy(QSizePolicy.Policy(5), QSizePolicy.Policy(4))
        wl.addWidget(self.welcome_sub_lbl)
        self._root.addWidget(self.welcome_sec)

        # --- Cards container (layout swaps between V and H) ---
        self.cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self.cards_container)
        self._cards_layout.setContentsMargins(30, 0, 30, 0)
        self._cards_layout.setSpacing(20)

        self.auto_card = self._make_card(
            "🤖", _t("auto_mode"), _t("auto_desc"), self.auto_mode_selected.emit
        )
        self.manual_card = self._make_card(
            "🔍", _t("manual_mode"), _t("manual_desc"), self.manual_mode_selected.emit
        )

        self._cards_layout.addWidget(self.auto_card)
        self._cards_layout.addWidget(self.manual_card)
        self._root.addWidget(self.cards_container)
        
        # Initial state
        self._update_card_text(self.auto_card, "🤖", _t("auto_mode"), _t("auto_desc"), False)
        self._update_card_text(self.manual_card, "🔍", _t("manual_mode"), _t("manual_desc"), False)

        # --- Toggle Section (Engine Selector) ---
        self.toggle_sec = QWidget()
        tl = QHBoxLayout(self.toggle_sec)
        tl.setContentsMargins(0, 30, 0, 10)
        tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from ui.components.segmented_toggle import SegmentedToggle
        self.toggle = SegmentedToggle(self, size_mode="standard")
        tl.addWidget(self.toggle)
        self._root.addWidget(self.toggle_sec)
        self.retranslate_ui()
        

    # --------------------------------------------------------- card factory
    def _make_card(self, icon, title, desc, callback):
        card = ClickableFrame()
        card.setObjectName("mode_card")
        card.setFixedHeight(150)
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Info button (visible only in mini)
        info = QLabel("ⓘ", card)
        info.setObjectName("mode_info_btn")
        info.setFixedSize(20, 20)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setProperty("info_text", desc)
        info.setCursor(QCursor(Qt.CursorShape.WhatsThisCursor))
        info.hide() # Hide by default
        card.info_btn = info # Keep ref for positioning
 
        card.clicked.connect(callback)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("mode_icon_lbl")
        # Tu definiujemy ścieżkę do ikony na podstawie emoji (możesz dopasować nazwy plików!)
        icon_filename = "auto_icon.png" if icon == "🤖" else "manual_icon.png"
        icon_path = resource_path("assets", icon_filename)
        
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText(icon) # Fallback do emoji, jeśli pliku nie ma
            
        lay.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(5)
        t_lbl = QLabel(title)
        t_lbl.setObjectName("mode_title_lbl")
        d_lbl = QLabel(desc)
        d_lbl.setObjectName("mode_desc_lbl")
        d_lbl.setWordWrap(True)
        text_col.addStretch() # Centrowanie pionowe: stretch na górze
        text_col.addWidget(t_lbl)
        text_col.addWidget(d_lbl)
        text_col.addStretch() # Centrowanie pionowe: stretch na dole
        lay.addLayout(text_col, 1)
        return card

    # ------------------------------------------------------- expanded / mini
    def _update_card_text(self, card, icon, title, desc, is_mini):
        """Updates the text and layout inside a tile."""
        icon_lbl = card.findChild(QLabel, "mode_icon_lbl")
        title_lbl = card.findChild(QLabel, "mode_title_lbl")
        desc_lbl = card.findChild(QLabel, "mode_desc_lbl")
        
        if icon_lbl:
            icon_filename = "auto_icon.png" if icon == "🤖" else "manual_icon.png"
            icon_path = resource_path("assets", icon_filename)
            
            if os.path.exists(icon_path):
                # Skalujemy inaczej dla trybu mini i expanded
                size = 30 if is_mini else 60
                pix = QPixmap(icon_path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_lbl.setPixmap(pix)
                icon_lbl.setText("") # Czyścimy tekst, by nie nakładał się na obrazek
            else:
                icon_lbl.setText(icon)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_mini:
                icon_lbl.setFixedSize(30, 30)
                icon_lbl.setStyleSheet("font-size: 15px; background: rgba(197, 160, 89, 0.15); border-radius: 8px; padding: 0px; margin: 0px;")
            else:
                icon_lbl.setMinimumSize(0, 0)
                icon_lbl.setMaximumSize(16777215, 16777215)
                icon_lbl.setFixedSize(80, 80)
                icon_lbl.setStyleSheet("font-size: 42px; background: rgba(197, 160, 89, 0.1); border-radius: 16px;")
        
        if title_lbl:
            title_lbl.setText(title)
            title_lbl.setStyleSheet(f"font-size: {'9px' if is_mini else '18px'}; font-weight: 800;")
            
            # --- ZMIENIONA LINIJKA: Ustawiamy AlignCenter dla trybu mini ---
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if is_mini else Qt.AlignmentFlag.AlignLeft)
            
            title_lbl.setWordWrap(True)

        if desc_lbl:
            desc_lbl.setText(desc)
            desc_lbl.setVisible(not is_mini)

        if hasattr(card, 'info_btn'):
            card.info_btn.setProperty("info_text", desc)

        # Zainstaluj filtr na info_btn...
        win = self.window()
        if win:
            card.info_btn.installEventFilter(win)

        # Zmiana kierunku layoutu wewnątrz karty
        lay = card.layout()
        if lay:
            if is_mini:
                lay.setDirection(QHBoxLayout.Direction.LeftToRight)
                # Zmniejszyliśmy marginesy i odstęp (spacing z 6 na 4), by odzyskać cenne piksele
                lay.setContentsMargins(6, 4, 18, 4)
                lay.setSpacing(4)
                lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                lay.setDirection(QHBoxLayout.Direction.LeftToRight)
                lay.setContentsMargins(20, 20, 20, 20)
                lay.setSpacing(20)
                lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    # ------------------------------------------------------- expanded / mini
    def set_expanded(self, expanded: bool):
        """Rebuilds card layout based on window mode."""
        if expanded == self._expanded:
            return
        self._expanded = expanded

        # Bezpiecznie odpinamy karty ze starego layoutu
        old = self.cards_container.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(self.cards_container)
            from PyQt6 import sip
            sip.delete(old)

        if expanded:
            self._root.setAlignment(Qt.AlignmentFlag.AlignTop) # Pionowe pozycjonowanie: na samej górze w trybie Extended
            new_l = QVBoxLayout(self.cards_container)
            new_l.setContentsMargins(30, 0, 30, 0)
            new_l.setSpacing(20)
            self.welcome_sec.show()
            
            # Resetujemy rozmiary z Mini
            for card in (self.auto_card, self.manual_card):
                card.setMinimumSize(0, 0)
                card.setMaximumSize(16777215, 16777215)
                card.setFixedHeight(150)
                card.info_btn.hide()

            self._update_card_text(self.auto_card, "🤖", _t("auto_mode"), _t("auto_desc"), False)
            self._update_card_text(self.manual_card, "🔍", _t("manual_mode"), _t("manual_desc"), False)
            
            # W Extended dodajemy bez centrowania by wypełniły szerokość
            new_l.addWidget(self.auto_card)
            new_l.addWidget(self.manual_card)
            self.toggle_sec.show()
        else:
            self._root.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Pionowe pozycjonowanie: idealnie na środku w trybie Mini!
            new_l = QHBoxLayout(self.cards_container)
            # Kompensujemy asymetryczny margines głównego okna (15px lewy, 5px prawy), by kafelki leżały idealnie symetrycznie
            new_l.setContentsMargins(15, 0, 23, 0) 
            new_l.setSpacing(12)
            self.welcome_sec.hide()
            self.toggle_sec.hide()
            
            # Prostokątne, smukłe kafle w Mini (165x54)
            self.auto_card.setFixedSize(172, 54)
            self.manual_card.setFixedSize(172, 54)
            
            self._update_card_text(self.auto_card, "🤖", _t("auto_mode"), _t("auto_desc"), True)
            self._update_card_text(self.manual_card, "🔍", _t("manual_mode"), _t("manual_desc"), True)
            
            # Pokazujemy i pozycjonujemy info w Mini (wyśrodkowane w pionie z prawej strony)
            for card in (self.auto_card, self.manual_card):
                card.info_btn.show()
                card.info_btn.move(card.width() - 22, (card.height() - 20) // 2)

            # W Mini centrujemy prostokąty
            new_l.addWidget(self.auto_card, 0, Qt.AlignmentFlag.AlignCenter)
            new_l.addWidget(self.manual_card, 0, Qt.AlignmentFlag.AlignCenter)

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure info icons have the filter installed when shown
        win = self.window()
        if win:
            for card in (self.auto_card, self.manual_card):
                card.info_btn.installEventFilter(win)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-position info icons on resize if in mini
        if not self._expanded:
            for card in (self.auto_card, self.manual_card):
                card.info_btn.move(card.width() - 22, (card.height() - 20) // 2)

    def retranslate_ui(self):
        """Dynamically updates all labels on the home screen after language change."""
        # 1. Aktualizacja nagłówków głównych
        if hasattr(self, 'welcome_title_lbl'):
            self.welcome_title_lbl.setText(_t("welcome_title"))
            
        if hasattr(self, 'welcome_sub_lbl'):
            import random
            from core.translations import TRANSLATIONS, Translator
            
            # Pobieramy bieżący język z Translatora
            lang = Translator._lang if hasattr(Translator, '_lang') else "pl"
            data = TRANSLATIONS.get(lang, TRANSLATIONS["pl"])
            
            # Łączymy obie listy dla wybranego języka
            all_texts = data.get("welcome_subtitle", []) + data.get("eula_rules", [])
            
            # Jeśli obecny tekst NIE występuje w wybranym języku (co jest pewne przy zmianie), losujemy nowy
            if self.current_splash_text not in all_texts:
                self.current_splash_text = random.choice(all_texts) if all_texts else "KuzenBot Ready"
            
            self.welcome_sub_lbl.setText(self.current_splash_text)
            
        # 2. Aktualizacja tekstów w kafelkach trybów w zależności od obecnego stanu (Mini/Expanded)
        if hasattr(self, 'auto_card') and hasattr(self, 'manual_card'):
            is_mini = not self._expanded
            self._update_card_text(self.auto_card, "🤖", _t("auto_mode"), _t("auto_desc"), is_mini)
            self._update_card_text(self.manual_card, "🔍", _t("manual_mode"), _t("manual_desc"), is_mini)
            
        # DODAJ TAKŻE ODŚWIEŻENIE TEKSTU PRZEŁĄCZNIKA:
        if hasattr(self, 'toggle'):
            self.toggle.label_builds.setText(_t("builds_toggle"))
            self.toggle.label_stats.setText(_t("stats_toggle"))

