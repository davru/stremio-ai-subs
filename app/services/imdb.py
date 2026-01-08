import requests

class IMDBService:
    def __init__(self):
        pass

    def search_content(self, query):
        """
        Busca películas o series usando el endpoint de sugerencias de IMDb (no oficial pero rápido).
        """
        if not query:
            return []
            
        # El endpoint necesita la primera letra para el path
        first_char = query[0].lower()
        # Limpiar query para url
        clean_query = requests.utils.quote(query.lower())
        
        url = f"https://v2.sg.media-imdb.com/suggestion/{first_char}/{clean_query}.json"
        
        try:
            # Necesitamos un User-Agent de navegador para que no nos bloqueen
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            
            results = []
            if 'd' in data:
                for item in data['d']:
                    # extraemos datos relevantes
                    # id suele ser 'tt1234567'
                    imdb_id = item.get('id')
                    title = item.get('l')
                    year = item.get('y')
                    kind = item.get('q') # feature, TV series, etc.
                    cover = item.get('i', {}).get('imageUrl')
                    
                    # Filtramos solo items que parecen peliculas o series (tienen año y titulo)
                    if imdb_id and title:
                        # OpenSubtitles requiere el ID, el usuario indica mantener el 'tt'
                        
                        results.append({
                            "imdb_id": imdb_id, # 'tt1234567'
                            "display_id": imdb_id,
                            "title": title,
                            "year": year,
                            "kind": kind,
                            "cover": cover
                        })
            
            return results
            
        except Exception as e:
            print(f"Error buscando en IMDb (API Sugerencias): {e}")
            return []
