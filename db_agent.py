#КЛАСС ДЛЯ ОБРАБОТКИ ЗАПРОСОВ БЕРУЩИХ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ

import sqlite3
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os

load_dotenv()

proxy_url = os.getenv('MY_PROXY')
if proxy_url:
    # Задаем системные переменные окружения только для текущего скрипта
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url

class DatabaseAnalyst:
    db_path: str
    llm: str

    def __init__(self, db_path: str, llm_model='gemini-3-flash-preview'):
        self.db_path = db_path
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model, 
            temperature=0.7,
            api_key=os.getenv('GEMINI_API_KEY')
        )
        self.schema = '''
        Таблица: screen_time_log
        Колонки: id, 
                 process_name (названия из диспетчера задач), 
                 process_name_usable (названия программ), 
                 window_title (названия окон, в браузерах это имена вкладок, сайтов), 
                 start_time, 
                 end_time, 
                 duration_seconds (длительность в секундах)
        '''

    def _generate(self, user_request: str):
        prompt = f'''
        Схема: {self.schema}
        Запрос пользователя: {user_request}
        Верни ТОЛЬКО валидный SQLite запрос. Никакого текста.
        '''
        raw = self.llm.invoke(prompt)
        return raw.text
        #return raw.replace('```', '').replace('sql', '')
        
    def get_data(self, user_request: str):
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
            return f'Какая-то ошибка в БД!!!'
        
