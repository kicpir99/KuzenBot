import os
import requests

class ImageManager:
    def __init__(self):
        self.gods_dir = os.path.join("assets", "gods")
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
            "Morgan Le Fay": "Morgan_Le_Fay",
            "Maman Brigitte": "Maman_Brigitte",
            "The Morrigan": "The_Morrigan"
        }

    def get_god_portrait_path(self, god_name: str) -> str:
        """
        Sprawdza czy portret boga istnieje lokalnie. 
        Jeśli nie, pobiera go z CDN w tle i zwraca ścieżkę.
        """
        if not god_name:
            return ""
            
        # Standaryzacja nazwy do pliku (np. "da-ji", "zeus")
        slug = god_name.lower().strip().replace(" ", "-").replace("'", "")
        filepath = os.path.join(self.gods_dir, f"{slug}.png")
        
        # Jeśli plik już jest na dysku, po prostu go zwróć
        if os.path.exists(filepath):
            return filepath
            
        # Jeśli pliku nie ma, pobieramy z CDN SmiteSource
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