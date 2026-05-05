import sqlite3
from langchain_ollama import OllamaLLM

#КЛАСС ДЛЯ ОБРАБОТКИ ЗАПРОСОВ БЕРУЩИХ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ

class DatabaseAnalyst:
    db_path: str
    llm: str

    def __init__(self, db_path: str, llm_model='R-407'):
        self.db_path = db_path
        self.llm = OllamaLLM(model=llm_model, temperature=0)
        self.schema = '''
        Таблица: screen_time_log
        Колонки: id, process_name, process_name_usable, window_title, start_time, end_time, duration_seconds
        '''

    def _generate(self, user_request: str):
        prompt = f'''
        Схема: {self.schema}
        Запрос пользователя: {user_request}
        Верни ТОЛЬКО валидный SQLite запрос. Никакого текста.
        '''
        raw = self.llm.invoke(prompt)
        return raw.replace('```', '').replace('sql', '')
        
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
        
