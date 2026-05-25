import sqlite3
import pandas as pd
from datetime import datetime
from data_collector import write_to_obsidian_log

if __name__ == '__main__':
    conn = sqlite3.connect('data/screen_time.db')
    df = pd.read_sql_query('SELECT * FROM screen_time_log;', conn)
    conn.close()

    for row in df.itertuples():
        start_t = datetime.strptime(row.start_time, "%Y-%m-%d %H:%M:%S")
        end_t = datetime.strptime(row.end_time, "%Y-%m-%d %H:%M:%S")
        clean_name = row.process_name_usable
        duration_seconds = row.duration_seconds
        window_title = row.window_title

        write_to_obsidian_log(start_t, end_t, clean_name, window_title, duration_seconds)
        print(f'Загружен: {row}')