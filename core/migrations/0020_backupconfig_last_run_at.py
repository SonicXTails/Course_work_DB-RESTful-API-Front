from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0019_backupconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupconfig',
            name='last_run_at',
            field=models.DateTimeField(null=True, blank=True, default=None),
        ),
    ]