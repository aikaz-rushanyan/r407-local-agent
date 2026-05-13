import os
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
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus

# --- НАСТРОЙКИ AFK ---
AFK_THRESHOLD_SECONDS = 180  # 3 минуты бездействия = скрипт встает на паузу

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
    """Обертка, чтобы было удобно использовать это в обычном коде"""
    return asyncio.run(is_media_playing_async())

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
os.makedirs('data', exist_ok=True)

with open('config/process_names.json', 'r', encoding='utf-8') as file:
    names = json.load(file)

conn = sqlite3.connect('data/screen_time.db')
cursor = conn.cursor()

def run_query(query, params=(), many=False):
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

def save_log_entry(last_w, start_t, end_t):
    """Запись в базу данных sqlite.
    process_name, process_name_usable, window_title, 
    start_time, end_time, duration_seconds"""
    duration = int((end_t - start_t).total_seconds())
    process_name, window_title = last_w

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
        print(f'Сохранено: {names.get(process_name, process_name)} | {duration} сек')

try:
    last_window = None
    start_time = datetime.now()

    print(f"Сборщик запущен. Таймер AFK: {AFK_THRESHOLD_SECONDS} секунд.")

    while True:
        idle_seconds = get_idle_duration()
        # Если комп не трогали дольше лимита, принудительно переводим окно в статус AFK
        if idle_seconds >= AFK_THRESHOLD_SECONDS and not check_media():
            current_window = ('AFK', 'Away From Keyboard')
        else:
            current_window = get_current_window()

        if current_window != last_window:
            now = datetime.now()
            end_t = now
            
            # Трюк с отмоткой времени: если мы только что провалились в AFK, 
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

except KeyboardInterrupt:
    now = datetime.now()
    if last_window is not None:
        save_log_entry(last_window, start_time, now)
    
    conn.close()
    print('Сохранено и остановлено.')