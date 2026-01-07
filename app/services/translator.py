import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class TranslatorService:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("⚠️ ADVERTENCIA: DEEPSEEK_API_KEY no encontrada en .env")
            api_key = "dummy-key-to-prevent-crash"
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-chat"

    def translate_text_chunk(self, text_chunk):
        """
        Traduce un bloque de texto SRT manteniendo el formato.
        """
        system_prompt = (
            "Eres un traductor profesional de subtítulos. "
            "Tu tarea es traducir los siguientes subtítulos del inglés al español de España. "
            "DEBES mantener estrictamente el formato SRT (índices y tiempos). "
            "Solo traduce el texto del diálogo. No alteres los tiempos ni los números."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text_chunk}
                ],
                temperature=0.3,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error en traducción: {e}")
            return text_chunk # Retornar original en caso de fallo para no romper flujo


    def translate_srt(self, srt_content):
        # Dividir por bloques de subtítulos (doble salto de línea suele separar bloques)
        # Para ser más seguro con el contexto de LLM, enviaremos grupos de X caracteres o lineas.
        # Una estrategia simple es dividir por lineas, agrupar hasta ~2000 caracteres.
        
        lines = srt_content.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        MAX_CHUNK_SIZE = 3000  # Caracteres aprox

        for line in lines:
            current_chunk.append(line)
            current_length += len(line)
            
            # Si encontramos un salto de linea vacío (separador de bloque) y superamos el tamaño
            if line.strip() == "" and current_length > MAX_CHUNK_SIZE:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        translated_parts = []
        total_chunks = len(chunks)
        print(f"Traducido en {total_chunks} partes...")

        for i, chunk in enumerate(chunks):
            print(f"Traduciendo parte {i+1}/{total_chunks}...")
            translated = self.translate_text_chunk(chunk)
            translated_parts.append(translated)
        
        return "\n".join(translated_parts)
