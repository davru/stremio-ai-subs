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

    def _parse_srt(self, content):
        import re
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        parts = re.split(r'\n\n+', content.strip())
        blocks = []
        for part in parts:
            lines = part.split('\n')
            if len(lines) >= 3:
                # Detectar índice y tiempos
                if lines[0].strip().isdigit() and '-->' in lines[1]:
                    block = {
                        'index': lines[0].strip(),
                        'time': lines[1].strip(),
                        'original_text': "\n".join(lines[2:])
                    }
                    blocks.append(block)
        return blocks

    def _reconstruct_srt(self, blocks):
        output = []
        for b in blocks:
            text = b.get('translated_text', b['original_text'])
            output.append(f"{b['index']}\n{b['time']}\n{text}")
        return "\n\n".join(output)

    async def translate_srt(self, srt_content):
        import re 
        blocks = self._parse_srt(srt_content)
        print(f"🧩 Parsed {len(blocks)} subtitle blocks.")
        
        # Agrupar por chunks de tamaño seguro para el navegador
        MAX_CHUNK_SIZE = 1000 
        SEPARATOR = " ||| "
        
        batches = []
        current_batch = []
        current_batch_length = 0
        
        for block in blocks:
            text_len = len(block['original_text'])
            if current_batch and (current_batch_length + text_len + len(SEPARATOR)) > MAX_CHUNK_SIZE:
                batches.append(current_batch)
                current_batch = []
                current_batch_length = 0
            
            current_batch.append(block)
            current_batch_length += text_len + len(SEPARATOR)
            
        if current_batch:
            batches.append(current_batch)

        print(f"📦 Created {len(batches)} batches for translation.")

        print("🌍 Lanzando navegador para traducción local (Translation API)...")
        async with async_playwright() as p:
            # ...existing code...
            browser = None
            possible_paths = [
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
                "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" 
            ]
            executable_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    executable_path = path
                    print(f"   ✅ Usando ejecutable: {path}")
                    break
            
            try:
                browser = await p.chromium.launch(
                    executable_path=executable_path,
                    headless=False,
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
                await page.goto("chrome://newtab")
            except:
                pass
            
            total_batches = len(batches)
            
            for i, batch in enumerate(batches):
                print(f"  Processing batch {i+1}/{total_batches} ({len(batch)} items)...")
                
                # Preparar texto unido: Reemplazamos saltos de línea internos por espacio para evitar confusión
                # o usamos un token especial si es necesario. Para subtítulos, space suele ser seguro si es una sola frase.
                # Pero si queremos multiline, usamos un placeholder.
                
                texts_to_translate = [b['original_text'].replace('\n', ' [BR] ') for b in batch]
                joined_text = SEPARATOR.join(texts_to_translate)
                
                translated_joined = await self._translate_chunk_in_browser(page, joined_text)
                
                if translated_joined.startswith("ERROR"):
                    raise Exception(f"Translation failed: {translated_joined}")
                
                # Separar resultados
                results = translated_joined.split(SEPARATOR.strip())
                
                # Validación básica
                if len(results) != len(batch):
                    # Fallback: traducir uno por uno
                    for block in batch:
                        safe_text = block['original_text'].replace('\n', ' [BR] ')
                        res = await self._translate_chunk_in_browser(page, safe_text)
                        if res.startswith("ERROR"):
                             raise Exception(f"Translation failed: {res}")
                        # Case insensitive replacement for [BR]
                        block['translated_text'] = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                else:
                    # Asignar resultados
                    for j, res in enumerate(results):
                        # Limpieza y restauración de saltos de línea
                        clean_res = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                        batch[j]['translated_text'] = clean_res

            await browser.close()
        
        return self._reconstruct_srt(blocks)
