import os
import time
import re
import json
import difflib
import requests
import sys
from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import logger

def resource_path(*paths):
    """Zwraca ścieżkę do zasobów rozpakowanych przez PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

class GameScanner(QThread):
    god_detected = pyqtSignal(str) 
    lobby_joined = pyqtSignal()
    match_started = pyqtSignal()

    def __init__(self):
        super().__init__()
        local_appdata = os.getenv('LOCALAPPDATA')
        self.log_path = os.path.join(local_appdata, "SMITE2Alpha", "Saved", "Logs", "Hemingway.log")
        self.running = True
        self.gods_db_path = resource_path("assets", "gods_db.json")
        self.aliases_path = resource_path("assets", "god_aliases.json")
        
        self.english_gods, self.new_gods = self._load_gods_db()
        self.aliases = self._load_aliases()
        self.current_god = None
        self.last_emitted_god = None
        self.last_internal_model = None

    def _load_aliases(self):
        """Ładuje słownik aliasów językowych z pliku JSON."""
        if os.path.exists(self.aliases_path):
            try:
                with open(self.aliases_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[Scanner] Błąd odczytu pliku z aliasami: {e}")
        return {}

    GODS_CACHE_TTL = 86400

    def _load_gods_db(self):
        old_names = []
        if os.path.exists(self.gods_db_path):
            try:
                with open(self.gods_db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                old_names = list(data.get("name_to_slug", {}).keys())
                cached_at = data.get("cached_at", 0)
                if old_names and (time.time() - cached_at) < self.GODS_CACHE_TTL:
                    logger.info(f"[Scanner] Zaladowano {len(old_names)} bogow z cache.")
                    new_gods = data.get("new_gods", [])
                    return old_names, new_gods
                logger.info("[Scanner] Cache wygasl, pobieram swieza liste...")
            except Exception as e:
                logger.warning(f"[Scanner] Blad odczytu cache ({e}), pobieram od nowa...")
        return self._fetch_gods_from_smitesource(old_names)

    def _fetch_gods_from_smitesource(self, old_names=None):
        if old_names is None:
            old_names = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            slug_to_name = {}
            r = requests.get('https://smitesource.com/builds', headers=headers, timeout=10)
            m = re.search(r'\\"initialGods\\":(\[\{.+?\}\])(?:,\\"|\})', r.text)
            if m:
                raw = m.group(1).replace(chr(92) + chr(34), chr(34)).replace(chr(92) + chr(92), chr(92))
                gods_list = json.loads(raw)
                for g in gods_list:
                    s = g.get("slug")
                    n = g.get("name")
                    if s and n:
                        slug_to_name[s] = n
            else:
                r_gods = requests.get('https://smitesource.com/gods', headers=headers, timeout=10)
                slugs = sorted(set(re.findall(r'"slug":"([a-z0-9-]+)"', r_gods.text)))
                special = {
                    'the-morrigan': 'The Morrigan', 'baron-samedi': 'Baron Samedi',
                    'da-ji': 'Da Ji', 'guan-yu': 'Guan Yu', 'hou-yi': 'Hou Yi',
                    'hun-batz': 'Hun Batz', 'jing-wei': 'Jing Wei',
                    'morgan-le-fay': 'Morgan Le Fay', 'ne-zha': 'Ne Zha',
                    'nu-wa': 'Nu Wa', 'sun-wukong': 'Sun Wukong',
                    'bari': 'Princess Bari', 'mulan': 'Hua Mulan',
                }
                for slug in slugs:
                    if slug in ("gods", "builds", "items"): continue
                    slug_to_name[slug] = special.get(slug, slug.replace('-', ' ').title())
            
            names = sorted(slug_to_name.values())
            old_set = set(n.lower() for n in old_names) | {"princess bari", "hua mulan"}
            new_gods = [n for n in names if n.lower() not in old_set]
            
            os.makedirs("assets", exist_ok=True)
            with open(self.gods_db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "slug_to_name": slug_to_name,
                    "name_to_slug": {name: slug for slug, name in slug_to_name.items()},
                    "cached_at": time.time(),
                    "new_gods": new_gods,
                }, f, indent=2, ensure_ascii=False)
            
            return names, new_gods
        except Exception as e:
            logger.error(f"[Scanner] Nie udalo sie pobrac listy bogow: {e}")
            return old_names or [], []

    def _match_god_name(self, localized_name):
        """Intelligent, error-resistant name matching with whole-word parsing and hard-fallbacks."""
        if not self.english_gods:
            return None

        clean_name = re.sub(r'[^a-z]', ' ', localized_name.lower())
        clean_name = f" {clean_name} "

        # 2. Używamy załadowanego słownika z pliku JSON
        for alias, eng_name in self.aliases.items():
            alias_clean = re.sub(r'[^a-z]', ' ', alias.lower())
            if f" {alias_clean} " in clean_name:
                return eng_name

        # 3. Szukanie DOKŁADNYCH oficjalnych angielskich nazw
        sorted_gods = sorted(self.english_gods, key=len, reverse=True)
        for eng in sorted_gods:
            eng_clean = re.sub(r'[^a-z]', ' ', eng.lower())
            if f" {eng_clean} " in clean_name:
                return eng

        # 4. Fallback: Chronione dopasowanie częściowe (Tylko dla słów >4 znaków)
        for eng in sorted_gods:
            if len(eng) > 4 and eng.lower() in clean_name:
                return eng

        # 5. Ograniczony Fuzzy Matching (Tylko długie słowa, wysoki rygor)
        words = clean_name.split()
        ignore_words = {'bp', 'god', 'c', 'skin', 'default', 'character', 'ally', 'enemy'}
        filtered_words = [w for w in words if w not in ignore_words and len(w) > 4]
        
        lower_gods = [g.lower() for g in self.english_gods]
        for word in filtered_words:
            matches = difflib.get_close_matches(word, lower_gods, n=1, cutoff=0.85)
            if matches:
                idx = lower_gods.index(matches[0])
                return self.english_gods[idx]

        logger.warning(f"[Scanner] UWAGA: Nie rozpoznano boga z logu: '{localized_name}'. Czysty string: '{clean_name}'")
        return None

    def run(self):
        log_dir = os.path.dirname(self.log_path)
        
        if not os.path.exists(log_dir):
            logger.warning(f"[Scanner] Katalog logów nie istnieje: {log_dir}. Gra prawdopodobnie nie była uruchamiana.")
            return

        if not os.path.exists(self.log_path):
            logger.warning(f"[Scanner] Nie znaleziono głównego pliku logów pod: {self.log_path}")
            return

        logger.info(f"[Scanner] Pomyślnie znaleziono plik. Rozpoczęto nasłuch logów: {self.log_path}")
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                # 1. Ogromny bufor 200 KB - niczego nie przeoczymy!
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                f.seek(pos - min(2000000, pos))
                
                last_found_god = None
                for h_line in f.readlines():
                    if "Ally 0 Skin" in h_line:
                        match = re.search(r"Ally 0 Skin (.+?)$", h_line)
                        if match and match.group(1).strip():
                            god_name = self._match_god_name(match.group(1).strip())
                            if god_name: last_found_god = god_name
                
                if last_found_god:
                    self.last_emitted_god = last_found_god
                    self.god_detected.emit(last_found_god)
                
                # Zabezpieczenie fizycznego rozmiaru pliku
                f.seek(0, os.SEEK_END)
                last_file_size = os.path.getsize(self.log_path)
                
                logger.info("[Scanner] Oczekiwanie na akcje w lobby...")
                
                # Główna pętla
                while self.running:
                    try:
                        current_size = os.path.getsize(self.log_path)
                        if current_size < last_file_size:
                            logger.info("[Scanner] Gra wyczyściła plik logów (restart gry). Resetuję wskaźnik na początek.")
                            f.seek(0, os.SEEK_SET)
                        last_file_size = current_size
                    except OSError:
                        pass
                    
                    line = f.readline()
                    if not line:
                        time.sleep(0.05)
                        continue
                    
                    if "TransitionToDraftState" in line and "CharacterDraft" in line:
                        if "Setup" in line:
                            self.last_emitted_god = None
                            self.lobby_joined.emit()

                    if "Bringing World /Game/Maps/" in line and "/Game/Maps/Lobbies/" not in line:
                        logger.info("[Scanner] Wykryto załadowanie mapy meczowej (Start meczu).")
                        self.match_started.emit()
                    
                    if "Ally 0 Skin" in line:
                        match = re.search(r"Ally 0 Skin (.+?)$", line)
                        if match and match.group(1).strip():
                            raw_local = match.group(1).strip()
                            god_name = self._match_god_name(raw_local)
                            if god_name and god_name != self.last_emitted_god:
                                logger.info(f"[Scanner] Wykryto wybór gracza: {god_name} (Odczyt z gry: {raw_local})")
                                self.last_emitted_god = god_name
                                self.god_detected.emit(god_name)

        except Exception as e:
            logger.error(f"[Scanner] Blad podczas odczytu logow: {e}", exc_info=True)

    def stop(self):
        self.running = False

