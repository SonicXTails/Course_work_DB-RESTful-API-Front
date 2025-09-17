from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_userprofile'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='car',
            constraint=models.CheckConstraint(check=models.Q(price__gt=0), name='car_price_gt_zero'),
        ),
        migrations.AddConstraint(
            model_name='car',
            constraint=models.CheckConstraint(check=(models.Q(year__gte=1980) & models.Q(year__lte=2100)), name='car_year_range'),
        ),
        migrations.AddConstraint(
            model_name='car',
            constraint=models.UniqueConstraint(fields=('VIN',), name='uniq_car_vin'),
        ),
    ]