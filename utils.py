from datetime import datetime
from dotenv import load_dotenv
import sqlite3
import json
import requests
import os

load_dotenv()

#СКРИПТ ДЛЯ ОБНОВЛЕНИЯ process_name_usable в screen_time.db из JSON.
def update_screen_time_log() -> None: #обновляет БД, ничего не возвращает
    #читаем актуальный JSON
    with open('config/process_names.json', 'r', encoding='utf-8') as f:
        names = json.load(f)

    #подключаемся к базе
    conn = sqlite3.connect('data/screen_time.db')
    cursor = conn.cursor()

    #проходимся по словарю и обновляем старые записи
    for raw_name, clean_name in names.items():
        cursor.execute("UPDATE screen_time_log SET process_name_usable = ? WHERE process_name = ?", (clean_name, raw_name))

    conn.commit()
    conn.close()
    print("База успешно обновлена!")

#СКРИПТ, ЧТОБЫ УЗНАТЬ ТЕКУЩУЮ ДАТУ.
def get_current_date() -> str: #выводит дату
    now = datetime.now()
    week_lst = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    current_day = week_lst[now.weekday()] 

    return f"{now.strftime('%Y-%m-%d')} ({current_day})"

#СКРИПТ ДЛЯ ОТПРАВКИ ОТЧЕТА В ТГ
def sent_tg_report():
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    db_path = 'data/screen_time.db' 
    
    if not token or not chat_id:
        print('[Ошибка] В .env не настроены токен или chat_id для Telegram!')
        print(f'TG_TOKEN: {token}\nTG_CHAT_ID: {chat_id}')
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT app_name, total_duration_minutes
        FROM daily_app_summary
        WHERE date(log_date) = date('now', 'localtime')
        ORDER BY 2 DESC
        LIMIT 5;
        ''')
        lst = cursor.fetchall()

    if not lst:
        result = '📝Сегодня компуктер не включал... логов нет.'
    else:
        result = '😎ТОП 5 ПРОГРАММ ЗА СЕГОДНЯ:\n'
        for app, mins in lst:
            result += f'{app} : {mins} мин.\n'

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': result
    }

    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"[Ошибка сети] Не удалось отправить запрос в Telegram: {e}")
        return False


def create_data_mart():
    
    db_path = 'data/screen_time.db' 
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # создаем таблицу витрины, если её еще нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_app_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date DATE,
                app_name TEXT,
                total_duration_minutes REAL
            )
        ''')

        cursor.execute('''
        DELETE
        FROM daily_app_summary
        WHERE date(log_date) = date('now', 'localtime')
    ''')
        
        print("Запуск агрегации сырых логов за сегодня...")

        cursor.execute('''
        INSERT INTO daily_app_summary (log_date, app_name, total_duration_minutes)
        SELECT 
            date(start_time), 
            process_name_usable, 
            ROUND(SUM(duration_seconds) / 60.0, 2) AS mins
        FROM screen_time_log
        WHERE date(start_time) = date('now', 'localtime')
        GROUP BY 2
        ORDER BY 3 DESC;
        ''')

    print("Агрегация успешно завершена! Витрина данных обновлена.")

if __name__ == '__main__':
    create_data_mart()
    sent_tg_report()


