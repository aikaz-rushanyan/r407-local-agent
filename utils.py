from datetime import datetime
from dotenv import load_dotenv
import sqlite3
import json
import requests
import os
import pandas as pd

load_dotenv()

#СКРИПТ ДЛЯ ОБНОВЛЕНИЯ process_name_usable в screen_time.db из JSON.
def update_screen_time_log(): #обновляет БД, ничего не возвращает
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
def get_current_date(): #выводит дату
    now = datetime.now()
    week_lst = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    current_day = week_lst[now.weekday()] 

    return f"{now.strftime('%Y-%m-%d')} ({current_day})"

#СКРИПТ ДЛЯ ОТПРАВКИ ОТЧЕТА В ТГ
def send_tg_report(lst):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    db_path = 'data/screen_time.db' 
    
    if not token or not chat_id:
        print('[Ошибка] В .env не настроены токен или chat_id для Telegram!')
        print(f'TG_TOKEN: {token}\nTG_CHAT_ID: {chat_id}')
        return

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


def get_stats_for_period(start_date, end_date):
    """
    Выдает статистику за любой период. 
    """
    db_path = 'data/screen_time.db'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT process_name_usable, ROUND(SUM(duration_seconds) / 60.0, 2) AS mins
            FROM screen_time_log
            WHERE date(start_time) BETWEEN ? AND ?
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 10;
        ''', (start_date, end_date))
        return cursor.fetchall()

if __name__ == '__main__':
    pass


