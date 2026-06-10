from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sqlite3

# Настройки расписания
default_args = {
    'owner': 'R-407',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# 1. Функция трансформации и очистки данных (наш SQL-запрос)
def run_sql_aggregation():
    # Путь внутри контейнера, который мы прокинули на Шаге 1
    db_path = '/opt/airflow/data/screen_time.db' 
    
    conn = sqlite3.connect(db_path)
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
    
    # Твой оптимизированный SQL-запрос агрегации
    query = '''
    INSERT INTO daily_app_summary (log_date, app_name, total_duration_minutes)
    SELECT 
        date(start_time), 
        process_name_usable, 
        ROUND(SUM(duration_seconds) / 60.0, 2) AS mins
    FROM screen_time_log
    WHERE date(start_time) = date('now', 'localtime')
    GROUP BY 2
    ORDER BY 3 DESC;
    '''
    
    print("Запуск агрегации сырых логов за сегодня...")
    cursor.execute(query)
    conn.commit()
    conn.close()
    print("Агрегация успешно завершена! Витрина данных обновлена.")


# 2. Описание самого графа задач (DAG)
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

    # Так как задача пока одна, цепочку из >> строить не нужно, она просто выполнится
    aggregate_task