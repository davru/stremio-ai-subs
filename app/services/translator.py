import re
import os
from ollama import AsyncClient
import asyncio
import time
from app.utils.logger import log

class TranslatorService:
    def __init__(self):
        # Get target language from environment
        self.target_language = os.getenv("TARGET_LANGUAGE", "Spanish")
        self.target_language_code = os.getenv("TARGET_LANGUAGE_CODE", "spa")
        
        # Configure Ollama
        self.model_ollama = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        self.client = AsyncClient()
        log.ai(f"Using Local Ollama ({self.model_ollama})")
        log.translate(f"Target language: {self.target_language} ({self.target_language_code})")

    async def _translate_batch(self, texts, title=None):
        # STRATEGY: Numbered list (More robust than JSON for small models like Llama 3 3B)
        
        # 1. Build numbered input
        input_formatted = ""
        for i, text in enumerate(texts):
            input_formatted += f"ITEM_{i}: {text}\n"

        context_instruction = f"Context: Subtitles for '{title}'." if title else "Context: Subtitles."

        system_prompt = (
            f"You are a professional subtitle translator. Your TASK is to translate the provided text list from ENGLISH to {self.target_language.upper()}.\n"
            f"{context_instruction}\n"
            "RULES:\n"
            f"1. You MUST translate every item to {self.target_language}. Do not leave English text.\n"
            "2. Keep the exact format 'ITEM_N: [Translation]'.\n"
            "3. Preserve tags: [BR], <i>, <b>, ♫.\n"
            "4. Example:\n"
            "   Input:\n"
            "     ITEM_0: Hello friend\n"
            "     ITEM_1: How are you?\n"
            "   Output:\n"
            "     ITEM_0: [Translation in target language ({{self.target_language}})]\n"
            "     ITEM_1: [Translation in target language ({{self.target_language}})]\n"
        )
        
        user_prompt = (
            f"Translate this list to {self.target_language}:\n\n"
            f"{input_formatted}"
        )
        
        try:
             # We use format='' (plain text) because JSON fails a lot on small models
             response = await self.client.chat(
                model=self.model_ollama, 
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
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
             log.error(f"Ollama batch error: {e}")
             return None

    async def _translate_single(self, text, title=None):
        context_instruction = f"Context: Subtitles for '{title}'." if title else ""
        
        system_prompt = (
            f"You are a professional translator. Translate the text from ENGLISH to {self.target_language.upper()}.\n"
            "Output ONLY the translation, nothing else."
        )
        
        user_prompt = (
            f"{context_instruction}\n"
            f"Translate this text to {self.target_language}:\n"
            f"{text}"
        )
        
        try:
            response = await self.client.chat(
                model=self.model_ollama, 
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ]
            )
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
            # Handle potential BOM or whitespace issues in 'line'
            clean_line = line.strip().replace('\ufeff', '')
            
            is_header = False
            if clean_line.isdigit() and (i + 1 < len(lines)):
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
                    'index': clean_line,
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
        # Check Ollama availability
        try:
            await self.client.show(self.model_ollama)
        except Exception as e:
            log.error(f"Error connecting to Ollama ({self.model_ollama}). Ensure Ollama is running.")
            raise e

        blocks = self._parse_srt(srt_content)
        log.info(f"Parsed {len(blocks)} subtitle blocks", "🧩")
        
        # Setup Log File in logs/ folder
        os.makedirs("logs", exist_ok=True)
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_') if title else "subtitle"
        log_filename = f"logs/translation_{safe_title}_{int(time.time())}.log"
        log.file(f"Live logging to: {log_filename}")
        
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write(f"Subtitle Translation Log\nTitle: {title}\nDate: {time.ctime()}\n")
            f.write("="*50 + "\n\n")

        # Group by item count
        # Reduce batch size for small models (Llama 3.2 3B)
        # Batch of 10 is a good speed/stability balance 
        BATCH_SIZE = 10
        
        batches = [blocks[i:i + BATCH_SIZE] for i in range(0, len(blocks), BATCH_SIZE)]

        log.batch(f"Created {len(batches)} batches for translation via Ollama ({self.model_ollama})")
        
        total_batches = len(batches)
        
        log.process(f"Starting translation with 4 concurrent workers", "🚀")
        semaphore = asyncio.Semaphore(4)

        async def process_batch(i, batch):
            async with semaphore:
                log.batch(f"Processing {len(batch)} items", i+1, total_batches)
                start_time = time.time()
                
                try:
                    # Prepare text list
                    texts_to_translate = [b['original_text'].replace('\n', ' [BR] ') for b in batch]
                    
                    # Try batch
                    translated_list = await self._translate_batch(texts_to_translate, title=title)
                    
                    batch_success = False
                    if translated_list and len(translated_list) == len(batch):
                        batch_success = True
                        for j, res in enumerate(translated_list):
                            clean_res = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                            if clean_res:
                                batch[j]['translated_text'] = clean_res
                            else:
                                batch_success = False
                                break
                    
                    if not batch_success:
                        log.warning(f"[Batch {i+1}] Validation failed. Retrying items individually")
                        for block in batch:
                            safe_text = block['original_text'].replace('\n', ' [BR] ')
                            try:
                                await asyncio.sleep(0.2) 
                                res = await self._translate_single(safe_text, title=title)
                                block['translated_text'] = re.sub(r'\s*\[br\]\s*', '\n', res, flags=re.IGNORECASE).strip()
                            except Exception as e_single:
                                block['translated_text'] = block['original_text']
                    
                    elapsed = time.time() - start_time
                    log.success(f"[Batch {i+1}] Finished in {elapsed:.1f}s")
                    
                    # LOGGING
                    try:
                        with open(log_filename, "a", encoding="utf-8") as f:
                            log_chunk = f"\n--- Batch {i+1} ---\n"
                            for b in batch:
                                t_text = b.get('translated_text', 'N/A')
                                log_chunk += f"[{b['index']}] {b['time']} => {t_text}\n"
                            f.write(log_chunk)
                    except Exception as log_err:
                        log.warning(f"Log write error: {log_err}")

                except Exception as e:
                    log.error(f"[Batch {i+1}] Error: {e}")
                    for block in batch:
                        if 'translated_text' not in block:
                             block['translated_text'] = block['original_text']

        # Run tasks concurrently
        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        # Use return_exceptions=True to ensure one crash doesn't stop others
        await asyncio.gather(*tasks, return_exceptions=True)

        return self._reconstruct_srt(blocks)
