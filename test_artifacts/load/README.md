
# Нагрузочное тестирование (Locust)

## Быстрый запуск
```bash
pip install locust
export LOAD_TOKEN=$ADMIN_TOKEN
locust -f load/locustfile.py --host ${API_BASE_URL:-http://localhost:8000} --headless -u 10 -r 5 -t 3m
```

## Профили
- Smoke (CI): `-u 10 -r 5 -t 2m`
- Расширенный: `-u 150 -r 20 -t 20m`
