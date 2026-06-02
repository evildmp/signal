from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0012_signal_onboarding_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="dot",
            name="flag_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dot",
            name="flagged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dot",
            name="flagged_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="flagged_dots",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
