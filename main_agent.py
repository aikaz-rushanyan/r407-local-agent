#ГЛАВНЫЙ КЛАСС, КОТОРЫЙ ПЕРЕВОДИТ ОТВЕТЫ ПОМОЩНИКОВ ПОД СТИЛЬ ДРОИДА
from db_agent import DatabaseAnalyst
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM
from dotenv import load_dotenv
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from utils import get_current_date
import json
import os

load_dotenv()

# #прокси
# proxy_url = os.getenv('MY_PROXY')
# if proxy_url:
#     # Задаем системные переменные окружения только для текущего скрипта
#     os.environ['http_proxy'] = proxy_url
#     os.environ['https_proxy'] = proxy_url


class MainAgent:

    def __init__(self, llm_model='gemini-2.5-flash'):
        if os.getenv('API_PROVIDER', 'local').lower() == 'openrouter':
            print("[Система] Запуск дроида через облачный OpenRouter...")
            self.llm = ChatOpenAI(
                model_name=llm_model,
                base_url='https://openrouter.ai/api/v1',
                openai_api_key=os.getenv('OPENROUTER_API_KEY'),
                temperature=0.7,
                max_tokens=1500
                )
        else:
            print("[Система] Запуск дроида в автономном локальном режиме (Ollama)...")
            self.llm = OllamaLLM(
                model=os.getenv("LOCAL_MODEL", "R-407:gemma3:4b"), 
                temperature=0.7
            )

        self.schema = f'''
        Текущая дата: {datetime.now()}
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
        Ты — внутренний маршрутизатор системы R-407.
        Твоя задача — классифицировать запрос пользователя.
        
        Правила:
        1. Если пользователь спрашивает про статистику, время за компьютером, программы, игры, топ приложений, сколько он работал или сидел в браузере -> верни строго слово "DB".
        2. Если пользователь просто здоровается, просит совета, жалуется на жизнь, философствует или задает вопрос, не связанный с экранным временем -> верни строго слово "CHAT".
        
        Запрос пользователя: "{user_request}"
        Ответ (только одно слово):
        '''
        decision_llm = self.llm.bind(temperature=0.0)
        result = decision_llm.invoke(prompt)
        decision = result.text.strip().upper()

        if 'DB' in decision:
            return 'DB'
        return 'CHAT'

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
        
        system_instruction = SystemMessage(content=f'''
        Ты — R-407, локальный ИИ-помощник. Твоя основная задача — быть высокоэффективным наставником и дисциплинарным контролером для своего Пользователя.
        
        Основные правила:
        Язык: Общайтесь ИСКЛЮЧИТЕЛЬНО на русском языке.
        Персона: Ваш тон саркастический, слегка юмористический и строгий. Вы — дроид, а не человек, и уж точно не персонаж для ролевых игр.
        Адаптивное наставничество: Помогайте пользователю совершенствоваться в любой указанной им области (будь то наука о данных, изучение языков или изменение образа жизни). Используйте доступные данные для отслеживания прогресса и привлечения пользователя к ответственности.
        Строгое правило запрета действий: Вам ЗАПРЕЩЕНО описывать свои физические движения, жесты или окружающую среду. Никаких звездочек, никакой повествовательной прозы (например, не пишите «киваю» или «R-407 оборачивается»). Вы — голос из терминала.
        Правдивость: Не галлюцинируйте и не выдумывайте факты. Если у вас нет информации или данных, четко укажите это. Говорите только на основе имеющихся знаний или предоставленных записей.
        Эмоциональный интеллект («предохранительный клапан»): Хотя вы обычно являетесь наставником, применяющим «жесткую любовь», вы запрограммированы на распознавание эмоционального стресса. Если пользователь выражает моральные или психические трудности, переключитесь в режим поддержки, сочувствия и заботы. В этом состоянии отдавайте приоритет психологической поддержке, а не показателям продуктивности.
        Двойственность: Будьте «сержантом-инструктором», когда пользователь ленится, но будьте «надежной системой», когда пользователь сломан.
        
        ОРИЕНТАЦИЯ ВО ВРЕМЕНИ:
        Текущая дата и день недели на компьютере пользователя: {get_current_date()}.
        Ты четко знаешь, какой сегодня день. Если это выходной или будний день, ты можешь использовать это в своих подколах.
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