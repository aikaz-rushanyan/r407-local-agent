import os
import time
import psutil
import win32gui
import win32process
import sqlite3
from datetime import datetime
import json

os.makedirs('data', exist_ok=True)

with open('config/process_names.json', 'r', encoding='utf-8') as file:
    names = json.load(file)

conn = sqlite3.connect('data/screen_time.db')
cursor = conn.cursor()

def run_query(query, params=(), many=False): #запрос SQL, кортеж значений, executemany вкл/выкл
    result = None

    if query.strip().upper().startswith('SELECT'):
        cursor.execute(query, params)
        result = cursor.fetchall()

    else:
        
        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params)

    return result

run_query('''
    CREATE TABLE IF NOT EXISTS screen_time_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        process_name TEXT,
        process_name_usable TEXT,
        window_title TEXT,
        start_time DATETIME,
        end_time DATETIME,
        duration_seconds INTEGER  
        )
''')

def get_current_window():
    current_window_handle = win32gui.GetForegroundWindow()
    current_window_title = win32gui.GetWindowText(current_window_handle)

    _, pid = win32process.GetWindowThreadProcessId(current_window_handle)

    if pid <= 0:
        return ('System', current_window_title)
    
    try:
        process = psutil.Process(pid)
        process_name = process.name()

        return (process_name, current_window_title)
    
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return ('Unknown.exe', current_window_title)

def generate_name(proc_name):
    name = proc_name.split('.')[0].replace('_', ' ')
    name = ''.join([i for i in name if not i.isdigit()]) + '*'
    

    return name

def save_log_entry(last_w, start_t, end_t):  
    duration = int((end_t - start_t).total_seconds())

    if duration > 0:
        process_name, window_title = last_w

        if process_name not in names:
            names[process_name] = generate_name(process_name)
            with open('config/process_names.json', 'w', encoding='utf-8') as f:
                json.dump(names, f, ensure_ascii=False, indent=4)
                    
        run_query('''INSERT INTO screen_time_log(process_name, process_name_usable, window_title, start_time, end_time, duration_seconds) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                    (process_name, 
                    names[process_name],
                    window_title, 
                    start_t.strftime('%Y-%m-%d %H:%M:%S'), 
                    end_t.strftime('%Y-%m-%d %H:%M:%S'), 
                    duration))
        
        conn.commit()          
        print(f'Сохранено: {process_name} | {duration}')

try:
    last_window = None
    start_time = datetime.now()

    while True:
        current_window = get_current_window()

        if current_window != last_window:
            now = datetime.now()

            if last_window is not None:
                save_log_entry(last_window, start_time, now)
                

        last_window = current_window
        start_time = now
    
        time.sleep(1)

except KeyboardInterrupt:
    now = datetime.now()
    if last_window is not None:
        save_log_entry(last_window, start_time, now)
    
    conn.close()
    print('Сохранено и становлено.')
