from django.db import migrations, models

def set_system_to_dark(apps, schema_editor):
    UserSettings = apps.get_model('core', 'UserSettings')
    UserSettings.objects.filter(theme='system').update(theme='dark')

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_backupconfig_cron_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersettings',
            name='theme',
            field=models.CharField(choices=[('system', 'System'), ('light', 'Light'), ('dark', 'Dark')], default='dark', max_length=10),
        ),
        migrations.RunPython(set_system_to_dark, reverse_code=migrations.RunPython.noop),
    ]
