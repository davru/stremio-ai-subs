#!/bin/bash
set -e

# Nombre del entorno virtual
VENV_NAME="venv"

echo "🚀 Iniciando OpenSubtitles Generator..."

# 1. Crear entorno virtual si no existe
if [ ! -d "$VENV_NAME" ]; then
    echo "📦 Creando entorno virtual ($VENV_NAME)..."
    python3 -m venv "$VENV_NAME"
fi

# 2. Activar entorno virtual
source "$VENV_NAME/bin/activate"

# 3. Instalar dependencias
echo "⬇️  Instalando/Actualizando dependencias..."
pip install -r requirements.txt

# 4. Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️  AVISO: No se encontró el archivo .env"
    echo "📄 Intentando crear copia desde .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Archivo .env creado. POR FAVOR, EDÍTALO CON TUS CLAVES."
        echo "   La aplicación puede fallar si no configuras las API KEYS."
        # No detenemos el script, pero avisamos.
    else
        echo "❌ Error: No existe .env.example para copiar."
    fi
fi

# 5. Iniciar servidor
echo "🟢 Servidor iniciado en http://localhost:8000"
echo "   Presiona CTRL+C para detener."
uvicorn app.main:app --reload
