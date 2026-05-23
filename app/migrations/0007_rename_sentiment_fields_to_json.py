from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_dot_claim_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="dot",
            name="feeling_free_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dot",
            name="action_sentiment_free_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dot",
            name="published_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="dot",
            name="feeling",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="dot",
            name="action_sentiment",
            field=models.JSONField(blank=True, default=list),
        ),
    ]