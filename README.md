# Fuzzy Address Search

Сервис для поиска адресов по нечеткому соответствию (триграммы + расстояние Левенштейна).

## Стек

- Python 3.11
- FastAPI
- pandas
- Docker

## Структура

- `app/search_service.py` — логика индекса и поиска
- `app/main.py` — FastAPI-приложение
- `app/data/final_norm.csv` — данные
- `Dockerfile` — для контейнера
- `requirements.txt` — зависимости

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload