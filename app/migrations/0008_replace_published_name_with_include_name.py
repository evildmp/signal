from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0007_rename_sentiment_fields_to_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="dot",
            name="include_name",
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name="dot",
            name="published_name",
        ),
    ]
