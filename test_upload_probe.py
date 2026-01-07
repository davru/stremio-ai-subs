
import sys
import os
import requests
from dotenv import load_dotenv

# Add app to path to import the client
sys.path.append(os.path.join(os.getcwd(), 'app'))
from app.services.opensubtitles import OpenSubtitlesClient

load_dotenv()

def probe_upload_endpoint():
    client = OpenSubtitlesClient()
    if not client.login():
        print("Login failed")
        return

    # Try to hit the upload endpoint (POST /subtitles) with empty body to see requirements
    upload_url = "https://api.opensubtitles.com/api/v1/subtitles"
    
    print(f"Probing {upload_url}...")
    
    try:
        # 1. Try empty JSON
        response = requests.post(upload_url, json={}, headers=client.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_upload_endpoint()
