import os
import asyncio
from playwright.async_api import async_playwright

STREMIO_EMAIL = os.getenv("STREMIO_EMAIL")
STREMIO_PASSWORD = os.getenv("STREMIO_PASSWORD")

class StremioUploader:
    async def upload_subtitle(self, file_path, imdb_id, content_type="movie", season=None, episode=None):
        if not STREMIO_EMAIL or not STREMIO_PASSWORD:
            print("❌ Error: Falta configuración de STREMIO_EMAIL o STREMIO_PASSWORD")
            return False

        print(f"🚀 Iniciando subida para {imdb_id} (Tipo: {content_type}, S:{season} E:{episode})...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Headless por defecto
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. Login
                print("🔑 Iniciando sesión...")
                await page.goto("https://stremio-community-subtitles.top/login")
                
                # Intentar llenar formulario de login
                await page.fill('input[name="email"], input[type="email"]', STREMIO_EMAIL)
                await page.fill('input[name="password"], input[type="password"]', STREMIO_PASSWORD)
                
                # Click en boton de submit (buscamos por tipo o texto)
                await page.click('button[type="submit"], input[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
                
                # Esperar navegación usando networkidle (más fiable que url exacta)
                # Esto espera a que no haya tráfico de red por 500ms, indicando que la página cargó
                await page.wait_for_load_state("networkidle")
                
                if "/login" in page.url:
                    print("⚠️ Aviso: La URL sigue conteniendo '/login'. Verifica credenciales.")
                
                print(f"✅ Login completado (URL actual: {page.url})")

                # 2. Ir a Upload
                print("📂 Navegando a página de subida...")
                await page.goto("https://stremio-community-subtitles.top/content/upload")
                
                # 3. Llenar formulario de subida
                # Nota: Esto es tentativo ya que no veo el código fuente. 
                # Se asume inputs estandar.
                
                # IMDb ID
                # Buscamos un input que tenga 'imdb' en el nombre o id, o sea el primer input de texto
                # Si el sitio pide "tt12345", nos aseguramos de tener el tt.
                full_imdb_id = imdb_id if str(imdb_id).startswith("tt") else f"tt{imdb_id}"
                
                print(f"📝 Rellenando ID: {full_imdb_id}")
                await page.fill('input[name*="content_id"], input[id*="content_id"]', full_imdb_id)

                # Tipo de contenido
                print("🗣 Seleccionando tipo de contenido...")
                select = await page.query_selector('select#content_type')
                if select:
                    # Mapeo simple: si es "episode" o "series", buscamos Episode o Series
                    target_type = "series" if content_type.lower() in ["series", "episode", "tv show"] else "movie"
                    
                    options = await select.query_selector_all('option')
                    for opt in options:
                        text = await opt.text_content()
                        if target_type.lower() in text.lower():
                            val = await opt.get_attribute('value')
                            await select.select_option(val)
                            break

                # Rellenar Season y Episode si aplica
                if season and episode:
                    print(f"🔢 Rellenando Temporada {season} y Episodio {episode}...")
                    # Intento 1: IDs/Names sugeridos
                    await page.fill('input[name="season_number"], input[id="season_number"]', str(season))
                    await page.fill('input[name="episode_number"], input[id="episode_number"]', str(episode))
                
                # Idioma
                # Asumimos un select. Seleccionamos 'Spanish' o 'es' por label o value.
                # A veces es un select dropdown
                print("🗣 Seleccionando idioma...")
                # Intentar seleccionar opción que contenga "Spanish" o "Español"
                select = await page.query_selector('select#language')
                if select:
                    options = await select.query_selector_all('option')
                    for opt in options:
                        text = await opt.text_content()
                        if "spa" in text.lower():
                            val = await opt.get_attribute('value')
                            await select.select_option(val)
                            break
                
                # Archivo
                print(f"📄 Adjuntando archivo: {file_path}")
                await page.set_input_files('input#subtitle_file', file_path)
                
                # 4. Enviar
                print("🚀 Enviando formulario...")
                # Buscar botón "Upload", "Save", "Submit"
                await page.click('button:has-text("Upload"), button:has-text("Save"), input[type="submit"]')
                
                # Esperar confirmación
                # Esperamos un poco o buscamos mensaje de éxito
                await page.wait_for_timeout(5000)
                
                print("✅ Subida finalizada.")
                return True

            except Exception as e:
                print(f"❌ Error durante la subida automática: {e}")
                # Tomar screenshot en caso de error para debug
                await page.screenshot(path="error_upload.png")
                print("📸 Captura de error guardada en error_upload.png")
                return False
            finally:
                await browser.close()
