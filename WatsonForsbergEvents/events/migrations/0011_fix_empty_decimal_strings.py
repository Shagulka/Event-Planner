from django.db import migrations


def fix_empty_decimals(apps, schema_editor):
    tables_and_columns = [
        ('events_budgetlineitem', 'proposed_amount'),
        ('events_budgetlineitem', 'actual_amount'),
        ('events_event', 'proposed_amount'),
        ('events_event', 'approved_amount'),
        ('events_eventpayment', 'amount'),
    ]
    with schema_editor.connection.cursor() as cursor:
        for table, column in tables_and_columns:
            cursor.execute(
                f"UPDATE {table} SET {column} = NULL WHERE {column} = ''"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0010_add_awards_event_type'),
    ]

    operations = [
        migrations.RunPython(fix_empty_decimals, migrations.RunPython.noop),
    ]
