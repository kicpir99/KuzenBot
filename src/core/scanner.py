import os
import time
import re
import json
import difflib
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import logger

class GameScanner(QThread):
    god_detected = pyqtSignal(str) 
    lobby_joined = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.log_path = os.path.expandvars(r"%LOCALAPPDATA%\SMITE2Alpha\Saved\Logs\Hemingway.log")
        self.running = True
        self.gods_db_path = os.path.join("assets", "gods_db.json")
        
        self.english_gods, self.new_gods = self._load_gods_db()
        self.current_god = None
        self.last_emitted_god = None

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
            r = requests.get('https://smitesource.com/gods', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            frags = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', r.text)
            stream = ''.join(frags).replace('\\"', '"')
            slugs = sorted(set(re.findall(r'"slug":"([a-z0-9-]+)"', stream)))
            
            slug_to_name = {}
            special = {
                'the-morrigan': 'The Morrigan', 'baron-samedi': 'Baron Samedi',
                'da-ji': 'Da Ji', 'guan-yu': 'Guan Yu', 'hou-yi': 'Hou Yi',
                'hun-batz': 'Hun Batz', 'jing-wei': 'Jing Wei',
                'morgan-le-fay': 'Morgan Le Fay', 'ne-zha': 'Ne Zha',
                'nu-wa': 'Nu Wa', 'sun-wukong': 'Sun Wukong',
            }
            for slug in slugs:
                slug_to_name[slug] = special.get(slug, slug.replace('-', ' ').title())
            
            names = sorted(slug_to_name.values())
            old_set = set(n.lower() for n in old_names)
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
        """Intelligent, error-resistant name matching with fuzzy logic."""
        if not self.english_gods:
            return None

        localized_lower = localized_name.lower()

        # 1. SŁOWNIK GLOBALNY: Łapie polskie tłumaczenia oraz skróty/literówki programistów gry
        aliases = {
            "jorm": "Jormungandr",
            "jormungand": "Jormungandr",
            "tsokuyomi": "Tsukuyomi",
            "afrodyta": "Aphrodite", 
            "ozyrys": "Osiris", 
            "wulkan": "Vulcan",
            "chepri": "Khepri", 
            "bachus": "Bacchus", 
            "tanatos": "Thanatos",
            "odyn": "Odin", 
            "merkury": "Mercury", 
            "kupidyn": "Cupid",
            "atena": "Athena", 
            "nemezis": "Nemesis",
            "mama brygida": "Maman Brigitte", 
            "morrigan": "The Morrigan"
        }
        
        for alias, eng_name in aliases.items():
            if alias in localized_lower:
                return eng_name

        # 2. Substring Match: Sprawdza, czy oficjalna angielska nazwa jest częścią napisu (łapie skiny)
        for eng in self.english_gods:
            if eng.lower() in localized_lower:
                return eng

        # 3. Fuzzy Matching (Ostateczność) z bardzo rygorystycznym progiem błędu (0.75)
        # Przez tak wysoki próg, algorytm nie będzie już na ślepo zgadywał (jak przy Ah Puch)
        lower_gods = [g.lower() for g in self.english_gods]
        matches = difflib.get_close_matches(localized_lower, lower_gods, n=1, cutoff=0.75)
        if matches:
            idx = lower_gods.index(matches[0])
            return self.english_gods[idx]
            
        return None

    def run(self):
        if not os.path.exists(self.log_path):
            logger.warning(f"[Scanner] Nie znaleziono pliku logow pod: {self.log_path}")
            return

        logger.info(f"[Scanner] Rozpoczeto nasluch logow: {self.log_path}")
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                f.seek(pos - min(30000, pos))
                
                # Skanowanie historii, żeby wiedzieć kto był zaznaczony przed odpaleniem apki
                last_found_god = None
                for h_line in f.readlines():
                    if "Ally 0 Skin" in h_line:
                        match = re.search(r"Ally 0 Skin (.+?)$", h_line)
                        if match:
                            god_name = self._match_god_name(match.group(1).strip())
                            if god_name: last_found_god = god_name
                
                if last_found_god:
                    self.last_emitted_god = last_found_god
                    self.god_detected.emit(last_found_god)
                
                f.seek(0, os.SEEK_END)
                logger.info("[Scanner] Oczekiwanie na akcje w lobby...")
                
                # Główna pętla
                while self.running:
                    line = f.readline()
                    if not line:
                        time.sleep(0.05)
                        continue
                    
                    if "TransitionToDraftState" in line and "CharacterDraft" in line:
                        if "Setup" in line:
                            self.last_emitted_god = None
                            self.lobby_joined.emit()
                    
                    if "Ally 0 Skin" in line:
                        match = re.search(r"Ally 0 Skin (.+?)$", line)
                        if match:
                            raw_local = match.group(1).strip()
                            god_name = self._match_god_name(raw_local)
                            
                            if god_name and god_name != self.last_emitted_god:
                                logger.info(f"[Scanner] Wykryto Twoj wybor: {god_name}")
                                self.last_emitted_god = god_name
                                self.god_detected.emit(god_name)

        except Exception as e:
            logger.error(f"[Scanner] Blad podczas odczytu logow: {e}", exc_info=True)

    def stop(self):
        self.running = False