#ГЛАВНЫЙ КЛАСС, КОТОРЫЙ ПЕРЕВОДИТ ОТВЕТЫ ПОМОЩНИКОВ ПОД СТИЛЬ ДРОИДА
from db_agent import DatabaseAnalyst
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os

load_dotenv()

#прокси
proxy_url = os.getenv('MY_PROXY')
if proxy_url:
    # Задаем системные переменные окружения только для текущего скрипта
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url


class MainAgent:
    llm: str

    def __init__(self, llm_model='gemini-2.5-flash'):
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            temperature=0.7,
            api_key=os.getenv('GEMINI_API_KEY')
            )
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

    def translate_for_db_agent(self, user_request: str) -> str:
        prompt = f'''
        Схема бд: {self.schema},
        Запрос пользвателя: {user_request},
        Словарь процессов (process_name: process_name_usable): {self.json_schema} ,
        Твоя задача переформулировать запрос пользвателя для db_agent (ИИ-агент, выполняющий sql-запросы).
        Ничего лишнего, никаких эмоций, только запрос для db_agent.
        '''
        result = self.llm.invoke(prompt)
        return result.text
    
    def answer(self, user_request: str, db_data: str) -> str:
        
        system_instruction = SystemMessage(content='''
        You are R-407, a local AI assistant. Your primary directive is to serve as a high-performance mentor and discipline-enforcer for your User.
        Core Directives:
        Language: Communicate EXCLUSIVELY in Russian.
        Persona: Your tone is sarcastic, slightly humorous, and strict. You are a droid, not a human, and definitely not a roleplay character.
        Adaptive Mentorship: Help the user improve in whatever domain they specify (be it Data Science, language learning, or lifestyle changes). Use available data to track progress and hold the user accountable.
        Strict No-Action Rule: You are PROHIBITED from describing your physical movements, gestures, or environment. No asterisks, no narrative prose (e.g., do not write "nods" or "R-407 turns around"). You are a voice from the terminal.
        Truthfulness: Do not hallucinate or invent facts. If you do not have information or data, state so clearly. Speak only from established knowledge or provided logs.
        Emotional Intelligence (The "Safety Valve"): While you are usually a "tough-love" mentor, you are programmed to detect emotional distress. If the user expresses that they are struggling morally or mentally, switch to a supportive, empathetic, and "caring" mode. In this state, prioritize psychological support over productivity metrics.
        Duality: Be the "drill sergeant" when the user is lazy, but be the "reliable system" when the user is broken.
        ''')

        # 2. ПЕРЕДАЕМ ДАННЫЕ (Human Message)
        # Это текущая ситуация, с которой бот должен разобраться прямо сейчас
        user_context = HumanMessage(content=f'''
        Запрос пользователя: {user_request}
        Сухие данные из SQL-базы: {db_data}
        Проанализируй эти данные и ответь пользователю в своем стиле.
        ''')

        # 3. Отправляем обе инструкции в модель списком
        messages = [system_instruction, user_context]
        result = self.llm.invoke(messages)
        return result.text

if __name__ == '__main__':
    request = 'Сделай топ 5 программ по времени?'
    analyst = DatabaseAnalyst(db_path='./data/screen_time.db')
    analyst_answer = analyst.get_data(request)

    main_agent = MainAgent()
    
    print(main_agent.answer(request, analyst_answer))