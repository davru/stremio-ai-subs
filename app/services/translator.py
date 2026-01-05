import os
from playwright.async_api import async_playwright

class TranslatorService:
    def __init__(self):
        pass

    async def _translate_chunk_in_browser(self, page, text):
        js_code = """
        async (text) => {
            if (!('Translator' in self)) {
                return "ERROR: API 'Translator' no encontrada. Asegúrate de usar Chrome actualizado y habilitar flags.";
            }
            if (!window.myTranslator) {
                try {
                    window.myTranslator = await Translator.create({
                        sourceLanguage: 'en',
                        targetLanguage: 'es'
                    });
                } catch (e) {
                    return "ERROR: Fallo creando traductor: " + e.message;
                }
            }
            try {
                return await window.myTranslator.translate(text);
            } catch (e) {
                 return "ERROR: Fallo traduciendo: " + e.message;
            }
        }
        """
        return await page.evaluate(js_code, text)

    async def translate_srt(self, srt_content):
        # 1. Dividir en chunks (lógica preservada)
        lines = srt_content.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        MAX_CHUNK_SIZE = 1500 # Reducido un poco para browser

        for line in lines:
            current_chunk.append(line)
            current_length += len(line)
            if line.strip() == "" and current_length > MAX_CHUNK_SIZE:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        translated_parts = []
        
        print("🌍 Lanzando navegador para traducción local (Translation API)...")
        async with async_playwright() as p:
            browser = None
            # Rutas comunes de Chrome Canary/Dev en macOS
            possible_paths = [
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
                "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" # Fallback a estable
            ]
            
            executable_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    executable_path = path
                    print(f"   ✅ Usando ejecutable: {path}")
                    break
            
            if not executable_path:
                print("⚠️ No se encontró Chrome (Canary/Dev/Stable) en rutas estándar. Usando detección automática...")

            try:
                # Lanzamos con executable_path si lo encontramos
                browser = await p.chromium.launch(
                    executable_path=executable_path,
                    headless=False, # APIs experimentales requieren modo gráfico a menudo
                    args=[
                        "--enable-features=TranslationAPI,PromptAPIForGeminiNano,OptimizationGuideOnDeviceModel",
                        "--optimization-guide-on-device-model-params-override" 
                    ] 
                )
            except Exception as e:
                print(f"⚠️ Fallo lanzando navegador custom ('{e}'). Intentando default...")
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=False,
                    args=["--enable-features=TranslationAPI"]
                )

            page = await browser.new_page()
            try:
                # Navegar a una página local segura puede ayudar a exponer la API
                await page.goto("chrome://newtab")
            except:
                pass
            
            total = len(chunks)
            print(f"Traducido {total} partes con API Local...")
            
            for i, chunk in enumerate(chunks):
                print(f"  Processing part {i+1}/{total}...")
                translated = await self._translate_chunk_in_browser(page, chunk)
                
                if translated.startswith("ERROR"):
                    print(f"  ❌ {translated}")
                    raise Exception(f"Translation failed: {translated}")
                else:
                    translated_parts.append(translated)
            
            await browser.close()
        
        return "\n".join(translated_parts)
