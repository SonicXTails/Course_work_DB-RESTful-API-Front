set -e

echo "[entrypoint] Загружаю переменные окружения..."

wait_for_db() {
    if [ "${DB_HOST}" = "localhost" ] && getent hosts host.docker.internal >/dev/null 2>&1; then
    echo "[entrypoint] DB_HOST=localhost -> host.docker.internal (Docker Desktop)"
    export DB_HOST=host.docker.internal
    fi
}

echo "[entrypoint] Миграции API..."
wait_for_db
python /app/manage.py migrate --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
  echo "[entrypoint] Создаю/обновляю суперпользователя API..."
  python /app/manage.py shell <<'PYCODE'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(
    username=os.environ["DJANGO_SUPERUSER_USERNAME"],
    defaults={"email": os.environ["DJANGO_SUPERUSER_EMAIL"], "is_staff": True, "is_superuser": True},
)
u.set_password(os.environ["DJANGO_SUPERUSER_PASSWORD"]); u.save()
print("Superuser ensured.")
PYCODE
fi

echo "[entrypoint] Миграции Front..."
python /app/car_frontend/manage.py migrate --noinput || true

echo "[entrypoint] Стартую supervisor..."
exec "$@"