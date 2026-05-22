from db_agent import DatabaseAnalyst
from langchain_ollama import OllamaLLM
import json
import subprocess
from datetime import datetime
#ГЛАВНЫЙ КЛАСС, КОТОРЫЙ ПЕРЕВОДИТ ОТВЕТЫ ПОМОЩНИКОВ ПОД СТИЛЬ ДРОИДА

# try:
#     ollama_list = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True).stdout.strip().split('\n')[1:]
# except subprocess.CalledProcessError as e:
#     print(f"Ошибка выполнения команды: {e}")
# except FileNotFoundError:
#     print("Ошибка: Утилита Ollama не установлена или не добавлена в PATH вашей системы.")

class MainAgent:

    def __init__(self, llm_model='R-407-gemma3:4b'):
        self.llm = OllamaLLM(model=llm_model, temperature=0.7)
        self.schema = '''
        имя db-файла: screen_time.db
        Таблица: screen_time_log
        Колонки: id, 
                 process_name (названия процессов из диспетчера задач), 
                 process_name_usable (названия программ), 
                 window_title (названия окон, в браузерах  это имена вкладок, сайтов), 
                 start_time (когда открыто была программа), 
                 end_time (когда закрыта была программа), 
                 duration_seconds (длительность в секундах)
        '''

        try:
            with open('config/process_names.json', 'r', encoding='utf-8') as f:
                self.json_schema = json.dumps(json.load(f), ensure_ascii=False, indent=4)
        except FileNotFoundError:
            self.json_schema = 'Словарь процессов не найден.'

    def get_routing_decision(self, user_request):
        """Выбор маршрута: SQL или диалог"""
        prompt = f'''
        Твоя задача — классифицировать запрос пользователя.
        
        Правила:
        1. Если пользователь спрашивает про статистику, время за компьютером, программы, игры, топ приложений, сколько он работал или сидел в браузере -> верни строго слово "DB".
        2. Если пользователь просто здоровается, просит совета, жалуется на жизнь, философствует или задает вопрос, не связанный с экранным временем -> верни строго слово "CHAT".

        Запрос пользователя: "{user_request}"
        Ответ (только одно слово):
        '''
        decision_llm = OllamaLLM(model="R-407-gemma3:4b", temperature=0.0)
        result = decision_llm.invoke(prompt)
        decision = result.strip().upper()

        if 'DB' in decision:
            return 'DB'
        return 'CHAT'

    def translate_for_db_agent(self, user_request):
        prompt = f'''
        Схема бд: {self.schema},
        Запрос пользвателя: {user_request},
        Словарь процессов (process_name: process_name_usable): {self.json_schema} ,
        Твоя задача переформулировать запрос пользвателя для db_agent (ИИ-агент, выполняющий sql-запросы).
        Проси информацию за {datetime.now().year} год.
        Ничего лишнего, никаких эмоций, только запрос для db_agent.
        '''
        result = self.llm.invoke(prompt)
        return result
    
    def answer(self, user_request, db_data):
        prompt = f'''
        Пользователь спросил: {user_request}
        Ответ от sql-агента: {db_data}
        Твоя задача переписать ответ под стиль R-407 для пользователя.
        '''
        result = self.llm.invoke(prompt)
        return result

if __name__ == '__main__':
    agent = MainAgent()
    result = agent.answer('здарова бро', 'Данные не требуются для ответа.')
    print(result)