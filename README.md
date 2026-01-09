# 🎬 Stremio AI Subs

AI-powered subtitle translator with automatic Stremio upload. Download English subtitles from OpenSubtitles, translate them to any language using local AI (Ollama), and automatically upload to Stremio Community.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)

## ✨ Features

- 🔍 **Smart Search**: Search movies and TV series using IMDb integration
- 📥 **Auto Download**: Fetch English subtitles from OpenSubtitles API
- 🤖 **AI Translation**: Translate subtitles using local Ollama
- 🌍 **Multi-Language**: Support for 45+ languages (Spanish, French, German, Japanese, etc.)
- ⚡ **Parallel Processing**: 4 concurrent workers for fast batch translation
- 📤 **Auto Upload**: Automated upload to Stremio Community Subtitles
- 🎨 **Modern UI**: Clean, IMDb-inspired dark theme interface
- 📝 **Smart Logging**: Detailed translation logs with timestamps

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed with your preferred model (default: `llama3.2:latest`)
  ```bash
  ollama pull llama3.2:latest  # or any other model you prefer
  ```
- OpenSubtitles API key ([get one here](https://www.opensubtitles.com/en/consumers))
- Stremio Community account ([create here](https://stremio-community-subtitles.top))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/davru/stremio-ai-subs.git
   cd stremio-ai-subs
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and credentials
   ```

3. **Run the application**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

4. **Open in browser**
   ```
   http://localhost:8000
   ```

## 🔧 Configuration

Edit the `.env` file with your credentials:

```env
# OpenSubtitles API Configuration
OPENSUBTITLES_API_KEY=your_api_key_here
OPENSUBTITLES_USERNAME=your_username_here
OPENSUBTITLES_PASSWORD=your_password_here

# Stremio Community Subtitles Upload
STREMIO_EMAIL=your_stremio_email_here
STREMIO_PASSWORD=your_stremio_password_here

# Ollama Model (default: llama3.2:latest)
# Other options: llama3.1, mistral, deepseek-coder, etc.
OLLAMA_MODEL=llama3.2:latest

# Translation Target Language
# Full language name used in AI prompts (default: Spanish)
TARGET_LANGUAGE=Spanish

# Translation Target Language Code (ISO 639-2)
# 3-letter code for Stremio upload (default: spa)
# Common codes: eng, fra, deu, ita, por, pob, rus, jpn, zho, kor, ara
TARGET_LANGUAGE_CODE=spa

# SRT File Naming Format
# Available placeholders: {language}, {title}, {year}, {author}
SRT_NAMING_FORMAT={language}_{title}_{year}[{author}].srt
```

### Get Your API Keys

- **OpenSubtitles**: [Register here](https://www.opensubtitles.com/en/consumers)
- **Stremio Community**: [Sign up here](https://stremio-community-subtitles.top)
- **Stremio Addon**: [Install addon](https://stremio-community-subtitles.top) (required to use uploaded subtitles)

## 📖 How It Works

1. **Search** for your movie or TV series
2. **Select** the content from IMDb results
3. **Choose** the episode subtitle you want to translate
4. **Translate** - AI processes the subtitle in batches (takes 1-5 minutes per episode)
5. **Auto-upload** - Subtitle is automatically uploaded to Stremio Community

## 📺 Using Translated Subtitles in Stremio

Once your subtitles are translated and uploaded, follow these steps to use them in Stremio:

1. **Install the Stremio Community Subtitles Addon**
   - Visit [https://stremio-community-subtitles.top](https://stremio-community-subtitles.top)
   - Click on "Install Addon" or follow the installation instructions
   - The addon will be added to your Stremio client

2. **Watch Your Content**
   - Open Stremio and play your movie or TV episode
   - Click the **CC** (subtitles) button in the player
   - Your translated Spanish subtitles should appear in the list
   - Select them and enjoy!

**Note**: It may take a few minutes for newly uploaded subtitles to appear in Stremio after upload.

## 🛠️ Technical Details

### Architecture

- **Backend**: FastAPI (Python)
- **AI Engine**: Ollama (Customizable model, defaulted to llama3.2)
- **Automation**: Playwright for Stremio upload
- **Concurrency**: AsyncIO with 4 parallel workers
- **Parsing**: Custom SRT parser with BOM handling

### Translation Strategy

- Uses text-based numbered list format (`ITEM_N: text`) instead of JSON for better reliability
- System/user prompt separation with few-shot examples
- Batch processing with graceful fallback to single-item translation
- Preserves SRT timing and formatting

### File Structure

```
stremio-ai-subs/
├── app/
│   ├── main.py                 # FastAPI endpoints
│   └── services/
│       ├── translator.py       # AI translation logic
│       ├── opensubtitles.py    # OpenSubtitles API client
│       ├── uploader.py         # Stremio upload automation
│       └── imdb.py             # IMDb search integration
├── static/
│   ├── index.html              # FE html
│   ├── styles.css              # FE styles
│   └── favicon.svg             
├── logs/                       # Translation logs
├── errors/                     # Error screenshots
├── temp/                       # Temporary SRT files
└── .env                        # Configuration (create from .env.example)
```

## 🎯 Usage Examples

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

### Custom SRT Naming

Customize subtitle file names in `.env`:

```env
# Default format
SRT_NAMING_FORMAT={language}_{title}_{year}[{author}].srt
# Output: SPA_Breaking.Bad_2008[davru.dev].srt

# Simple format
SRT_NAMING_FORMAT={title}_S{season}E{episode}_{language}.srt
# Output: Breaking.Bad_S01E01_SPA.srt
```

### Changing Target Language

Translate subtitles to any supported language by updating `.env`:

**Supported Languages** (45+):
English (eng), Polish (pol), Spanish (spa), French (fra), German (deu), Italian (ita), Portuguese (por), Portuguese Brazil (pob), Russian (rus), Japanese (jpn), Chinese (zho), Korean (kor), Arabic (ara), Hindi (hin), Turkish (tur), Dutch (nld), Swedish (swe), Norwegian (nor), Danish (dan), Finnish (fin), Czech (ces), Slovak (slk), Hungarian (hun), Romanian (ron), Bulgarian (bul), Greek (ell), Hebrew (heb), Thai (tha), Vietnamese (vie), Indonesian (ind), Malay (msa), Ukrainian (ukr), Serbian (srp), Croatian (hrv), Slovenian (slv), Estonian (est), Latvian (lav), Lithuanian (lit), Persian (fas), Urdu (urd), Bengali (ben), Burmese (mya), Catalan (cat), Basque (eus), Esperanto (epo), Macedonian (mkd), Telugu (tel), Albanian (sqi)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenSubtitles](https://www.opensubtitles.com) for subtitle database
- [Ollama](https://ollama.ai) for local AI inference
- [Stremio Community](https://stremio-community-subtitles.top) for subtitle hosting
- [IMDb](https://www.imdb.com) for content metadata

## ⚠️ Disclaimer

This tool is for personal use only. Respect copyright laws and subtitle licensing terms. Always credit original subtitle authors.

---

Made with ❤️ by [David (davru) Sanchez Rubio](https://davru.dev)

