# Generated manually to ensure database table exists in environments
# where migration 0003 may have been applied with an older definition.
from django.db import migrations


def ensure_table_exists(apps, schema_editor):
    model = apps.get_model("startupscan_api", "IdeaPitchSubmission")
    table_name = model._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name not in existing_tables:
        schema_editor.create_model(model)


def drop_table_if_exists(apps, schema_editor):
    model = apps.get_model("startupscan_api", "IdeaPitchSubmission")
    table_name = model._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name in existing_tables:
        schema_editor.delete_model(model)


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0004_alter_pitchanalysis_burn_rate_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_table_exists, drop_table_if_exists),
    ]
