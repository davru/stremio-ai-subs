import requests

class IMDBService:
    def __init__(self):
        pass

    def search_content(self, query):
        """
        Search movies or series using IMDb suggestion endpoint (unofficial but fast).
        """
        if not query:
            return []
            
        # Endpoint needs the first letter for the path
        first_char = query[0].lower()
        # Clean query for url
        clean_query = requests.utils.quote(query.lower())
        
        url = f"https://v2.sg.media-imdb.com/suggestion/{first_char}/{clean_query}.json"
        
        try:
            # We need a browser User-Agent to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            
            results = []
            if 'd' in data:
                for item in data['d']:
                    # extract relevant data
                    # id is usually 'tt1234567'
                    imdb_id = item.get('id')
                    title = item.get('l')
                    year = item.get('y')
                    kind = item.get('q') # feature, TV series, etc.
                    cover = item.get('i', {}).get('imageUrl')
                    
                    # Filter only items that look like movies or series (have year and title)
                    if imdb_id and title:
                        # OpenSubtitles requires ID, user indicates keeping 'tt'
                        
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
            print(f"Error searching on IMDb (Suggestion API): {e}")
            return []
