from django.db import migrations, models
import app.models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0009_replace_include_name_with_owner_user"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dot",
            old_name="claim_token",
            new_name="ownership_token",
        ),
        migrations.AddField(
            model_name="dot",
            name="claim_token",
            field=models.CharField(
                default=app.models.generate_dot_identifier,
                editable=False,
                max_length=64,
            ),
        ),
    ]
