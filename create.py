import sqlite3

conn = sqlite3.connect('data/screen_time.db')
cursor = conn.cursor()

cursor.execute('''
    INSERT INTO daily_app_summary (log_date, app_name, total_min)
    SELECT 
        date(start_time), 
        process_name_usable, 
        ROUND(SUM(duration_seconds) / 60.0, 2) as mins
    FROM screen_time_log
    WHERE date(start_time) = date('now', 'localtime')
    GROUP BY 2
    ORDER BY 3 DESC;
''')
res = cursor.fetchall()

conn.commit()
conn.close()

print(res)

