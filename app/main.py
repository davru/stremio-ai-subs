from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import requests
import io
import os
from app.services.opensubtitles import OpenSubtitlesClient
from app.services.translator import TranslatorService
from app.services.imdb import IMDBService

app = FastAPI()

# Servir archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

os_client = OpenSubtitlesClient()
translator = TranslatorService()
imdb_service = IMDBService()

class SearchRequest(BaseModel):
    query: str

class ProcessRequest(BaseModel):
    file_id: int
    file_name: str

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
async def process_subtitle(request: ProcessRequest):
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
        
        # 4. Retornar archivo traducido
        
        new_filename = f"ES_{request.file_name}"
        if not new_filename.lower().endswith('.srt'):
            new_filename += '.srt'
            
        return StreamingResponse(
            io.BytesIO(translated_content.encode('utf-8')),
            media_type="application/x-subrip",
            headers={
                "Content-Disposition": f'attachment; filename="{new_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        print(f"Error procesando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
