import os
import pandas as pd
import time
import psutil
import win32gui
import win32process
import sqlite3
import json
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import pystray
from PIL import Image, ImageDraw
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus

# === ЛОГИКА СБОРА ДАННЫХ ===

# --- ИГНОР БРАУЗЕРОВ ---
BROWSERS_TO_IGNORE = {'chrome.exe', 'msedge.exe', 'browser.exe', 'yandex.exe', 'opera.exe', 'brave.exe'}
# --- НАСТРОЙКИ AFK ---
AFK_THRESHOLD_SECONDS = 300  # 5 минут бездействия = скрипт встает на паузу
# --- OBSIDIAN ---
OBSIDIAN_BRAIN_PATH = 'Obsidian_brain/Daily_logs'
os.makedirs(OBSIDIAN_BRAIN_PATH, exist_ok=True)

# Флаги для управления треем и потоками
program_alive = True
is_running = True

# Замок для безопасной записи в базу из разных потоков (Main loop и Flask)
db_lock = threading.Lock()

# Структура для получения времени последнего инпута от Windows
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]

def get_idle_duration():
    """Возвращает количество секунд с последнего движения мышью или нажатия клавиши"""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        # Сравниваем текущий аптайм системы с временем последнего инпута
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0

async def is_media_playing_async():
    """Асинхронная функция для запроса статуса у Windows"""
    
    # Запрашиваем у Windows доступ к менеджеру медиа
    manager = await MediaManager.request_async()
    
    # Получаем текущую активную сессию (какой плеер/браузер сейчас главный)
    session = manager.get_current_session()
    
    # Если сессии нет (ты вообще закрыл браузер и все плееры)
    if session is None:
        return False
        
    # Получаем информацию о воспроизведении
    playback_info = session.get_playback_info()
    
    # Проверяем статус: PLAYING (играет), PAUSED (на паузе), STOPPED (остановлено)
    if playback_info.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
        return True
        
    return False

def check_media():
    """Обертка, чтобы было удобно использовать is_media_playing_async в обычном коде"""
    return asyncio.run(is_media_playing_async())

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
os.makedirs('data', exist_ok=True)
os.makedirs('config', exist_ok=True)

if not os.path.exists('config/process_names.json'):
    names = {'Code.exe': 'VS Code'}
    with open('config/process_names.json', 'w', encoding='utf-8') as file:
        json.dump(names, file, ensure_ascii=False, indent=4)
else:
    with open('config/process_names.json', 'r', encoding='utf-8') as file:
        names = json.load(file)

conn = sqlite3.connect('data/screen_time.db', check_same_thread=False, timeout=30)
cursor = conn.cursor()

def run_query(query, params=(), many=False):
    """Быстрый SQL-запрос"""
    result = None
    with db_lock:
        if query.strip().upper().startswith('SELECT'):
            cursor.execute(query, params)
            result = cursor.fetchall()
        else:
            if many:
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params)
            conn.commit()
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
    """Возвращает окно: process_name, current_window_title.
    Если возникла ошибка то возвращет: 'Unknown.exe', current_window_title"""
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
    """Генерация имени в JSON"""
    name = proc_name.split('.')[0].replace('_', ' ')
    name = ''.join([i for i in name if not i.isdigit()]) + '*'
    return name

def write_to_obsidian_log(start_t, end_t, process_name_usable, window_title, duration_seconds):
    """Создание логов в формате md"""
    #Перевод в минуты
    duration_min = round(duration_seconds / 60, 2)

    #Меньше минуты - мусор
    if duration_min < 0.5:
        return
    
    #Перевод в формат час:минута (14:05 - 14:15)
    start_str = start_t.strftime('%H:%M')
    end_str = end_t.strftime('%H:%M')

    #Название лога - дата
    date_str = start_t.strftime('%Y-%m-%d')
    file_path = os.path.join(OBSIDIAN_BRAIN_PATH, f'{date_str}.md')

    #Создание лога
    log_line = f'⌛ {start_str} - {end_str} | 🖥️ {process_name_usable} - {duration_min} | 🦖 {window_title}'

    #Проверка на существование файла
    file_exists = os.path.exists(file_path)

    #Открываем файл в режиме 'append'
    with open(file_path, 'a', encoding='utf-8') as f:
        #Если записей нет - пишем заголовок
        if not file_exists and os.path.getsize(file_path) == 0:
            f.write(f'🧠 Логи активности за {date_str}\n\n')
        #Запись лога
        f.write(f'{log_line}\n')

def save_log_entry(last_w, start_t, end_t):
    """Запись в базу данных sqlite.
    process_name, process_name_usable, window_title, 
    start_time, end_time, duration_seconds"""

    duration = int((end_t - start_t).total_seconds())
    process_name, window_title = last_w

    #Проверка на браузер
    if process_name.lower() in BROWSERS_TO_IGNORE:
        return
    
    # Если мы были в режиме AFK, мы просто игнорируем это и не пишем в базу
    if process_name == 'AFK':
        print(f'Пауза AFK завершена. Время отсутствия: {duration} сек.')
        return

    if duration > 0:
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

        clean_name = names.get(process_name, process_name)
        write_to_obsidian_log(start_t, end_t, clean_name, window_title, duration)

        print(f'Сохранено: {clean_name} | {duration} сек')

app = Flask(__name__)
CORS(app) # Чтобы браузер не ругался на CORS-политику безопасности

@app.route('/log', methods=['POST'])
def receive_browser_log():
    data = request.json
    
    # Расширение пришлет: process_name, window_title, duration_seconds
    proc_name = data.get('process_name', 'Browser')
    window_title = data.get('window_title', 'Unknown Tab')
    duration = int(data.get('duration_seconds', 0))
    
    if duration <= 0:
        return jsonify({"status": "ignored", "reason": "zero duration"}), 200

    end_time = datetime.now()
    start_time = end_time - timedelta(seconds=duration)

    # Пишем напрямую в базу
    run_query('''INSERT INTO screen_time_log(process_name, process_name_usable, window_title, start_time, end_time, duration_seconds) 
                VALUES (?, ?, ?, ?, ?, ?)''', 
                (proc_name, "Браузер", window_title, 
                 start_time.strftime('%Y-%m-%d %H:%M:%S'), 
                 end_time.strftime('%Y-%m-%d %H:%M:%S'), duration))
    conn.commit()

    # Пишем в Obsidian
    write_to_obsidian_log(start_time, end_time, "Браузер", window_title, duration)
    print(f'Сохранено (Браузер): {window_title} | {duration} сек')
    
    return jsonify({"status": "success"}), 200

def start_server():
    # Запускаем сервер на порту 5000 без дебаг-режима, чтобы не ломать потоки
    app.run(port=5000, debug=False, use_reloader=False)
    print("API-сервер для браузерного расширения запущен на http://127.0.0.1:5000")

def data_collector_loop():
    global is_running, program_alive

    last_window = None
    start_time = datetime.now()

    print(f"Сборщик запущен. Таймер AFK: {AFK_THRESHOLD_SECONDS} секунд.")

    while program_alive:
        if is_running:
            idle_seconds = get_idle_duration()
            # Если комп не трогали дольше лимита, принудительно переводим окно в статус AFK
            if idle_seconds >= AFK_THRESHOLD_SECONDS and not check_media():
                current_window = ('AFK', 'Away From Keyboard')
            else:
                current_window = get_current_window()

            if current_window != last_window:
                now = datetime.now()
                end_t = now
                
                # Отмотка времени: если мы только что провалились в AFK, 
                # значит последние X секунд мы уже ничего не делали. Вычитаем их из активной программы.
                if current_window[0] == 'AFK':
                    end_t = now - timedelta(seconds=AFK_THRESHOLD_SECONDS)
                    
                if last_window is not None:
                    save_log_entry(last_window, start_time, end_t)
                    
                last_window = current_window
                
                # Если мы провалились в AFK, то он начался X секунд назад.
                # Если мы вернулись из AFK, активная работа началась прямо сейчас.
                if current_window[0] == 'AFK':
                    start_time = end_t 
                else:
                    start_time = now
            
            time.sleep(1)
        else:
            time.sleep(1)

    now = datetime.now()
    if last_window is not None:
        save_log_entry(last_window, start_time, now)
    conn.close()
    print('Сохранено и остановлено.')


# === ЛОГИКА ТРЕЯ ===

def create_circle_image(color):
    width, height = 64, 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((4, 4, width-4, height-4), fill=color, outline='black', width=2)
    return image

def toggle_status(icon, item):
    global is_running
    is_running = not is_running
    if is_running:
        icon.icon = create_circle_image('green')
        icon.title = "Droid Data Collector (Активен)"
        print("Сборщик запущен.")
    else:
        icon.icon = create_circle_image('red')
        icon.title = "Droid Data Collector (На паузе)"
        print("Сборщик поставлен на паузу.")

def on_exit_clicked(icon, item):
    global is_running, program_alive
    print("Уничтожение приложения...")
    is_running = False
    program_alive = False # Завершаем цикл my_data_collector_logic
    icon.stop()           # Закрываем трей

def run_tray():
    """Точка сборки всех потоков"""
    # 1. Стартуем поток Flask-сервера
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 2. Стартуем поток сборщика данных
    collector_thread = threading.Thread(target=data_collector_loop, daemon=True)
    collector_thread.start()

    # 3. Стартуем сам Трей (блокирует консоль)
    icon = pystray.Icon("data_collector_services")
    icon.icon = create_circle_image('green')
    icon.title = "Droid Data Collector (Активен)"
    icon.menu = pystray.Menu(
        pystray.MenuItem(lambda text: "Поставить на ПАУЗУ" if is_running else "ЗАПУСТИТЬ сбор", toggle_status),
        pystray.MenuItem('Выход', on_exit_clicked)
    )
    icon.run()

if __name__ == '__main__':
    run_tray()