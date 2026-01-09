from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import requests
import os
from app.services.opensubtitles import OpenSubtitlesClient
from app.services.translator import TranslatorService
from app.services.imdb import IMDBService
from app.services.uploader import StremioUploader

app = FastAPI()

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Temporary directory
os.makedirs("temp", exist_ok=True)

os_client = OpenSubtitlesClient()
translator = TranslatorService()
imdb_service = IMDBService()
uploader = StremioUploader()

class SearchRequest(BaseModel):
    query: str

class ProcessRequest(BaseModel):
    file_id: int
    file_name: str
    imdb_id: str | None = None # Optional, but necessary for upload
    title: str | None = None
    year: str | int | None = None
    content_type: str = "movie"  # "movie" or "series"
    season_number: int | None = None
    episode_number: int | None = None

def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error deleting temp: {e}")

async def run_upload_task(file_path: str, imdb_id: str, content_type: str = "movie", season: int = None, episode: int = None):
    if imdb_id:
        success = await uploader.upload_subtitle(file_path, imdb_id, content_type, season, episode)
        if success:
            print("🎉 Upload completed successfully.")
        else:
            print("⚠️ Upload failed.")
    # Cleanup file after attempt to upload
    cleanup_file(file_path)

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.get("/api/search_media")
async def search_media(query: str):
    """Search movies/series on IMDb (Suggestion endpoint)"""
    return imdb_service.search_content(query)

@app.get("/api/search_subtitles")
async def search_subtitles(imdb_id: str, kind: str = "movie"):
    """Search subtitles on OpenSubtitles using IMDb ID"""
    try:
        # If it is a series, use parent_imdb_id
        is_series = kind.lower() in ['tv series', 'tv mini-series', 'series']
        
        if is_series:
            results = os_client.search(parent_imdb_id=imdb_id)
        else:
            results = os_client.search(imdb_id=imdb_id)
            
        # Simplify response for frontend
        simplified = []
        for item in results:
            attrs = item.get('attributes', {})
            files = attrs.get('files', [])
            if files:
                file_id = files[0].get('file_id')
                file_name = files[0].get('file_name')
                
                # Extract season and episode from feature_details if they exist
                feature_details = attrs.get('feature_details', {})
                season_num = feature_details.get('season_number')
                episode_num = feature_details.get('episode_number')
                
                # If not in feature_details, try to extract from filename (fallback)
                if not season_num or not episode_num:
                    import re
                    # Regex for S01E01, 1x01, etc.
                    match = re.search(r'[sS](\d+)[eE](\d+)', file_name)
                    if match:
                        season_num = int(match.group(1))
                        episode_num = int(match.group(2))

                simplified.append({
                    "id": item.get('id'),
                    "file_id": file_id,
                    "file_name": file_name,
                    "language": attrs.get('language'),
                    "movie_name": feature_details.get('movie_name'),
                    "year": feature_details.get('year'),
                    "downloads": attrs.get('download_count'),
                    "season_number": season_num,
                    "episode_number": episode_num
                })
        return simplified
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_subtitle(request: ProcessRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Get download link
        download_link = os_client.download_url(request.file_id)
        if not download_link:
            raise HTTPException(status_code=404, detail="Could not get download link")
        
        # 2. Download original SRT content
        print(f"Downloading from {download_link}...")
        srt_response = requests.get(download_link)
        srt_content = srt_response.text
        
        # 3. Translate
        print(f"Translating content for: {request.title or 'Unknown'}...")
        translated_content = await translator.translate_srt(srt_content, title=request.title)
        
        # 4. Save file temporarily for upload
        # Use SRT_NAMING_FORMAT from environment or fallback to default
        naming_format = os.getenv("SRT_NAMING_FORMAT", "{language}_{title}_{year}[{author}].srt")
        
        if request.title:
            # Clean title: remove special chars and replace spaces with dots
            safe_title = "".join([c for c in request.title if c.isalnum() or c in " ._-"])
            safe_title = safe_title.strip().replace(" ", ".")
            safe_year = str(request.year) if request.year else ""
            
            # Apply naming format
            new_filename = naming_format.format(
                language="ES",
                title=safe_title,
                year=safe_year,
                author="davru.dev"
            )
        else:
            new_filename = f"ES_{request.file_name}"

        if not new_filename.lower().endswith('.srt'):
            new_filename += '.srt'
            
        temp_path = os.path.join("temp", new_filename)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        # 5. Schedule background upload
        print(request)
        if request.imdb_id:
            print(f"📅 Scheduling automatic upload for: {request.imdb_id} (S{request.season_number}E{request.episode_number})")
            background_tasks.add_task(
                run_upload_task, 
                temp_path, 
                request.imdb_id, 
                request.content_type, 
                request.season_number, 
                request.episode_number
            )
        else:
            print("⚠️ No IMDb ID, skipping automatic upload.")
        
        # 6. Respond to user
        if request.imdb_id:
            return {"status": "success", "message": "Translation completed. Upload to Stremio is being processed in the background."}
        else:
            # If for some reason there's no ID, indicate it was generated but not uploaded (though current flow always asks for ID)
            # In this case, clean up the file since the user won't download it
            background_tasks.add_task(cleanup_file, temp_path)
            return {"status": "warning", "message": "Translation completed, but no IMDb ID was provided for upload."}

    except Exception as e:
        print(f"Error processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
