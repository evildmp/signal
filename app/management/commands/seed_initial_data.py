from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds initial development users."

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = "jerry"

        if user_model.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING("User 'jerry' already existed"))
            return

        user_model.objects.create_user(username=username, password=username)
        self.stdout.write(self.style.SUCCESS("Created user 'jerry'"))
