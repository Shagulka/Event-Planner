from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0005_client_address_client_market_area'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='website',
            field=models.URLField(blank=True),
        ),
    ]
