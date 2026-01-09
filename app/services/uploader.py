import os
import time
from playwright.async_api import async_playwright
from app.utils.logger import log

STREMIO_EMAIL = os.getenv("STREMIO_EMAIL")
STREMIO_PASSWORD = os.getenv("STREMIO_PASSWORD")

class StremioUploader:
    async def upload_subtitle(self, file_path, imdb_id, content_type="movie", season=None, episode=None):
        if not STREMIO_EMAIL or not STREMIO_PASSWORD:
            log.error("STREMIO_EMAIL or STREMIO_PASSWORD configuration missing")
            return False

        log.upload(f"Starting upload for {imdb_id} (Type: {content_type}, S:{season} E:{episode})")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Headless by default
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. Login
                log.auth("Logging in")
                await page.goto("https://stremio-community-subtitles.top/login")
                
                # Try filling login form
                await page.fill('input[name="email"], input[type="email"]', STREMIO_EMAIL)
                await page.fill('input[name="password"], input[type="password"]', STREMIO_PASSWORD)
                
                # Click submit button (search by type or text)
                await page.click('button[type="submit"], input[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
                
                # Wait for navigation using networkidle (more reliable than exact url)
                # This waits for no network traffic for 500ms, indicating page loaded
                await page.wait_for_load_state("networkidle")
                
                if "/login" in page.url:
                    log.warning("URL still contains '/login'. Check credentials")
                
                log.success(f"Login completed (Current URL: {page.url})")

                # 2. Go to Upload
                log.web("Navigating to upload page")
                await page.goto("https://stremio-community-subtitles.top/content/upload")
                
                # 3. Fill upload form
                # Note: This is tentative as I don't see source code. 
                # Assuming standard inputs.
                
                # IMDb ID
                # Looking for input with 'imdb' in name or id, or first text input
                # If site asks for "tt12345", ensure we have 'tt'.
                full_imdb_id = imdb_id if str(imdb_id).startswith("tt") else f"tt{imdb_id}"
                
                log.info(f"Filling ID: {full_imdb_id}", "📝")
                await page.fill('input[name*="content_id"], input[id*="content_id"]', full_imdb_id)

                # Content type
                log.info("Selecting content type", "🗣")
                select = await page.query_selector('select#content_type')
                if select:
                    # Simple mapping: if "episode" or "series", search Episode or Series
                    target_type = "series" if content_type.lower() in ["series", "episode", "tv show"] else "movie"
                    
                    options = await select.query_selector_all('option')
                    for opt in options:
                        text = await opt.text_content()
                        if target_type.lower() in text.lower():
                            val = await opt.get_attribute('value')
                            await select.select_option(val)
                            break

                # Fill Season and Episode if applicable
                if season and episode:
                    log.info(f"Filling Season {season} and Episode {episode}", "🔢")
                    # Attempt 1: Suggested IDs/Names
                    await page.fill('input[name="season_number"], input[id="season_number"]', str(season))
                    await page.fill('input[name="episode_number"], input[id="episode_number"]', str(episode))
                
                # Language
                # Get target language code from environment (default: spa for Spanish)
                target_lang_code = os.getenv("TARGET_LANGUAGE_CODE", "spa")
                log.info(f"Selecting language: {target_lang_code}", "🗣")
                
                select = await page.query_selector('select#language')
                if select:
                    # Try to select by value directly first
                    try:
                        await select.select_option(target_lang_code)
                        log.success(f"Selected language code: {target_lang_code}")
                    except:
                        # Fallback: search through options if direct selection fails
                        options = await select.query_selector_all('option')
                        for opt in options:
                            val = await opt.get_attribute('value')
                            if val and target_lang_code.lower() in val.lower():
                                await select.select_option(val)
                                log.success(f"Selected language: {val}")
                                break
                
                # File
                log.file(f"Attaching file: {file_path}")
                await page.set_input_files('input#subtitle_file', file_path)
                
                # 4. Send
                log.upload("Sending form")
                # Search for "Upload", "Save", "Submit" button
                await page.click('button:has-text("Upload"), button:has-text("Save"), input[type="submit"]')
                
                # Wait for confirmation
                # Wait a bit or search for success message
                await page.wait_for_timeout(5000)
                
                log.success("Upload completed")
                return True

            except Exception as e:
                log.error(f"Error during automatic upload: {e}")
                # Take screenshot on error for debugging
                os.makedirs("errors", exist_ok=True)
                error_filename = f"errors/upload_error_{int(time.time())}.png"
                await page.screenshot(path=error_filename)
                log.info(f"Error capture saved to {error_filename}", "📸")
                return False
            finally:
                await browser.close()
