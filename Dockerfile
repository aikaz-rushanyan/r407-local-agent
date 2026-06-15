FROM apache/airflow:2.9.1-python3.12

# Используем официальные constraints, чтобы pip не обновлял лишнего
RUN pip install --no-cache-dir "apache-airflow-providers-telegram" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.1/constraints-3.12.txt"