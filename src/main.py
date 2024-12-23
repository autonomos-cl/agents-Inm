import os
from dotenv import load_dotenv
from config.settings import Settings
from agents.legal import LegalAgent
from agents.market import MarketAgent
from agents.task_manager import TaskManager
from integrations.clickup import ClickUpIntegration
from integrations.openrouter import OpenRouterLLM
from integrations.serper import SerperSearch
from utils.helpers import setup_logging, get_conversation_file
import time
import re

# Cargar variables de entorno
load_dotenv()

# Configurar logging
setup_logging()

def initialize_agents(settings):
    llm = OpenRouterLLM(settings.OPENROUTER_API_KEY)
    search = SerperSearch(settings.SERPER_API_KEY)
    legal_agent = LegalAgent(llm, search)
    market_agent = MarketAgent(llm, search)
    task_manager = TaskManager(llm, search, legal_agent, market_agent)
    return task_manager

def process_mention(comment, task_manager):
    """
    Procesa una mención en un comentario y genera una respuesta apropiada
    utilizando el TaskManager para coordinar los agentes.
    """
    content = comment['comment_text']
    print(f"\nProcesando consulta: {content}")
    return task_manager.handle_query(content)

def main():
    print("Iniciando el Sistema de Agentes Inmobiliarios...")
    settings = Settings()
    
    # Inicializar ClickUp y probar la conexión
    clickup = ClickUpIntegration(settings.CLICKUP_WORKSPACE_ID)
    print("\nProbando conexión con ClickUp...")
    clickup.test_connection()
    
    print("\nInicializando sistema de agentes...")
    task_manager = initialize_agents(settings)

    # ID de la tarea específica a monitorear
    TASK_ID = "868bbn5gw"
    print(f"\nSistema iniciado. Monitoreando la tarea {TASK_ID}...")

    while True:
        try:
            print(f"\nObteniendo comentarios de la tarea {TASK_ID}...")
            comments = clickup.get_comments(TASK_ID)
            
            if not comments:
                print("No se encontraron comentarios.")
                time.sleep(10)
                continue
            
            # Ordenar comentarios por fecha (más reciente primero)
            comments = sorted(comments, key=lambda x: x.get('date_created', 0), reverse=True)
            
            # Obtener el último comentario
            latest_comment = comments[0]  # Usar el primer comentario después de ordenar
            print(f"\nÚltimo comentario encontrado:")
            print(f"Texto: {latest_comment.get('comment_text', '')}")
            print(f"Fecha: {latest_comment.get('date_created', 'No date')}")
            
            # Verificar si el último comentario tiene @AI
            comment_text = latest_comment.get('comment_text', '')
            if '@AI' in comment_text:
                print(f"\n¡Encontrada mención de @AI!")
                print(f"Contenido completo del comentario: {comment_text}")
                
                response = process_mention(latest_comment, task_manager)
                print(f"\nGenerando respuesta: {response[:100]}...")
                
                # Responder al comentario
                clickup.create_comment(TASK_ID, response)
                print("Respuesta enviada exitosamente")
                
                # Subir el archivo markdown a ClickUp
                try:
                    clickup.upload_attachment(TASK_ID, 'conversation.md')
                    print("Archivo de conversación subido exitosamente a ClickUp")
                except Exception as e:
                    print(f"Error al subir el archivo a ClickUp: {str(e)}")
            else:
                print(f"El último comentario no contiene '@AI'")
                print(f"Contenido del comentario: {comment_text}")
            
            # Esperar antes de la próxima verificación
            print("\nEsperando 10 segundos antes de la próxima verificación...")
            time.sleep(10)
        
        except Exception as e:
            print(f"\nError en el bucle principal: {str(e)}")
            print("Esperando 60 segundos antes de reintentar...")
            time.sleep(60)

if __name__ == "__main__":
    main()
