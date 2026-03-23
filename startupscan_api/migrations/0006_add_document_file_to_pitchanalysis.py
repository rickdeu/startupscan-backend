from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0005_ensure_idea_pitch_submission_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="pitchanalysis",
            name="document_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="pitches/docs/%Y/%m/%d/",
                verbose_name="Ficheiro Submetido",
            ),
        ),
    ]
