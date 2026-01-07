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

    def search(self, query):
        # El endpoint de búsqueda no requiere token de usuario obligatoriamente, solo API Key.
        # Quitamos la llamada forzada a login() para permitir búsquedas sin login.
        
        params = {
            "query": query,
            "languages": "en", 
            "order_by": "download_count", 
            "order_direction": "desc"
        }
        
        try:
            response = requests.get(f"{BASE_URL}/subtitles", params=params, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error searching subtitles: {e}")
            if 'response' in locals():
                print(f"Response: {response.text}")
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
