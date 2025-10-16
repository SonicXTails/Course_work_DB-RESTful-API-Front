Quick Start / Быстрый старт

################ EN ################
1) Prepare PostgreSQL
   - Create DB and user with password.
   - Save credentials for later (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST=127.0.0.1, DB_PORT=5432).

2) Create & activate virtual env (Python 3.10+ recommended 3.11)
   - Windows (PowerShell):
       python -m venv .venv
       .\.venv\Scripts\Activate.ps1
   - Linux/macOS (bash):
       python -m venv .venv
       source .venv/bin/activate

3) Install backend deps
   - pip install -r requirements.txt

4) Configure settings for API
   - In API_car_dealer/settings.py set DB params (NAME/USER/PASSWORD/HOST/PORT).
   - Add ALLOWED_HOSTS = ["127.0.0.1","localhost"].
   - If you run the Django front on port 8001, set CORS/CSRF to allow http://127.0.0.1:8001.

5) Apply migrations & (optionally) create admin
   - python manage.py migrate
   - python manage.py createsuperuser   # optional
   - (Optional demo) python manage.py seed_marketplace  # if you need demo data

6) Run API server (port 8000)
   - python manage.py runserver 0.0.0.0:8000   (Windows short: py manage.py runserver)

7) Run Frontend (separately, port 8001)
   - open a new terminal, activate the same venv
   - cd car_frontend
   - python manage.py migrate
   - python manage.py runserver 0.0.0.0:8001   (Windows short: py manage.py runserver 8001)

8) Open in browser
   - Frontend UI: http://127.0.0.1:8001/
   - API root:    http://127.0.0.1:8000/
   - Swagger:     http://127.0.0.1:8000/swagger/
   - Admin:       http://127.0.0.1:8000/admin/

Notes:
- If Front cannot reach API, re-check ALLOWED_HOSTS and CORS/CSRF settings in API_car_dealer/settings.py.
- For backups (optional), ensure pg_dump is installed; backup utilities live under core/utils.

-------------------------------------------------------------

################ RU ################
1) Подготовьте PostgreSQL
   - Создайте БД и пользователя с паролем.
   - Запомните параметры: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST=127.0.0.1, DB_PORT=5432.

2) Создайте и активируйте виртуальное окружение (Python 3.10+, лучше 3.11)
   - Windows (PowerShell):
       python -m venv .venv
       .\.venv\Scripts\Activate.ps1
   - Linux/macOS (bash):
       python -m venv .venv
       source .venv/bin/activate

3) Установите зависимости бэкенда
   - pip install -r requirements.txt

4) Настройте параметры API
   - В API_car_dealer/settings.py пропишите параметры БД (NAME/USER/PASSWORD/HOST/PORT).
   - Добавьте ALLOWED_HOSTS = ["127.0.0.1","localhost"].
   - Если фронт запускается на 8001, включите CORS/CSRF для http://127.0.0.1:8001.

5) Примените миграции и (при необходимости) создайте администратора
   - python manage.py migrate
   - python manage.py createsuperuser   # по желанию
   - (Опционально демо-данные) python manage.py seed_marketplace  # если нужно наполнить

6) Запустите API (порт 8000)
   - python manage.py runserver 0.0.0.0:8000   (коротко в Windows: py manage.py runserver)

7) Запустите фронтенд (отдельно, порт 8001)
   - во втором терминале активируйте то же venv
   - cd car_frontend
   - python manage.py migrate
   - python manage.py runserver 0.0.0.0:8001   (коротко в Windows: py manage.py runserver 8001)

8) Откройте в браузере
   - Фронт:   http://127.0.0.1:8001/
   - API:     http://127.0.0.1:8000/
   - Swagger: http://127.0.0.1:8000/swagger/
   - Admin:   http://127.0.0.1:8000/admin/

Примечания:
- Если фронт «не видит» API — проверьте ALLOWED_HOSTS и настройки CORS/CSRF в API_car_dealer/settings.py.
- Для резервных копий (опционально) убедитесь, что установлен pg_dump; утилиты лежат в core/utils.