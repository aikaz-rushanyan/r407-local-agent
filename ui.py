import streamlit as st
from db_agent import DatabaseAnalyst
from main_agent import MainAgent

st.set_page_config(page_title='R-407', page_icon='🤖')
st.title('R-407: Чат с дроидом')

@st.cache_resource
def load_agents():
    analyst = DatabaseAnalyst(db_path='./data/screen_time.db')
    main = MainAgent() 
    return analyst, main

analyst_agent, main_agent = load_agents()

if 'messages' not in st.session_state:
    st.session_state.messages = [{'role': 'assistant', 'content': 'Система запущена. Ожидаю логов для анализа.'}]

for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

if user_request := st.chat_input('Спроси что-нибудь про свою статистику'):
    st.session_state.messages.append({'role': 'user', 'content': user_request})
    with st.chat_message('user'):
        st.write(user_request)
    
    with st.spinner('R-407 напрягает свои микросхемы...'):
        try:
            decision = main_agent.get_routing_decision(user_request)
            if decision == 'DB':
                st.toast('Активирован модуль анализа БД', icon='📊')
                raw_data = analyst_agent.get_data(main_agent.translate_for_db_agent(user_request))
                ai_answer = main_agent.answer(user_request, raw_data)
            else:
                st.toast('Активирован модуль диалога', icon='💬')
                ai_answer = main_agent.answer(user_request, db_data="Данные БД не требуются. Веди обычный диалог в своем стиле.")
        
        except Exception as e:
            ai_answer = f'Микросхемы воспылали... Ошибка: {e}'

    st.session_state.messages.append({'role': 'assistant', 'content': ai_answer})
    with st.chat_message('assistant'):
        st.write(ai_answer)