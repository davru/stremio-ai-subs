from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import requests
import io
import os
import shutil
from app.services.opensubtitles import OpenSubtitlesClient
from app.services.translator import TranslatorService
from app.services.imdb import IMDBService
from app.services.uploader import StremioUploader

app = FastAPI()

# Servir archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Directorio temporal
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
    imdb_id: str | None = None # Opcional, pero necesario para upload
    title: str | None = None
    year: str | int | None = None
    content_type: str = "movie"  # "movie" o "series"

def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error borrando temp: {e}")

async def run_upload_task(file_path: str, imdb_id: str, content_type: str = "movie"):
    if imdb_id:
        success = await uploader.upload_subtitle(file_path, imdb_id, content_type)
        if success:
            print("🎉 Subida completada exitosamente.")
        else:
            print("⚠️ La subida falló.")
    # Limpiar archivo despues de intentar subir
    cleanup_file(file_path)

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.get("/api/search_media")
async def search_media(query: str):
    """Buscamos películas/series en IMDb (Endpoint sugerencias)"""
    return imdb_service.search_content(query)

@app.get("/api/search_subtitles")
async def search_subtitles(imdb_id: str, kind: str = "movie"):
    """Buscamos subtítulos en OpenSubtitles usando el ID de IMDb"""
    try:
        # Si es una serie, usar parent_imdb_id
        is_series = kind.lower() in ['tv series', 'tv mini-series', 'series']
        
        if is_series:
            results = os_client.search(parent_imdb_id=imdb_id)
        else:
            results = os_client.search(imdb_id=imdb_id)
            
        # Simplificar respuesta para el frontend
        simplified = []
        for item in results:
            attrs = item.get('attributes', {})
            files = attrs.get('files', [])
            if files:
                file_id = files[0].get('file_id')
                file_name = files[0].get('file_name')
                simplified.append({
                    "id": item.get('id'),
                    "file_id": file_id,
                    "file_name": file_name,
                    "language": attrs.get('language'),
                    "movie_name": attrs.get('feature_details', {}).get('movie_name'),
                    "year": attrs.get('feature_details', {}).get('year'),
                    "downloads": attrs.get('download_count')
                })
        return simplified
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_subtitle(request: ProcessRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Obtener link de descarga
        download_link = os_client.download_url(request.file_id)
        if not download_link:
            raise HTTPException(status_code=404, detail="No se pudo obtener el link de descarga")
        
        # 2. Descargar contenido SRT original
        print(f"Descargando desde {download_link}...")
        srt_response = requests.get(download_link)
        srt_content = srt_response.text
        
        # 3. Traducir
        print("Traduciendo contenido...")
        translated_content = translator.translate_srt(srt_content)
        
        # 4. Guardar archivo temporalmente para subirlo
        if request.title:
            # Personalización: ES + Titulo + Año + davru.dev
            # Limpiamos el título de caracteres raros y reemplazamos espacios por puntos
            safe_title = "".join([c for c in request.title if c.isalnum() or c in " ._-"])
            safe_title = safe_title.strip().replace(" ", ".")
            safe_year = f"_{request.year}" if request.year else ""
            
            new_filename = f"ES_{safe_title}{safe_year}[davru.dev].srt"
        else:
            new_filename = f"ES_{request.file_name}"

        if not new_filename.lower().endswith('.srt'):
            new_filename += '.srt'
            
        temp_path = os.path.join("temp", new_filename)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(translated_content)
            
        # 5. Programar subida en segundo plano
        if request.imdb_id:
            print(f"📅 Programando subida automática para: {request.imdb_id}")
            background_tasks.add_task(run_upload_task, temp_path, request.imdb_id, request.content_type)
        else:
            print("⚠️ No hay IMDb ID, se omite la subida automática.")
        
        # 6. Responder al usuario
        if request.imdb_id:
            return {"status": "success", "message": "Traducción completada. La subida a Stremio se está procesando en segundo plano."}
        else:
            # Si por alguna razón no hay ID, indicamos que se generó pero no se subió (aunque el flujo actual siempre pide ID)
            # En este caso, limpiamos el archivo ya que el usuario no lo descargará
            background_tasks.add_task(cleanup_file, temp_path)
            return {"status": "warning", "message": "Traducción completada, pero no se proporcionó IMDb ID para subirlo."}

    except Exception as e:
        print(f"Error procesando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
