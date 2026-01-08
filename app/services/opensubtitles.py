import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.opensubtitles.com/api/v1"
API_KEY = os.getenv("OPENSUBTITLES_API_KEY")
USERNAME = os.getenv("OPENSUBTITLES_USERNAME")
PASSWORD = os.getenv("OPENSUBTITLES_PASSWORD")

class OpenSubtitlesClient:
    def __init__(self):
        self.headers = {
            "Api-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "TemporaryUserAgent" # Para desarrollo/pruebas
        }
        self.token = None

    def login(self):
        if not USERNAME or not PASSWORD:
            raise Exception("Credenciales de OpenSubtitles no configuradas")
            
        payload = {"username": USERNAME, "password": PASSWORD}
        response = requests.post(f"{BASE_URL}/login", json=payload, headers=self.headers)
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers["Authorization"] = f"Bearer {self.token}"
            return True
        else:
            print(f"Error login: {response.text}")
            return False

    def search(self, imdb_id=None, parent_imdb_id=None, query=None):
        # El endpoint de búsqueda no requiere token de usuario obligatoriamente, solo API Key.
        
        params = {
            "languages": "en", 
            "order_by": "download_count", 
            "order_direction": "desc"
        }
        
        if parent_imdb_id:
            # Para series (TV Shows), usamos parent_imdb_id con el ID de la serie
            params["parent_imdb_id"] = int(parent_imdb_id.replace("tt", "")) if str(parent_imdb_id).startswith("tt") else parent_imdb_id
        elif imdb_id:
            # El usuario indica que se debe conservar el 'tt' para la búsqueda
            params["imdb_id"] = imdb_id
        elif query:
            params["query"] = query
        else:
            return []
        
        try:
            response = requests.get(f"{BASE_URL}/subtitles", params=params, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error searching subtitles: {e}")
            if 'response' in locals():
                print(f"Response: {response.text}")
            return []

    def search_features(self, query):
        """
        Busca metadatos de películas/series en OpenSubtitles (no subtítulos, solo info).
        """
        params = {"query": query}
        try:
            response = requests.get(f"{BASE_URL}/features", params=params, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error searching features: {e}")
            return []

    def download_url(self, file_id):
        if not self.token:
            self.login()
            
        payload = {"file_id": int(file_id)}
        response = requests.post(f"{BASE_URL}/download", json=payload, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("link")
        return None

    # Nota: La subida es compleja y requiere hash del video normalmente.
    # Por ahora dejaremos un placeholder o implementación básica de subida si tienes el archivo.
    # OpenSubtitles requiere hash de película para subir, lo cual es dificil si solo buscamos por texto.
    # Nos centraremos en la descarga y traducción primero.
