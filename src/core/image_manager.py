import os
import requests
import sys

def resource_path(*paths):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, *paths)

class ImageManager:
    def __init__(self):
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        self.gods_dir = os.path.join(appdata, "KuzenBot", "gods")
        os.makedirs(self.gods_dir, exist_ok=True)
        
        # Mapa unikalnych nazw w CDN SmiteSource dla niespójnych bogów
        self.special_gods_map = {
            "Da Ji": "Daji",
            "Sun Wukong": "Sun_Wukong",
            "Guan Yu": "Guan_Yu",
            "Hou Yi": "Hou_Yi",
            "Hun Batz": "Hun_Batz",
            "Ne Zha": "Ne_Zha",
            "Zhong Kui": "Zhong_Kui",
            "Ah Muzen Cab": "Ah_Muzen_Cab",
            "Maman Brigitte": "Maman_Brigitte"
            # Morgan Le Fay i The Morrigan usunięte!
        }

    def get_god_portrait_path(self, god_name: str, download_if_missing: bool = False) -> str:
        """
        Checks if the god portrait exists locally.
        If not, it fetches it from the CDN in the background and returns the path.
        """
        if not god_name:
            return ""
            
        # Standaryzacja nazwy do pliku (np. "da-ji", "zeus")
        slug = god_name.lower().strip().replace(" ", "-").replace("'", "")
        
        # 1. NAJPIERW sprawdzamy pliki wbudowane w aplikację (.exe) folderze assets
        local_path = resource_path("assets", "gods", f"{slug}.png")
        if os.path.exists(local_path):
            return local_path
            
        # 2. POTEM sprawdzamy cache w AppData
        filepath = os.path.join(self.gods_dir, f"{slug}.png")
        if os.path.exists(filepath):
            return filepath
        
        if not download_if_missing:
            return ""
            
        # 3. Jeśli pliku nie ma nigdzie, pobieramy z CDN SmiteSource
        url_name = self.special_gods_map.get(god_name, god_name.replace(" ", "").replace("'", ""))
        url = f"https://cdn.smitesource.com/cdn-cgi/image/width=256,format=auto,quality=75/Gods/{url_name}/Default/t_GodPortrait_{url_name}.png"
        
        try:
            print(f"[ImageManager] Pobieranie brakującego portretu boga: {god_name} -> {url}")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return filepath
        except Exception as e:
            print(f"[ImageManager] Błąd pobierania portretu dla {god_name}: {e}")
            
        return "" # Zwraca pusty string w przypadku całkowitego błędu