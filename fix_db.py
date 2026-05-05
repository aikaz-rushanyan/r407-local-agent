import sqlite3
import json

#СКРИПТ ДЛЯ ОБНОВЛЕНИЯ process_name_usable в screen_time.db из JSON.

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