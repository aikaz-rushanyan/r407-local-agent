#КЛАСС ДЛЯ ОБРАБОТКИ ЗАПРОСОВ БЕРУЩИХ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ
import sqlite3
from dotenv import load_dotenv
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM
from datetime import datetime
from utils import get_current_date
import os

load_dotenv()

# proxy_url = os.getenv('MY_PROXY')
# if proxy_url:
#     # Задаем системные переменные окружения только для текущего скрипта
#     os.environ['http_proxy'] = proxy_url
#     os.environ['https_proxy'] = proxy_url

class DatabaseAnalyst:

    def __init__(self, db_path):

        if os.getenv('API_PROVIDER', 'local').lower() == 'openrouter':
            print("[Система] Запуск SQL-дроида через облачный OpenRouter...")
            self.llm = ChatOpenAI(
                model_name=os.getenv('API_DB_AGENT', 'openrouter/owl-alpha'),
                base_url='https://openrouter.ai/api/v1',
                openai_api_key=os.getenv('OPENROUTER_API_KEY'),
                temperature=0.0,
                max_tokens=1500
                )
        else:
            print("[Система] Запуск SQL-дроида в автономном локальном режиме (Ollama)...")
            self.llm = OllamaLLM(
                model=os.getenv("LOCAL_DB_AGENT", "R-407-gemma3:4b"), 
                temperature=0.0
            )
        self.db_path=db_path
        self.schema = f'''
        Текущая дата: {datetime.now()}
        Таблица: screen_time_log
        Колонки: id, 
                 process_name (названия из диспетчера задач), 
                 process_name_usable (названия программ), 
                 window_title (названия окон, в браузерах это имена вкладок, сайтов), 
                 start_time, 
                 end_time, 
                 duration_seconds (длительность в секундах)
        '''

    def _generate(self, user_request):
        prompt = f'''
        Схема: {self.schema}
        Запрос пользователя: {user_request}
        
        ВРЕМЕННОЙ КОНТЕКСТ:
        Сегодняшняя дата и день недели: {get_current_date()}
        Используй эту дату для вычисления относительных временных промежутков (сегодня, вчера, 3 дня назад, эти выходные).
        
        Ты — опытный инженер данных и специалист по SQLite. Твоя задача — переводить текстовые запросы пользователя в один валидный SQL-запрос.
        ПРАВИЛО АРХИТЕКТУРЫ:
        Если запрос пользователя требует сравнения разных категорий данных, вычисления нескольких метрик одновременно или пошаговой фильтрации, ты ОБЯЗАН использовать обобщенные табличные выражения CTE (оператор WITH ... AS ...). 
        Запрещено генерировать несколько отдельных запросов. Результатом твоей работы должен быть только один финальный SQL-скрипт.
        
        Верни ТОЛЬКО валидный SQLite запрос. Никакого текста.
        '''
        raw = self.llm.invoke(prompt)
        res_text = raw.content if hasattr(raw, 'content') else raw
        return res_text.replace('```', '').replace('sqlite', '').replace('sql', '').strip()
        
    def get_data(self, user_request):
        sql_query = self._generate(user_request)
        print(f"[Аналитик] Выполняю запрос:\n{sql_query}")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            return f'Какая-то ошибка в БД!!!, {e}'
        
