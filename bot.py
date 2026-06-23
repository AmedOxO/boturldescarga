import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sys

# --- CONFIGURACION ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8838129848:AAEoYT1heMVSn-PIBrT_WwHaZnDMvvAZ74A'

# Crear carpeta para descargas
if not os.path.exists('descargas'):
    os.makedirs('descargas')

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archivos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  file_id TEXT,
                  file_name TEXT,
                  file_type TEXT,
                  file_size INTEGER,
                  fecha TEXT)''')
    conn.commit()
    conn.close()
    logger.info("📁 Base de datos inicializada")

def guardar_archivo(user_id, file_id, file_name, file_type, file_size):
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO archivos (user_id, file_id, file_name, file_type, file_size, fecha)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, file_id, file_name, file_type, file_size, fecha))
    conn.commit()
    # Obtener el ID del registro insertado
    registro_id = c.lastrowid
    conn.close()
    return registro_id

def obtener_archivos(user_id):
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    c.execute('''SELECT id, file_name, file_id, file_type, file_size, fecha 
                 FROM archivos WHERE user_id = ? ORDER BY fecha DESC''',
              (user_id,))
    archivos = c.fetchall()
    conn.close()
    return archivos

def eliminar_archivo(user_id, registro_id):
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    c.execute('''DELETE FROM archivos 
                 WHERE user_id = ? AND id = ?''',
              (user_id, registro_id))
    conn.commit()
    conn.close()
    return c.rowcount > 0

def obtener_archivo_por_id(user_id, registro_id):
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    c.execute('''SELECT file_name, file_type, file_id FROM archivos 
                 WHERE user_id = ? AND id = ?''',
              (user_id, registro_id))
    resultado = c.fetchone()
    conn.close()
    return resultado

def obtener_archivo_por_file_id(user_id, file_id):
    conn = sqlite3.connect('archivos.db')
    c = conn.cursor()
    c.execute('''SELECT id, file_name, file_type, file_id FROM archivos 
                 WHERE user_id = ? AND file_id = ?''',
              (user_id, file_id))
    resultado = c.fetchone()
    conn.close()
    return resultado

# --- COMANDOS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🎉 **¡Bienvenido {user.first_name}!**

Soy tu bot de almacenamiento en la nube de Telegram.

📤 **¿Qué puedo hacer?**
✅ Guardar archivos en la nube
✅ Descargar archivos cuando quieras
✅ Eliminar archivos que no necesites
✅ Ver todos tus archivos organizados

📋 **Comandos rápidos:**
/start - Ver este mensaje
/menu - Abrir el menú principal
/list - Ver mis archivos
/ayuda - Obtener ayuda
/eliminar [ID] - Eliminar un archivo
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    keyboard = [
        [InlineKeyboardButton("📂 Ver archivos", callback_data='list')],
        [InlineKeyboardButton("📤 Subir archivo", callback_data='upload')],
        [InlineKeyboardButton("❓ Ayuda", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚡ **Acceso rápido:**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 Ver mis archivos", callback_data='list')],
        [InlineKeyboardButton("📤 Subir archivo", callback_data='upload')],
        [InlineKeyboardButton("❓ Ayuda", callback_data='help')],
        [InlineKeyboardButton("ℹ️ Información", callback_data='info')],
        [InlineKeyboardButton("🗑️ Eliminar archivo", callback_data='delete_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 **MENÚ PRINCIPAL**\n\n"
        "Selecciona una opción:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **GUÍA DE USO**

📤 **Subir archivos:**
• Envía cualquier archivo al chat
• Se guardará automáticamente

📂 **Ver archivos:**
• Usa /list o el botón "Ver archivos"
• Verás lista con botones de acción

📥 **Descargar archivos:**
• En la lista, haz clic en "📥 Descargar"
• El archivo se enviará al chat

🗑️ **Eliminar archivos:**
• En la lista, haz clic en "🗑️ Eliminar"
• O usa /eliminar [ID]

⚡ **Comandos rápidos:**
/start - Inicio
/menu - Menú principal
/list - Ver archivos
/ayuda - Esta ayuda
/eliminar [ID] - Eliminar archivo

💾 **Almacenamiento:**
Los archivos se guardan en la nube de Telegram
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    archivos = obtener_archivos(user_id)
    
    if not archivos:
        keyboard = [[InlineKeyboardButton("📤 Subir archivo", callback_data='upload')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📂 **No tienes archivos guardados aún.**\n\n"
            "Envía un archivo o presiona el botón:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    for i, (id_reg, nombre, file_id, tipo, tamaño, fecha) in enumerate(archivos, 1):
        emoji = {
            'video': '🎬', 'foto': '📸', 'documento': '📄',
            'audio': '🎵', 'mensaje_voz': '🎤'
        }.get(tipo, '📎')
        
        if tamaño:
            if tamaño < 1024:
                size_str = f"{tamaño} B"
            elif tamaño < 1024 * 1024:
                size_str = f"{tamaño / 1024:.1f} KB"
            else:
                size_str = f"{tamaño / (1024 * 1024):.1f} MB"
        else:
            size_str = "desconocido"
        
        # Usar el ID numérico de la base de datos para los botones
        keyboard = [
            [
                InlineKeyboardButton("📥 Descargar", callback_data=f'down_{id_reg}'),
                InlineKeyboardButton("🗑️ Eliminar", callback_data=f'del_{id_reg}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mensaje = f"""
{emoji} **{i}. {nombre}**
📁 Tipo: {tipo}
📊 Tamaño: {size_str}
📅 Fecha: {fecha}
🆔 ID: `{id_reg}`
"""
        try:
            await update.message.reply_text(
                mensaje,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error al mostrar archivo: {e}")
    
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📊 **Fin de la lista**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def delete_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ **Uso incorrecto.**\n\n"
            "Formato: `/eliminar ID_NUMERICO`\n"
            "Ejemplo: `/eliminar 5`\n\n"
            "Usa /list para ver los IDs numéricos.",
            parse_mode='Markdown'
        )
        return
    
    try:
        registro_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ **ID inválido.**\n"
            "El ID debe ser un número.\n"
            "Usa /list para ver los IDs.",
            parse_mode='Markdown'
        )
        return
    
    user_id = update.effective_user.id
    
    if eliminar_archivo(user_id, registro_id):
        await update.message.reply_text(
            "🗑️ **Archivo eliminado con éxito.**",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ **Archivo no encontrado.**\n"
            "Verifica el ID y vuelve a intentar.",
            parse_mode='Markdown'
        )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        if update.message.document:
            file = update.message.document
            file_type = "documento"
            nombre = file.file_name or "documento.pdf"
            file_size = file.file_size or 0
        elif update.message.video:
            file = update.message.video
            file_type = "video"
            nombre = file.file_name or "video.mp4"
            file_size = file.file_size or 0
        elif update.message.photo:
            file = update.message.photo[-1]
            file_type = "foto"
            nombre = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            file_size = file.file_size or 0
        elif update.message.audio:
            file = update.message.audio
            file_type = "audio"
            nombre = file.file_name or "audio.mp3"
            file_size = file.file_size or 0
        elif update.message.voice:
            file = update.message.voice
            file_type = "mensaje_voz"
            nombre = f"voz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
            file_size = file.file_size or 0
        else:
            await update.message.reply_text(
                "❌ **Tipo de archivo no soportado.**\n\n"
                "📤 Envía: videos, fotos, documentos o audios.",
                parse_mode='Markdown'
            )
            return
        
        file_id = file.file_id
        
        # Guardar en la base de datos y obtener el ID numérico
        registro_id = guardar_archivo(user_id, file_id, nombre, file_type, file_size)
        
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        # Usar el ID numérico para los botones
        keyboard = [
            [InlineKeyboardButton("📥 Descargar", callback_data=f'down_{registro_id}')],
            [InlineKeyboardButton("📂 Ver mis archivos", callback_data='list')],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f'del_{registro_id}')],
            [InlineKeyboardButton("🔙 Menú principal", callback_data='menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mensaje_exito = (
            f"✅ **¡Archivo guardado con éxito!**\n\n"
            f"📎 **Nombre:** {nombre}\n"
            f"📁 **Tipo:** {file_type}\n"
            f"📊 **Tamaño:** {size_str}\n"
            f"💾 **Almacenado en:** Nube de Telegram\n"
            f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"🔍 **ID:** `{registro_id}`\n\n"
            f"**Acciones rápidas:**"
        )
        
        await update.message.reply_text(
            mensaje_exito,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"ERROR al procesar archivo: {e}")
        await update.message.reply_text(
            f"❌ **Error al procesar el archivo.**\n"
            f"Detalle: {str(e)[:100]}",
            parse_mode='Markdown'
        )

# --- MANEJADOR DE BOTONES ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'menu':
        keyboard = [
            [InlineKeyboardButton("📂 Ver mis archivos", callback_data='list')],
            [InlineKeyboardButton("📤 Subir archivo", callback_data='upload')],
            [InlineKeyboardButton("❓ Ayuda", callback_data='help')],
            [InlineKeyboardButton("ℹ️ Información", callback_data='info')],
            [InlineKeyboardButton("🗑️ Eliminar archivo", callback_data='delete_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎯 **MENÚ PRINCIPAL**\n\n"
            "Selecciona una opción:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == 'upload':
        await query.edit_message_text(
            "📤 **Para subir un archivo:**\n\n"
            "1. Envía el archivo directamente al chat\n"
            "2. O reenvía un archivo desde otro chat\n\n"
            "📎 **Formatos soportados:**\n"
            "• Videos 🎬\n"
            "• Fotos 📸\n"
            "• Documentos 📄\n"
            "• Audios 🎵\n"
            "• Notas de voz 🎤",
            parse_mode='Markdown'
        )
    
    elif data == 'help':
        help_text = """
📚 **GUÍA DE USO**

📤 **Subir archivos:**
• Envía cualquier archivo al chat
• Se guardará automáticamente

📂 **Ver archivos:**
• Usa /list o el botón "Ver archivos"
• Verás lista con botones de acción

📥 **Descargar archivos:**
• En la lista, haz clic en "📥 Descargar"
• El archivo se enviará al chat

🗑️ **Eliminar archivos:**
• En la lista, haz clic en "🗑️ Eliminar"
• O usa /eliminar [ID]

⚡ **Comandos rápidos:**
/start - Inicio
/menu - Menú principal
/list - Ver archivos
/ayuda - Esta ayuda
/eliminar [ID] - Eliminar archivo

💾 **Almacenamiento:**
Los archivos se guardan en la nube de Telegram
"""
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif data == 'info':
        archivos = obtener_archivos(user_id)
        total = len(archivos)
        
        info_text = f"""
ℹ️ **INFORMACIÓN DEL BOT**

📊 **Estadísticas:**
• Archivos guardados: {total}
• Usuario ID: `{user_id}`

📁 **Almacenamiento:**
• Nube de Telegram (ilimitado)
• Descarga local automática

🤖 **Versión:** 2.0
📅 **Última actualización:** {datetime.now().strftime('%d/%m/%Y')}

💡 **Comandos disponibles:**
/menu - Abrir menú
/list - Ver archivos
/ayuda - Ayuda
/eliminar - Eliminar archivo
"""
        await query.edit_message_text(info_text, parse_mode='Markdown')
    
    elif data == 'delete_menu':
        archivos = obtener_archivos(user_id)
        if not archivos:
            await query.edit_message_text(
                "📂 **No tienes archivos para eliminar.**",
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for id_reg, nombre, file_id, tipo, tamaño, fecha in archivos[:10]:
            emoji = {
                'video': '🎬', 'foto': '📸', 'documento': '📄',
                'audio': '🎵', 'mensaje_voz': '🎤'
            }.get(tipo, '📎')
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {nombre[:20]}", callback_data=f'del_{id_reg}')
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data='menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ **Selecciona el archivo a eliminar:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == 'list':
        archivos = obtener_archivos(user_id)
        if not archivos:
            await query.edit_message_text(
                "📂 **No tienes archivos guardados aún.**",
                parse_mode='Markdown'
            )
            return
        
        for id_reg, nombre, file_id, tipo, tamaño, fecha in archivos[:5]:
            emoji = {
                'video': '🎬', 'foto': '📸', 'documento': '📄',
                'audio': '🎵', 'mensaje_voz': '🎤'
            }.get(tipo, '📎')
            
            keyboard = [
                [
                    InlineKeyboardButton("📥 Descargar", callback_data=f'down_{id_reg}'),
                    InlineKeyboardButton("🗑️ Eliminar", callback_data=f'del_{id_reg}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            mensaje = f"""
{emoji} **{nombre}**
📁 Tipo: {tipo}
🆔 ID: `{id_reg}`
📅 Fecha: {fecha}
"""
            await query.message.reply_text(
                mensaje,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "📊 **Fin de la lista**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.message.delete()
    
    # DESCARGAR - Usa el ID numérico
    elif data.startswith('down_'):
        try:
            registro_id = int(data.replace('down_', ''))
        except ValueError:
            await query.edit_message_text(
                "❌ **ID inválido.**",
                parse_mode='Markdown'
            )
            return
        
        archivo = obtener_archivo_por_id(user_id, registro_id)
        
        if not archivo:
            await query.edit_message_text(
                "❌ **Archivo no encontrado.**\n"
                "Puede haber sido eliminado.",
                parse_mode='Markdown'
            )
            return
        
        nombre, tipo, file_id = archivo
        
        try:
            await query.edit_message_text(
                f"📥 **Descargando:** {nombre}\n\n"
                f"⏳ Enviando archivo...",
                parse_mode='Markdown'
            )
            
            if tipo == 'video':
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=file_id,
                    caption=f"📥 Descargado: {nombre}"
                )
            elif tipo == 'foto':
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=f"📥 Descargado: {nombre}"
                )
            elif tipo == 'documento':
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_id,
                    caption=f"📥 Descargado: {nombre}"
                )
            elif tipo == 'audio':
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=file_id,
                    caption=f"📥 Descargado: {nombre}"
                )
            else:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_id,
                    caption=f"📥 Descargado: {nombre}"
                )
            
            await query.message.reply_text(
                "✅ **Archivo enviado con éxito.**",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error al descargar: {e}")
            await query.edit_message_text(
                f"❌ **Error al descargar el archivo.**\n"
                f"Detalle: {str(e)[:100]}",
                parse_mode='Markdown'
            )
    
    # ELIMINAR - Usa el ID numérico
    elif data.startswith('del_'):
        try:
            registro_id = int(data.replace('del_', ''))
        except ValueError:
            await query.edit_message_text(
                "❌ **ID inválido.**",
                parse_mode='Markdown'
            )
            return
        
        if eliminar_archivo(user_id, registro_id):
            await query.edit_message_text(
                "🗑️ **Archivo eliminado con éxito.**",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ **Archivo no encontrado.**",
                parse_mode='Markdown'
            )

# --- FUNCION PRINCIPAL ---
def main():
    try:
        init_db()
        
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu))
        application.add_handler(CommandHandler("list", list_files))
        application.add_handler(CommandHandler("ayuda", ayuda))
        application.add_handler(CommandHandler("help", ayuda))
        application.add_handler(CommandHandler("eliminar", delete_file_command))
        
        application.add_handler(MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
            handle_file
        ))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        print("\n" + "="*60)
        print("🤖 BOT DE TELEGRAM MEJORADO")
        print("="*60)
        print("📁 Base de datos: archivos.db")
        print("📂 Carpeta descargas: descargas/")
        print("📋 Comandos: /start, /menu, /list, /ayuda, /eliminar")
        print("="*60)
        print("💡 Los archivos se guardan en la nube de Telegram")
        print("💡 Ahora usa IDs numéricos para los botones")
        print("="*60)
        print("Presiona Ctrl+C para detener.")
        print("="*60 + "\n")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
            
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario.")
    except Exception as e:
        if "Conflict" in str(e):
            print("\n" + "="*60)
            print("⚠️ CONFLICTO DETECTADO")
            print("="*60)
            print("Cerrando todas las instancias...")
            os.system("taskkill /F /IM python.exe 2>nul")
            print("Espera 3 segundos...")
            import time
            time.sleep(3)
            print("Reiniciando el bot...")
            os.system("python bot.py")
            print("="*60)
        else:
            logger.error(f"Error fatal: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()