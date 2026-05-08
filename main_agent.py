from db_agent import DatabaseAnalyst
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
import os
#ГЛАВНЫЙ КЛАСС, КОТОРЫЙ ПЕРЕВОДИТ ОТВЕТЫ ПОМОЩНИКОВ ПОД СТИЛЬ ДРОИДА

load_dotenv()

#прокси
proxy_url = os.getenv('MY_PROXY')
if proxy_url:
    # Задаем системные переменные окружения только для текущего скрипта
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url


class MainAgent:
    llm: str

    def __init__(self, llm_model='gemini-3-flash-preview'):
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            temperature=0.7,
            api_key=os.getenv('GEMINI_API_KEY')
            )

    def answer(self, user_request: str, db_data):
        
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