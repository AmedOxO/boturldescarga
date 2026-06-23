import os
import sys
import subprocess

# Matar procesos de Python antes de iniciar
print("🔍 Verificando procesos...")
os.system("taskkill /F /IM python.exe 2>nul")
print("✅ Procesos eliminados")

# Ejecutar el bot
print("🚀 Iniciando bot...")
os.system("python bot.py")