from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.telegram.operators.telegram import TelegramOperator
from datetime import datetime, timedelta
import sqlite3
import requests
import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')


# Настройки расписания
default_args = {
    'owner': 'R-407',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def send_tg_msg(txt):
    if not TOKEN or not CHAT_ID:
        print("Ошибка: Секреты Телеграма не найдены в переменных окружения!")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": txt
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print('Сообщение отправлено!')
        else:
            print(f'Что-то не так... {response.status_code}, {response.text}')
    except Exception as e:
        print(f'Ошибка: {e}')

def send_report():
    db_path = '/opt/airflow/data/screen_time.db' 
    
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

    return result

# Функция трансформации и очистки данных (наш SQL-запрос)
def run_sql_aggregation():
    # Путь внутри контейнера, который мы прокинули на Шаге 1
    db_path = '/opt/airflow/data/screen_time.db' 
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Сначала создаем таблицу витрины, если её еще нет
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
        
        #SQL-запрос агрегации
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


# Описание самого графа задач (DAG)
with DAG(
    dag_id='r407_daily_optimization',
    default_args=default_args,
    schedule_interval='55 23 * * *',  # Запуск каждый день в 23:55
    start_date=datetime(2026, 6, 1), # Дата, с которой граф начинает гипотетически существовать
    catchup=False                     # Не нужно лихорадочно выполнять задачи за прошлые дни при старте
) as dag:
    # Объявляем нашу задачу
    aggregate_task = PythonOperator(
        task_id='aggregate_raw_logs',
        python_callable=run_sql_aggregation
    )

    generate_report_task = PythonOperator(
        task_id='generate_report_text',
        python_callable=send_report
    )

    # Таск, который берет этот текст и шлет в ТГ через коннект
    send_tg_task = TelegramOperator(
        task_id='send_telegram_report',
        telegram_conn_id='my_telegram_connection',
        # Эта магия вытащит строку, которую вернул предыдущий таск
        text="{{ ti.xcom_pull(task_ids='generate_report_text') }}",
        chat_id='920398904'
    )

    # Так как задача пока одна, цепочку из >> строить не нужно, она просто выполнится
    aggregate_task >> generate_report_task >> send_tg_task