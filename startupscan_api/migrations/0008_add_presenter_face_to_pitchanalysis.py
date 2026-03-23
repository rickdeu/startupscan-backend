from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0007_add_explainer_video_to_pitchanalysis"),
    ]

    operations = [
        migrations.AddField(
            model_name="pitchanalysis",
            name="presenter_face_image_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="pitches/presenter/%Y/%m/%d/",
                verbose_name="Rosto do Apresentador",
            ),
        ),
    ]
