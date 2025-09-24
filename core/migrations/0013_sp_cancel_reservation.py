from django.db import migrations


SQL_UP = r"""
CREATE OR REPLACE FUNCTION sp_cancel_reservation(p_order_id INT, p_reason TEXT DEFAULT NULL)
RETURNS VOID AS $$
DECLARE v_car_vin VARCHAR;
BEGIN
SELECT car_id INTO v_car_vin FROM core_order WHERE id = p_order_id FOR UPDATE;
IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_NOT_FOUND' USING HINT='Заказ не найден'; END IF;


PERFORM 1 FROM core_order WHERE id = p_order_id AND status = 'pending';
IF NOT FOUND THEN RAISE EXCEPTION 'ORDER_INVALID_STATE' USING HINT='Отменять можно только pending'; END IF;


UPDATE core_order SET status='cancelled' WHERE id = p_order_id;
UPDATE core_car SET status='available' WHERE "VIN" = v_car_vin;
END; $$ LANGUAGE plpgsql;
"""


SQL_DOWN = r"""
DROP FUNCTION IF EXISTS sp_cancel_reservation(INT, TEXT);
"""


class Migration(migrations.Migration):
    dependencies = [
    ('core', '0012_add_car_checks'),
    ]


    operations = [
    migrations.RunSQL(SQL_UP, reverse_sql=SQL_DOWN),
    ]