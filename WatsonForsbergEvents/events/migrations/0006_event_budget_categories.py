from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_event_event_type'),
    ]

    operations = [
        migrations.AddField(model_name='event', name='budget_materials_proposed',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_materials_actual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_venue_proposed',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_venue_actual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_tickets_proposed',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_tickets_actual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_misc_proposed',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='event', name='budget_misc_actual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
    ]
