from django.db import migrations

CREATE_VIEWS = r"""
CREATE OR REPLACE VIEW vw_active_listings AS
SELECT c."VIN" AS vin, m.name AS make, md.name AS model,
c.price, c.year, c.status, c.created_at
FROM core_car c
JOIN core_make m ON m.id = c.make_id
JOIN core_model md ON md.id = c.model_id
WHERE c.status = 'available';


CREATE OR REPLACE VIEW vw_sales_by_make_month AS
SELECT m.name AS make,
date_trunc('month', t.transaction_date) AS month,
COUNT(*) AS deals,
SUM(t.amount) AS revenue
FROM core_transaction t
JOIN core_order o ON o.id = t.order_id
JOIN core_car c ON c."VIN" = o.car_id
JOIN core_make m ON m.id = c.make_id
WHERE t.status = 'completed'
GROUP BY m.name, date_trunc('month', t.transaction_date);


CREATE OR REPLACE VIEW vw_user_activity AS
SELECT u.id AS user_id, u.username,
COUNT(DISTINCT o.id) AS orders_cnt,
COUNT(DISTINCT t.id) AS tx_cnt
FROM core_user u
LEFT JOIN core_order o ON o.buyer_id = u.id
LEFT JOIN core_transaction t ON t.order_id = o.id AND t.status = 'completed'
GROUP BY u.id, u.username;
"""


DROP_VIEWS = r"""
DROP VIEW IF EXISTS vw_user_activity;
DROP VIEW IF EXISTS vw_sales_by_make_month;
DROP VIEW IF EXISTS vw_active_listings;
"""


class Migration(migrations.Migration):
    dependencies = [
    ('core', '0010_remove_car_car_price_gt_zero_and_more'),
    ]


    operations = [
    migrations.RunSQL(CREATE_VIEWS, reverse_sql=DROP_VIEWS),
    ]