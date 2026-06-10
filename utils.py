from datetime import datetime

def get_current_date():
    now = datetime.now()
    week_lst = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    current_day = week_lst[now.weekday()] 

    return f"{now.strftime('%Y-%m-%d')} ({current_day})"