#!/bin/bash
set -e  # Salir si hay algún error

echo "=== INICIO DEL BUILD ==="
echo "Python version:"
python --version

echo "Pip version:"
pip --version

echo "=== VERIFICANDO REQUIREMENTS.TXT ==="
echo "Contenido de requirements.txt:"
cat requirements.txt
echo "---"

echo "¿Existe requirements.txt?"
ls -la requirements.txt

echo "=== INSTALANDO DEPENDENCIAS MANUALMENTE ==="
echo "Instalando Flask..."
pip install Flask==2.3.3

echo "Instalando requests..."
pip install requests==2.31.0

echo "Instalando gunicorn..."
pip install gunicorn==21.2.0

echo "=== VERIFICANDO INSTALACIONES ==="
echo "Packages installed:"
pip list

echo "=== VERIFICANDO FLASK ESPECÍFICAMENTE ==="
python -c "import flask; print('Flask version:', flask.__version__)"

echo "=== ESTRUCTURA DE ARCHIVOS ==="
ls -la

echo "=== BUILD COMPLETADO EXITOSAMENTE ==="