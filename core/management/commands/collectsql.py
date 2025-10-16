from io import StringIO
from pathlib import Path

from django.core.management import BaseCommand, call_command
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Собирает полный forward-SQL всех миграций (в порядке зависимостей) в один файл."

    def add_arguments(self, parser):
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS,
                            help="Имя БД из settings.DATABASES (по умолчанию: default)")
        parser.add_argument("--output", default="migrations_full.sql",
                            help="Путь к итоговому файлу (по умолчанию: migrations_full.sql)")
        parser.add_argument("--apps", default="",
                            help="Список app_label через запятую: core,users,orders (по умолчанию: все)")
        parser.add_argument("--only-unapplied", action="store_true",
                            help="Выгружать только ещё не применённые миграции")

    def handle(self, *args, **opts):
        db = opts["database"]
        out_path = Path(opts["output"]).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        apps_filter = {a.strip() for a in opts["apps"].split(",") if a.strip()}
        only_unapplied = opts["only_unapplied"] 

        connection = connections[db]
        executor = MigrationExecutor(connection)
        loader = executor.loader

        seen = set()
        ordered = []
        for leaf in loader.graph.leaf_nodes():
            for key in loader.graph.forwards_plan(leaf):
                if key in seen:
                    continue
                seen.add(key)
                migration = loader.graph.nodes[key]
                ordered.append((migration.app_label, migration.name, migration))

        buf = StringIO()
        for app_label, name, migration in ordered:
            if apps_filter and app_label not in apps_filter:
                continue
            if only_unapplied and (app_label, name) in loader.applied_migrations:
                continue

            tmp = StringIO()
            try:
                call_command("sqlmigrate", app_label, name, database=db, stdout=tmp)
            except Exception as e:
                buf.write(f"-- {app_label}.{name} (Ошибка генерации SQL: {e})\n\n")
                continue

            sql = tmp.getvalue().strip()
            if not sql:
                buf.write(f"-- {app_label}.{name} (нет SQL)\n\n")
                continue

            buf.write(f"-- === {app_label}.{name} ===\n")
            buf.write(sql)
            buf.write("\n\n")

        out_path.write_text(buf.getvalue(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Готово: {out_path}"))