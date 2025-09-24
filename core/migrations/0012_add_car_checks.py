from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
    ('core', '0011_fix_views'),
    ]


    operations = [
    migrations.AddConstraint(
    model_name='car',
    constraint=models.CheckConstraint(
    check=Q(price__gt=0), name='car_price_gt_zero_v2'
    ),
    ),
    migrations.AddConstraint(
    model_name='car',
    constraint=models.CheckConstraint(
    check=(Q(year__gte=1980) & Q(year__lte=2100)), name='car_year_range_v2'
    ),
    ),
    ]