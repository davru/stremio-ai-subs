import os
import requests
from dotenv import load_dotenv
from app.utils.logger import log

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
            "User-Agent": "TemporaryUserAgent" # For development/testing
        }
        self.token = None

    def login(self):
        if not USERNAME or not PASSWORD:
            raise Exception("OpenSubtitles credentials not configured")
            
        payload = {"username": USERNAME, "password": PASSWORD}
        response = requests.post(f"{BASE_URL}/login", json=payload, headers=self.headers)
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers["Authorization"] = f"Bearer {self.token}"
            return True
        else:
            log.error(f"Login error: {response.text}")
            return False

    def search(self, imdb_id=None, parent_imdb_id=None, query=None):
        # Search endpoint does not strictly require user token, only API Key.
        
        params = {
            "languages": "en", 
            "order_by": "download_count", 
            "order_direction": "desc"
        }
        
        if parent_imdb_id:
            # For series (TV Shows), use parent_imdb_id with series ID
            params["parent_imdb_id"] = int(parent_imdb_id.replace("tt", "")) if str(parent_imdb_id).startswith("tt") else parent_imdb_id
        elif imdb_id:
            # User indicates 'tt' should be kept for search
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
            log.error(f"Error searching subtitles: {e}")
            if 'response' in locals():
                log.debug(f"Response: {response.text}")
            return []

    def search_features(self, query):
        """
        Search metadata for movies/series on OpenSubtitles (not subtitles, just info).
        """
        params = {"query": query}
        try:
            response = requests.get(f"{BASE_URL}/features", params=params, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            log.error(f"Error searching features: {e}")
            return []

    def download_url(self, file_id):
        if not self.token:
            self.login()
            
        payload = {"file_id": int(file_id)}
        response = requests.post(f"{BASE_URL}/download", json=payload, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("link")
        return None

    # Note: Upload is complex and usually requires video hash.
    # For now we leave a placeholder or basic upload implementation if you have the file.
    # OpenSubtitles requires video hash to upload, which is hard if we only search by text.
    # We will focus on download and translation first.
