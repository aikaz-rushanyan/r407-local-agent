from db_agent import DatabaseAnalyst
from langchain_ollama import OllamaLLM

'ГЛАВНЫЙ КЛАСС, КОТОРЫЙ ПЕРЕВОДИТ ОТВЕТЫ ПОМОЩНИКОВ ПОД СТИЛЬ ДРОИДА'

class MainAgent:
    llm: str

    def __init__(self, llm_model='R-407'):
        self.llm = OllamaLLM(model=llm_model, temperature=0.7)

    def answer(self, user_request: str, db_data):
        prompt = f'''
        Пользователь спросил: {user_request}
        Ответ от sql-агента: {db_data}
        Твоя задача переписать ответ под свой стиль для пользователя.
        '''
        result = self.llm.invoke(prompt)
        return result

if __name__ == '__main__':
    request = 'Сделай топ 5 программ по времени?'
    analyst = DatabaseAnalyst(db_path='./data/screen_time.db')
    analyst_answer = analyst.get_data(request)

    main_agent = MainAgent()
    
    print(main_agent.answer(request, analyst_answer))