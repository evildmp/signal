from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0010_rename_dot_claim_token_and_add_claim_token"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dot",
            name="identifier",
        ),
    ]
