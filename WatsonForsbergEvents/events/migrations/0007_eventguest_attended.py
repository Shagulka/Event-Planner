from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_event_budget_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventguest',
            name='attended',
            field=models.BooleanField(default=False),
        ),
    ]
