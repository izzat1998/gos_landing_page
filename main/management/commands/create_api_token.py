from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a token for a user"

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="Username for which to create a token"
        )

    def handle(self, *args, **options):
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist"))
            return

        token, created = Token.objects.get_or_create(user=user)

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created token for user {username}: {token.key}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Existing token for user {username}: {token.key}")
            )

        self.stdout.write(
            self.style.WARNING(
                "Add this token to your .env file as API_TOKEN=token_key"
            )
        )
