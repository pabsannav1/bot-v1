import ollama
import datetime
from typing import Optional, Dict, Any

def guardar_conversacion(archivo: str, rol: str, mensaje: str) -> None:
    """Guarda una nueva interacción en el archivo de historial."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(archivo, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {rol}: {mensaje}\n")

def leer_historial(archivo: str) -> str:
    """Lee todo el historial de conversaciones."""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def gestionar_conversacion(prompt: str, archivo_historial: str = "conversacion_historial.txt", modelo: str = "llama3.2") -> str:
    """
    Gestiona una conversación con el LLM, guardando el historial y usándolo como contexto.
    
    Args:
        prompt: El mensaje del usuario
        archivo_historial: Ruta al archivo donde se guarda el historial
        modelo: El modelo de Ollama a usar
    Returns:
        La respuesta del modelo
    """
    # Leer el historial existente
    historial = leer_historial(archivo_historial)
    
    # Construir el contexto completo
    contexto_completo = f"""
    Historial de la conversación:
    {historial}
    
    Usuario actual: {prompt}
    
    Por favor, responde al último mensaje del usuario teniendo en cuenta el contexto anterior.
    """
    
    try:
        # Obtener respuesta del modelo usando el contexto
        respuesta = ollama.chat(model=modelo, messages=[
            {
                'role': 'user',
                'content': contexto_completo
            }
        ])
        
        contenido_respuesta = respuesta['message']['content']
        
        # Guardar la nueva interacción
        guardar_conversacion(archivo_historial, "Usuario", prompt)
        guardar_conversacion(archivo_historial, "Asistente", contenido_respuesta)
        
        return contenido_respuesta
    
    except Exception as e:
        error_msg = f"Error al interactuar con el modelo: {str(e)}"
        print(error_msg)
        return error_msg

def main():
    """Función principal que ejecuta el bucle de conversación."""
    print("¡Bienvenido al chat con LLama 3.2!")
    print("Escribe 'salir' para terminar la conversación")
    
    # Verificar que podemos conectar con el modelo
    try:
        ollama.list()
        print("Conexión con Ollama establecida correctamente")
    except Exception as e:
        print(f"Error: No se puede conectar con Ollama. Error: {e}")
        return
    
    while True:
        try:
            entrada_usuario = input("\nTú: ").strip()
            if entrada_usuario.lower() in ['salir', 'exit', 'quit']:
                print("¡Hasta luego!")
                break
            
            if not entrada_usuario:
                print("Por favor, escribe un mensaje.")
                continue
                
            print("\nProcesando...")
            respuesta = gestionar_conversacion(entrada_usuario)
            print(f"\nAsistente: {respuesta}")
            
        except KeyboardInterrupt:
            print("\n\nSesión terminada por el usuario.")
            break
        except Exception as e:
            print(f"\nError inesperado: {e}")
            print("Intenta de nuevo o escribe 'salir' para terminar.")

if __name__ == "__main__":
    main()