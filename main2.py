import os
import time
import logging
import ollama
import requests
import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
HISTORIAL_ARCHIVO = "conversacion_historial.txt"

def get_updates(offset: int = None) -> Dict:
    """Obtiene actualizaciones del bot de Telegram."""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 100}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error al obtener actualizaciones: {e}")
        return {"ok": False}

def send_message(chat_id: int, text: str) -> Dict:
    """Envía un mensaje a través del bot de Telegram."""
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error al enviar mensaje: {e}")
        return {"ok": False}

def send_typing_action(chat_id: int) -> None:
    """Envía la acción de 'escribiendo...' al chat."""
    url = f"{BASE_URL}/sendChatAction"
    data = {
        "chat_id": chat_id,
        "action": "typing"
    }
    try:
        requests.post(url, json=data)
    except Exception as e:
        logger.error(f"Error al enviar acción de typing: {e}")

def guardar_mensaje(mensaje: str) -> None:
    """Guarda un mensaje en el archivo de historial."""
    try:
        with open(HISTORIAL_ARCHIVO, 'a', encoding='utf-8') as f:
            f.write(f"{mensaje}\n")
    except Exception as e:
        logger.error(f"Error al guardar mensaje: {e}")

def leer_historial() -> str:
    """Lee el historial de conversaciones."""
    try:
        with open(HISTORIAL_ARCHIVO, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.error(f"Error al leer historial: {e}")
        return ""

def gestionar_conversacion(mensaje: str, modelo: str = "llama3.2") -> str:
    """Gestiona una conversación con el LLM usando el historial."""
    try:
        # Leer historial existente
        historial = leer_historial()
        
        # Construir el contexto completo
        contexto_completo = f"""
{historial}
{mensaje}"""
        
        # Obtener respuesta del modelo
        respuesta = ollama.chat(
            model=modelo,
            messages=[{
                "role": "user",
                "content": contexto_completo
            }]
        )
        
        contenido_respuesta = respuesta['message']['content']
        
        # Guardar tanto el mensaje como la respuesta
        guardar_mensaje(mensaje)
        guardar_mensaje(contenido_respuesta)
        
        return contenido_respuesta
    
    except Exception as e:
        error_msg = f"Error al interactuar con el modelo: {str(e)}"
        logger.error(error_msg)
        return error_msg

def reset_historial() -> bool:
    """Borra el historial de conversaciones."""
    try:
        if os.path.exists(HISTORIAL_ARCHIVO):
            os.remove(HISTORIAL_ARCHIVO)
        return True
    except Exception as e:
        logger.error(f"Error al borrar historial: {e}")
        return False

def manejar_comando(chat_id: int, comando: str) -> None:
    """Maneja los comandos del bot."""
    if comando == "/start":
        mensaje = """
¡Hola! Soy un bot que utiliza LLama 3.2 para chatear. 
Mantengo un historial compartido de todas las conversaciones.

Comandos disponibles:
/start - Muestra este mensaje de bienvenida
/help - Muestra la ayuda
/reset - Borra todo el historial de conversaciones
/modelo - Muestra el modelo actual en uso

¡Escribe cualquier mensaje para comenzar a chatear!
"""
        send_message(chat_id, mensaje)
    
    elif comando == "/help":
        send_message(chat_id, "Envía cualquier mensaje y chatearé contigo usando LLama 3.2. El historial es compartido entre todos los usuarios.")
    
    elif comando == "/reset":
        if reset_historial():
            send_message(chat_id, "¡Historial borrado! Empecemos de nuevo.")
        else:
            send_message(chat_id, "Error al borrar el historial.")
    
    elif comando == "/modelo":
        send_message(chat_id, "Usando modelo: llama2:3.2")

def main():
    """Función principal que ejecuta el bot."""
    logger.info("Iniciando bot...")
    
    if not TELEGRAM_TOKEN:
        logger.error("No se encontró el token de Telegram en las variables de entorno")
        return

    try:
        ollama.list()
        logger.info("Conexión con Ollama establecida correctamente")
    except Exception as e:
        logger.error(f"Error: No se puede conectar con Ollama. Error: {e}")
        return

    offset = None

    while True:
        try:
            updates = get_updates(offset)
            
            if updates.get("ok"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" not in update:
                        continue
                        
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    
                    if "text" not in message:
                        send_message(chat_id, "Por favor, envía solo mensajes de texto.")
                        continue
                        
                    texto = message["text"]
                    
                    if texto.startswith("/"):
                        manejar_comando(chat_id, texto)
                        continue
                    
                    send_typing_action(chat_id)
                    respuesta = gestionar_conversacion(texto)
                    
                    if len(respuesta) > 4000:
                        for i in range(0, len(respuesta), 4000):
                            send_message(chat_id, respuesta[i:i+4000])
                    else:
                        send_message(chat_id, respuesta)
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en el bucle principal: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()