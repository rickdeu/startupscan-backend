from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0006_add_document_file_to_pitchanalysis"),
    ]

    operations = [
        migrations.AddField(
            model_name="pitchanalysis",
            name="explainer_video_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="pitches/explainer/%Y/%m/%d/",
                verbose_name="Vídeo Explicativo IA",
            ),
        ),
    ]
