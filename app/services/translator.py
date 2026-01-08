import re
import ollama
import os
import google.generativeai as genai
from ollama import AsyncClient
import asyncio
import time

class TranslatorService:
    def __init__(self):
        # Configurar Gemini si hay API Key
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            # Usar Gemini 2.0 Flash (Disponible en 2026, más rápido y capaz)
            self.model_name = "gemini-2.0-flash"
            self.use_gemini = True
            print(f"✨ Using Google Gemini API ({self.model_name})")
            
            # Inicializar también Ollama como fallback
            self.client = AsyncClient()
            self.model_ollama = "llama3.2:latest"
        else:
            self.use_gemini = False
            self.model_ollama = "llama3.2:latest"
            self.client = AsyncClient()
            print(f"🦙 Using Local Ollama ({self.model_ollama})")

    async def _translate_gemini_full_content(self, srt_content, title=None):
        """Traduce TODO el contenido de una vez usando el contexto masivo de Gemini"""
        model = genai.GenerativeModel(self.model_name)
        
        context_instruction = f"Context: You are translating subtitles for the movie/series '{title}'." if title else "Context: You are translating subtitles for a movie/series."
        
        prompt = (
            "You are a professional movie and series translator. Your task is to translate the following SRT content from English to Spanish (Spain).\n"
            f"{context_instruction}\n"
            "STRICT RULES:\n"
            "1. Output valid SRT format ONLY. Do not wrap in markdown code blocks.\n"
            "2. Preserve all timestamps and indices exactly.\n"
            "3. Translate text content to natural, idiomatic Spanish (Spain).\n"
            "4. KEEP keys/tags: [BR], <i>, <b>, <u>, </i>, </b>, </u>, ♪, ♫, #, and any other special symbol.\n"
            "5. Do NOT translate speaker names if they appear in uppercase (e.g. 'JOHN:').\n"
            "6. Provide the FULL translation for the input provided.\n\n"
            "INPUT SRT CONTENT:\n"
            f"{srt_content}"
        )
        
        try:
             # Gemini 1.5 Flash supports ~1M tokens, so we can send the whole file usually.
             # However, for huge files, we might occasionally split, but SRTs are small (50k chars).
             
             # Run in executor because genai is sync (mostly)
             loop = asyncio.get_event_loop()
             response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
             return response.text.replace("```srt", "").replace("```", "").strip()
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            raise e

    async def _translate_batch(self, texts, title=None):
        # ESTRATEGIA: Lista numerada (Más robusto que JSON para modelos pequeños como Llama 3 3B)
        
        # 1. Construir entrada numerada
        input_formatted = ""
        for i, text in enumerate(texts):
            input_formatted += f"ITEM_{i}: {text}\n"

        context_instruction = f"Contexto: Estas traduciendo subtítulos para la película/serie '{title}'." if title else "Contexto: Traducción de subtítulos."

        prompt = (
            f"Actúa como traductor profesional de EN a ES (España). {context_instruction}\n"
            "INSTRUCCIONES CLAVE:\n"
            "1. Traduce cada línea manteniendo el prefijo exacto 'ITEM_N: '.\n"
            "2. NO toques las etiquetas [BR], <i>, <b>, <u>, ♪, ♫.\n"
            "3. NO añadas charla, ni introducciones. Solo la lista traducida.\n"
            "4. Respeta el Español de España (idiomático).\n\n"
            "TEXTO A TRADUCIR:\n"
            f"{input_formatted}"
        )
        
        try:
             # Usamos format='' (texto plano) porque JSON falla mucho en modelos pequeños
             response = await self.client.chat(
                model=self.model_ollama, 
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'num_ctx': 4096} # Aumentar ventana de contexto si es posible
             )
             content = response['message']['content'].strip()
             
             # Parsear salida
             translated_map = {}
             lines = content.split('\n')
             for line in lines:
                 match = re.match(r'ITEM_(\d+):\s*(.*)', line)
                 if match:
                     idx = int(match.group(1))
                     text = match.group(2).strip()
                     translated_map[idx] = text
            
             # Reconstruir lista ordenada
             result_list = []
             for i in range(len(texts)):
                 # Si falta alguna línea, usamos el original como fallback en lugar de fallar todo el batch
                 result_list.append(translated_map.get(i, texts[i]))
                 
             return result_list

        except Exception as e:
             print(f"❌ Error batch Ollama: {e}")
             return None

    async def _translate_single(self, text, title=None):
        context_instruction = f"Context: You are translating subtitles for '{title}'." if title else ""
        prompt = (
            f"Translate exactly this text to Spanish (Spain). {context_instruction}\n"
            "Preserve [BR] tags.\n"
            "Preserve tags <i>, <b>, <u> and symbols ♪, ♫, #.\n"
            "Output ONLY the translation.\n\n"
            f"{text}"
        )
        try:
            response = await self.client.chat(model=self.model_ollama, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content'].strip()
        except:
            return text 

    def _parse_srt(self, content):
        # Normalizar saltos de línea
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = [l.strip() for l in content.split('\n')]
        
        blocks = []
        current_block = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Heurística robusta: Si encontramos un número solo en una línea...
            # Y la SIGUIENTE línea contiene '-->', entonces es cabecera de bloque.
            is_header = False
            if line.isdigit() and (i + 1 < len(lines)):
                if '-->' in lines[i+1]:
                    is_header = True
            
            if is_header:
                # Si había un bloque abierto, lo cerramos y guardamos
                if current_block:
                    # Parse text list to string
                    current_block['original_text'] = "\n".join(current_block['text_lines'])
                    del current_block['text_lines'] # Clean up
                    blocks.append(current_block)
                
                # Iniciamos nuevo bloque
                current_block = {
                    'index': line,
                    'time': lines[i+1],
                    'text_lines': []
                }
                i += 2 # Saltamos linea indice y linea tiempo
                continue
            
            # Si estamos dentro de un bloque, acumulamos texto
            if current_block is not None:
                # Si la linea no está vacía, es texto.
                # Ignoramos lineas vacias dentro del bloque para no meter ruido.
                if line:
                    current_block['text_lines'].append(line)
            
            i += 1
            
        # Añadir el último bloque pendiente
        if current_block:
            current_block['original_text'] = "\n".join(current_block['text_lines'])
            if 'text_lines' in current_block: del current_block['text_lines']
            blocks.append(current_block)
            
        return blocks

    def _reconstruct_srt(self, blocks):
        output = []
        for b in blocks:
            text = b.get('translated_text', b['original_text'])
            output.append(f"{b['index']}\n{b['time']}\n{text}")
        return "\n\n".join(output)

    async def translate_srt(self, srt_content, title=None):
        if self.use_gemini:
             print("⚡️ Fast Translation with Gemini Flash...")
             # Dividir en chunks si es MASIVO (>800kb), pero SRTs normales caben de sobra.
             # Gemini Flash soporta ~700,000 palabras. Un SRT tiene ~5,000.
             # enviamos directo.
             try:
                translated = await self._translate_gemini_full_content(srt_content, title)
                return translated
             except Exception as e:
                print(f"⚠️ Gemini request failed: {e}. Falling back to Ollama if available...")
                if not hasattr(self, 'client') or not self.client: 
                     raise e

        # Verificar disponibilidad de Ollama
        try:
            # Una pequeña llamada para despertar el modelo o verificar conexión
            if not self.use_gemini:
                # Solo comprobamos explicitamente si no venimos de un fallback
                # en fallback asumimos que vamos a instanciar/usar el cliente
                await self.client.show(self.model_ollama)
        except Exception as e:
            print(f"❌ Error conectando con Ollama ({self.model_ollama}). Asegúrate de que Ollama está corriendo.")
            raise e

        blocks = self._parse_srt(srt_content)
        print(f"🧩 Parsed {len(blocks)} subtitle blocks.")
        
        # Agrupar por cantidad de items
        # Reducimos tamaño de batch para modelos pequeños (Llama 3.2 3B)
        # Batch de 10 es un buen equilibrio velocidad/estabilidad 
        BATCH_SIZE = 10
        
        batches = [blocks[i:i + BATCH_SIZE] for i in range(0, len(blocks), BATCH_SIZE)]

        print(f"📦 Created {len(batches)} batches for translation via Ollama ({self.model_ollama}).")
        
        total_batches = len(batches)
        
        for i, batch in enumerate(batches):
            print(f"  🤖 Processing batch {i+1}/{total_batches} ({len(batch)} items)...")
            
            # Preparar lista de textos
            texts_to_translate = [b['original_text'].replace('\n', ' [BR] ') for b in batch]
            
            # Intentar batch
            translated_list = await self._translate_batch(texts_to_translate, title=title)
            
            if translated_list and len(translated_list) == len(batch):
                for j, res in enumerate(translated_list):
                    # Limpiar y asignar
                    clean_res = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                    batch[j]['translated_text'] = clean_res
            else:
                # Si falla el batch, hacemos fallback silencioso a original o reintento simple
                # En este caso, como _translate_batch ya tiene fallback interno (devuelve original si falta linea),
                # esto apenas debería ocurrir a menos que falle la llamada de red/ollama.
                print(f"  ⚠️ Text Batch flawed. Retrying individually ({len(batch)} items)...")
                for block in batch:
                    safe_text = block['original_text'].replace('\n', ' [BR] ')
                    res = await self._translate_single(safe_text, title=title)
                    block['translated_text'] = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()

        return self._reconstruct_srt(blocks)
