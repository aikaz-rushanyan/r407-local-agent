# R-407: Local Data Science AI Agent 🤖📊

Локальный ИИ-ассистент с саркастичным характером, который анализирует логи использования компьютера (Screen Time) с помощью Text-to-SQL архитектуры.

## О проекте
Проект создан для приватного анализа личной статистики без передачи данных на сторонние серверы (100% Local execution). 
Модель получает естественный запрос на русском языке, автономно пишет SQL-код, выполняет его в локальной базе данных SQLite и выдает саркастичный, но мотивирующий ответ о продуктивности пользователя.

## Стек технологий
- **Язык:** Python
- **База данных:** SQLite3
- **Оркестрация ИИ:** LangChain (`langchain-ollama`)
- **LLM Engine:** Ollama
- **Модели:** SQL-агент и кастомная сборка `R-407` (`qwen2.5-coder:3b`базовая модель `gemma4:e2b`, настроенная через `Modelfile`)

## Архитектура
Проект построен на принципах ООП с жестким разделением ответственности (Separation of Concerns):
1. `db_agent.py` (`DatabaseAnalyst`): "Сухой" аналитик. Переводит естественный язык в SQL, обращается к базе данных `screen_time.db` и возвращает сырые факты.
2. `main_agent.py` (`MainAgent`): Оболочка личности R-407. Принимает точные факты от базы данных и генерирует финальный ответ. Характер дроида зашит на системном уровне через `Modelfile` и поддерживается в промптах LangChain.

## Установка и запуск
**Требования:**
- Установленная [Ollama](https://ollama.com/)

**Шаги:**
1. Клонировать репозиторий:
   ```bash
   git clone [https://github.com/aikaz-rushanyan/r407-local-agent.git](https://github.com/aikaz-rushanyan/r407-local-agent.git)
   
2. Скачать модели:
   ```bash
   ollama pull qwen2.5-coder:3b
   ```
   ```bash
   ollama pull gemma4:e2b
   ```

3.Собрать кастомную модель R-407 в локальном движке Ollama:
```bash
ollama create R-407 -f Modelfile
```
4. Создать и активировать виртуальное окружение:
```bash
python -m venv venv 
venv\Scripts\activate # Для Windows
```   
5. **Установить зависимости:**
```bash
pip install -r requirements.txt
```
6. **Запустить data_collector.py для сбора данных (автоматически создаст data/screen_time.db)**
```bash
python data_collector.py
```  
6. **Запустить агента:**
```bash
python main_agent.py
```
**Примечание:** 
Сама база данных `screen_time.db` и виртуальное окружение добавлены в `.gitignore` из соображений приватности. Для тестирования необходимо использовать собственную базу SQLite со схемой логов времени (используйте data_collector.py).
