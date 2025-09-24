-- verify.sql — быстрая самопроверка после restore
\echo 'Проверка: список таблиц и количество строк'
SELECT table_schema, table_name, pg_total_relation_size(quote_ident(table_schema)||'.'||quote_ident(table_name)) AS bytes,
       (xpath('/row/c/text()', query_to_xml(format('SELECT COUNT(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text::bigint AS row_count
FROM information_schema.tables
WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY bytes DESC
LIMIT 50;

\echo 'Проверка: наличие ключевых сущностей'
DO $$
DECLARE
  missing text[] := ARRAY[]::text[];
BEGIN
  FOREACH var IN ARRAY ARRAY['users','roles','user_roles','makes','models','cars','orders','transactions','reviews','audit_log','user_settings'] LOOP
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.tables 
      WHERE table_name = var AND table_schema IN ('public')
    ) THEN
      missing := array_append(missing, var);
    END IF;
  END LOOP;
  IF array_length(missing,1) IS NOT NULL THEN
    RAISE EXCEPTION 'Отсутствуют таблицы: %', array_to_string(missing, ', ');
  END IF;
END $$;

\echo 'Проверка: целостность внешних ключей (случайные выборки)'
-- Примеры для типичных FK — скорректируй по своей схеме при необходимости
-- Наличие моделей для марок
SELECT COUNT(*) AS bad_models_no_make
FROM models m LEFT JOIN makes mk ON mk.id = m.make_id
WHERE mk.id IS NULL;
-- Наличие авто для моделей
SELECT COUNT(*) AS bad_cars_no_model
FROM cars c LEFT JOIN models m ON m.id = c.model_id
WHERE m.id IS NULL;

\echo 'Проверка: активные представления (VIEW)'
SELECT table_schema, table_name
FROM information_schema.views
WHERE table_name IN ('vw_active_listings','vw_sales_by_make_month','vw_user_activity');

\echo 'Проверка завершена.'