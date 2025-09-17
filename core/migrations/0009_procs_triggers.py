from django.db import migrations

SQL = r"""
-- ######### ПРОЦЕДУРЫ #########
CREATE OR REPLACE FUNCTION sp_reserve_car(p_user_id INT, p_car_vin VARCHAR)
RETURNS INT AS $$
DECLARE v_order_id INT; v_price NUMERIC;
BEGIN
  PERFORM 1 FROM core_car WHERE "VIN"=p_car_vin AND status='available' FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'CAR_NOT_AVAILABLE' USING HINT='Авто недоступно'; END IF;

  SELECT price INTO v_price FROM core_car WHERE "VIN"=p_car_vin;
  INSERT INTO core_order(buyer_id, car_id, status, order_date, total_amount)
  VALUES(p_user_id, p_car_vin, 'pending', now(), v_price)
  RETURNING id INTO v_order_id;

  UPDATE core_car SET status='reserved' WHERE "VIN"=p_car_vin;
  RETURN v_order_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_complete_sale(p_order_id INT)
RETURNS INT AS $$
DECLARE v_tx_id INT; v_car_vin VARCHAR; v_amount NUMERIC;
BEGIN
  SELECT car_id, total_amount INTO v_car_vin, v_amount FROM core_order WHERE id=p_order_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND'; END IF;

  PERFORM 1 FROM core_order WHERE id=p_order_id AND status='pending';
  IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Продажа возможна только из pending'; END IF;

  INSERT INTO core_transaction(order_id, amount, transaction_date, status)
  VALUES(p_order_id, v_amount, now(), 'completed')
  RETURNING id INTO v_tx_id;

  UPDATE core_order SET status='paid' WHERE id=p_order_id;
  UPDATE core_car   SET status='sold' WHERE "VIN"=v_car_vin;

  RETURN v_tx_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE sp_bulk_reprice(p_make_id INT, p_percent NUMERIC)
LANGUAGE plpgsql AS $$
BEGIN
  UPDATE core_car
  SET price = ROUND(price * (1 + p_percent/100.0), 2)
  WHERE make_id = p_make_id AND status IN ('available','reserved');
END;
$$;

-- ######### ВАЛИДАЦИЯ ТРАНЗАКЦИЙ #########
CREATE OR REPLACE FUNCTION trg_validate_tx() RETURNS trigger AS $$
DECLARE v_order_status TEXT;
BEGIN
  SELECT status INTO v_order_status FROM core_order WHERE id = NEW.order_id;
  IF v_order_status <> 'pending' THEN
    RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Транзакцию можно создать только из pending';
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS validate_tx ON core_transaction;
CREATE TRIGGER validate_tx BEFORE INSERT ON core_transaction
FOR EACH ROW EXECUTE FUNCTION trg_validate_tx();

-- ######### АУДИТ DB-УРОВНЯ #########
-- HSTORE не нужен, так как используем JSONB, но не помешает:
CREATE EXTENSION IF NOT EXISTS hstore;

CREATE OR REPLACE FUNCTION audit_row() RETURNS trigger AS $$
DECLARE rec_id text;
BEGIN
  -- Универсально вынимаем PK: сначала id, если нет — VIN (для core_car)
  rec_id := COALESCE(
              (to_jsonb(NEW)->>'id'),
              (to_jsonb(OLD)->>'id'),
              (to_jsonb(NEW)->>'VIN'),
              (to_jsonb(OLD)->>'VIN')
           );

  INSERT INTO core_auditlog(user_id, action, table_name, record_id, old_data, new_data, action_time)
  VALUES (NULL, TG_OP, TG_TABLE_NAME, rec_id, to_jsonb(OLD), to_jsonb(NEW), now());
  RETURN COALESCE(NEW, OLD);
END; $$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='audit_cars') THEN
    CREATE TRIGGER audit_cars  AFTER INSERT OR UPDATE OR DELETE ON core_car  FOR EACH ROW EXECUTE FUNCTION audit_row();
    CREATE TRIGGER audit_orders AFTER INSERT OR UPDATE OR DELETE ON core_order FOR EACH ROW EXECUTE FUNCTION audit_row();
    CREATE TRIGGER audit_tx     AFTER INSERT OR UPDATE OR DELETE ON core_transaction FOR EACH ROW EXECUTE FUNCTION audit_row();
  END IF;
END $$;
"""

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_views'),
    ]

    operations = [
        migrations.RunSQL(SQL),
    ]