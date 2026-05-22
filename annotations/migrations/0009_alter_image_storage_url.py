from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('annotations', '0008_add_image_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='storage_url',
            field=models.CharField(
                help_text=(
                    'Canonical GCS URI of the original '
                    'full-resolution file (e.g. gs://<bucket>'
                    '/originals/<image_id>/<filename>).'
                ),
                max_length=1024,
            ),
        ),
    ]
