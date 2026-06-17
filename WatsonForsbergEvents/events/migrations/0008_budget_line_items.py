from django.db import migrations, models
import django.db.models.deletion


def migrate_flat_budget_to_line_items(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    EventBudget = apps.get_model('events', 'EventBudget')
    BudgetLineItem = apps.get_model('events', 'BudgetLineItem')

    FLAT_FIELDS = [
        ('budget_materials_proposed', 'budget_materials_actual', 'materials', 'Materials'),
        ('budget_venue_proposed',     'budget_venue_actual',     'venue',     'Venue'),
        ('budget_tickets_proposed',   'budget_tickets_actual',   'tickets',   'Tickets'),
        ('budget_misc_proposed',      'budget_misc_actual',      'misc',      'Misc'),
    ]

    for event in Event.objects.all():
        items = []
        for p_field, a_field, category, name in FLAT_FIELDS:
            proposed = getattr(event, p_field, None)
            actual = getattr(event, a_field, None)
            if proposed or actual:
                items.append((category, name, proposed, actual))

        if items:
            budget = EventBudget.objects.create(event=event)
            for category, name, proposed, actual in items:
                BudgetLineItem.objects.create(
                    budget=budget,
                    category=category,
                    name=name,
                    proposed_amount=proposed,
                    actual_amount=actual,
                )


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0007_eventguest_attended'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='budget',
                    to='events.event',
                )),
            ],
        ),
        migrations.CreateModel(
            name='BudgetLineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('budget', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='line_items',
                    to='events.eventbudget',
                )),
                ('category', models.CharField(
                    choices=[
                        ('materials', 'Materials'),
                        ('venue', 'Venue'),
                        ('swag', 'Swag'),
                        ('tickets', 'Tickets'),
                        ('donations', 'Donations'),
                        ('travel', 'Travel'),
                        ('misc', 'Misc'),
                    ],
                    max_length=20,
                )),
                ('name', models.CharField(max_length=200)),
                ('proposed_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('actual_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
            options={'ordering': ['category', 'id']},
        ),
        migrations.RunPython(migrate_flat_budget_to_line_items, migrations.RunPython.noop),
        migrations.RemoveField(model_name='event', name='budget_materials_proposed'),
        migrations.RemoveField(model_name='event', name='budget_materials_actual'),
        migrations.RemoveField(model_name='event', name='budget_venue_proposed'),
        migrations.RemoveField(model_name='event', name='budget_venue_actual'),
        migrations.RemoveField(model_name='event', name='budget_tickets_proposed'),
        migrations.RemoveField(model_name='event', name='budget_tickets_actual'),
        migrations.RemoveField(model_name='event', name='budget_misc_proposed'),
        migrations.RemoveField(model_name='event', name='budget_misc_actual'),
    ]
