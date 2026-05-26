from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0011_remove_dot_identifier"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignalOnboardingState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("using_signal_seen", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="signal_onboarding_state",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
