from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_event_created_at_event_created_by_event_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('CONFERENCE', 'Conference'),
                    ('MEETING', 'Meeting'),
                    ('PARTY', 'Party'),
                    ('FUNDRAISER', 'Fundraiser'),
                    ('OTHER', 'Other'),
                ],
                default='',
                max_length=20,
            ),
        ),
    ]
