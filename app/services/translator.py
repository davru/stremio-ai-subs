import re
import ollama
import os
import google.generativeai as genai
from ollama import AsyncClient
import asyncio
import time

class TranslatorService:
    def __init__(self):
        # Configure Gemini if API Key is present
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            # Use Gemini 2.0 Flash (Available in 2026, faster and more capable)
            self.model_name = "gemini-2.0-flash"
            self.use_gemini = True
            print(f"✨ Using Google Gemini API ({self.model_name})")
            
            # Initialize Ollama as fallback too
            self.client = AsyncClient()
            self.model_ollama = "llama3.2:latest"
        else:
            self.use_gemini = False
            self.model_ollama = "llama3.2:latest"
            self.client = AsyncClient()
            print(f"🦙 Using Local Ollama ({self.model_ollama})")

    async def _translate_gemini_full_content(self, srt_content, title=None):
        """Translates ALL content at once using Gemini's massive context"""
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
        # STRATEGY: Numbered list (More robust than JSON for small models like Llama 3 3B)
        
        # 1. Build numbered input
        input_formatted = ""
        for i, text in enumerate(texts):
            input_formatted += f"ITEM_{i}: {text}\n"

        context_instruction = f"Context: You are translating subtitles for the movie/series '{title}'." if title else "Context: Subtitle translation."

        prompt = (
            f"Act as a professional translator from EN to ES (Spain). {context_instruction}\n"
            "KEY INSTRUCTIONS:\n"
            "1. Translate each line keeping the exact prefix 'ITEM_N: '.\n"
            "2. DO NOT touch tags [BR], <i>, <b>, <u>, ♪, ♫.\n"
            "3. DO NOT add chatter or introductions. Only the translated list.\n"
            "4. Respect Spain Spanish (idiomatic).\n\n"
            "TEXT TO TRANSLATE:\n"
            f"{input_formatted}"
        )
        
        try:
             # We use format='' (plain text) because JSON fails a lot on small models
             response = await self.client.chat(
                model=self.model_ollama, 
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'num_ctx': 4096} # Increase context window if possible
             )
             content = response['message']['content'].strip()
             
             # Parse output
             translated_map = {}
             lines = content.split('\n')
             for line in lines:
                 match = re.match(r'ITEM_(\d+):\s*(.*)', line)
                 if match:
                     idx = int(match.group(1))
                     text = match.group(2).strip()
                     translated_map[idx] = text
            
             # Reconstruct ordered list
             result_list = []
             for i in range(len(texts)):
                 # If a line is missing, use original as fallback instead of failing the whole batch
                 result_list.append(translated_map.get(i, texts[i]))
                 
             return result_list

        except Exception as e:
             print(f"❌ Ollama batch error: {e}")
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
        # Normalize line breaks
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = [l.strip() for l in content.split('\n')]
        
        blocks = []
        current_block = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Robust heuristic: If we find a single number on a line...
            # AND the NEXT line contains '-->', then it is a block header.
            is_header = False
            if line.isdigit() and (i + 1 < len(lines)):
                if '-->' in lines[i+1]:
                    is_header = True
            
            if is_header:
                # If a block was open, close and save it
                if current_block:
                    # Parse text list to string
                    current_block['original_text'] = "\n".join(current_block['text_lines'])
                    del current_block['text_lines'] # Clean up
                    blocks.append(current_block)
                
                # Start new block
                current_block = {
                    'index': line,
                    'time': lines[i+1],
                    'text_lines': []
                }
                i += 2 # Skip index and timestamp lines
                continue
            
            # If inside a block, accumulate text
            if current_block is not None:
                # If line is not empty, it is text.
                # Ignore empty lines inside block to avoid noise.
                if line:
                    current_block['text_lines'].append(line)
            
            i += 1
            
        # Add the last pending block
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
             # Split into chunks if MASSIVE (>800kb), but normal SRTs fit easily.
             # Gemini Flash supports ~700,000 words. An SRT has ~5,000.
             # send directly.
             try:
                translated = await self._translate_gemini_full_content(srt_content, title)
                return translated
             except Exception as e:
                print(f"⚠️ Gemini request failed: {e}. Falling back to Ollama if available...")
                if not hasattr(self, 'client') or not self.client: 
                     raise e

        # Check Ollama availability
        try:
            # A small call to wake up the model or check connection
            if not self.use_gemini:
                # Only check explicitly if not coming from a fallback
                # in fallback we assume we will instantiate/use the client
                await self.client.show(self.model_ollama)
        except Exception as e:
            print(f"❌ Error connecting to Ollama ({self.model_ollama}). Ensure Ollama is running.")
            raise e

        blocks = self._parse_srt(srt_content)
        print(f"🧩 Parsed {len(blocks)} subtitle blocks.")
        
        # Group by item count
        # Reduce batch size for small models (Llama 3.2 3B)
        # Batch of 10 is a good speed/stability balance 
        BATCH_SIZE = 10
        
        batches = [blocks[i:i + BATCH_SIZE] for i in range(0, len(blocks), BATCH_SIZE)]

        print(f"📦 Created {len(batches)} batches for translation via Ollama ({self.model_ollama}).")
        
        total_batches = len(batches)
        
        for i, batch in enumerate(batches):
            print(f"  🤖 Processing batch {i+1}/{total_batches} ({len(batch)} items)...")
            
            # Prepare text list
            texts_to_translate = [b['original_text'].replace('\n', ' [BR] ') for b in batch]
            
            # Try batch
            translated_list = await self._translate_batch(texts_to_translate, title=title)
            
            if translated_list and len(translated_list) == len(batch):
                for j, res in enumerate(translated_list):
                    # Clean and assign
                    clean_res = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                    batch[j]['translated_text'] = clean_res
            else:
                # If batch fails, silent fallback to original or simple retry
                # In this case, since _translate_batch already has internal fallback (returns original if line missing),
                # this should barely happen unless network/ollama call fails.
                print(f"  ⚠️ Text Batch flawed. Retrying individually ({len(batch)} items)...")
                for block in batch:
                    safe_text = block['original_text'].replace('\n', ' [BR] ')
                    res = await self._translate_single(safe_text, title=title)
                    block['translated_text'] = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()

        return self._reconstruct_srt(blocks)
