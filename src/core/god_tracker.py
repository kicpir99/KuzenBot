import time, json, os

class GodTracker:
    @staticmethod
    def get_active_new_gods(current_new_gods):
        """Zwraca listę bogów, którzy są 'nowi' (max 7 dni od wykrycia)."""
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        tracker_path = os.path.join(appdata, "KuzenBot", "new_gods_tracker.json")
        
        # Wczytaj tracker
        tracker = {}
        if os.path.exists(tracker_path):
            try:
                with open(tracker_path, "r", encoding="utf-8") as f:
                    tracker = json.load(f)
            except: pass

        now = time.time()
        # Dodaj nowych do trackera
        for god in current_new_gods:
            if god not in tracker:
                tracker[god] = now
        
        # Przefiltruj (usuń te, które mają > 7 dni)
        seven_days = 7 * 24 * 3600
        active = [g for g, ts in tracker.items() if now - ts < seven_days]
        
        # Zapisz
        os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
        with open(tracker_path, "w", encoding="utf-8") as f:
            json.dump(tracker, f)
            
        return set(active)