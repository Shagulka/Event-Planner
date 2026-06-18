from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0011_fix_empty_decimal_strings'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
