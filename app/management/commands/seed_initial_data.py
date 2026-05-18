from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from datetime import timedelta
import random

from app.models import (
    DOT_IDENTIFIER_ADJECTIVES,
    DOT_IDENTIFIER_COLOURS,
    DOT_IDENTIFIER_NOUNS,
    Dot,
    Team,
    TeamMembership,
)


TEAM_TREE = {
    "Organisation": {
        "Colours": {
            "Blue": {},
            "Green": {},
            "Red": {
                "Deep red": {},
                "Faded red": {},
            },
        },
        "Tastes": {
            "Bitter": {},
            "Sweet": {},
            "Sour": {},
        },
        "Machines": {},
    }
}


USERS_AND_TEAMS = {
    "jerry": ["Deep red", "Blue"],
    "tina": ["Deep red"],
    "david_b": ["Deep red"],
    "chris": ["Deep red"],
    "lou": ["Tastes"],
    "sterling": ["Tastes"],
    "moe": ["Tastes"],
    "john": ["Tastes"],
    "jonathan": ["Blue"],
    "ernie": ["Blue"],
    "david_r": ["Blue", "Faded red"],
    "rik": ["Faded red"],
    "benjamin": ["Faded red"],
    "elliot": ["Faded red"],
    "greg": ["Faded red"],
    "florian": ["Machines"],
    "ralf": ["Machines"],
    "wolfgan": ["Machines"],
    "karl": ["Machines"],
    "john_l": ["Green"],
    "ringo": ["Green"],
    "paul": ["Green"],
    "george": ["Green"],
}


def ensure_team_tree(tree, parent=None):
    for team_name, children in tree.items():
        team, _ = Team.objects.get_or_create(name=team_name, defaults={"parent": parent})
        if team.parent_id != (parent.id if parent else None):
            team.parent = parent
            team.save(update_fields=["parent"])
        ensure_team_tree(children, parent=team)


def _identifier_for_index(index):
    adjective = DOT_IDENTIFIER_ADJECTIVES[index % len(DOT_IDENTIFIER_ADJECTIVES)]
    colour = DOT_IDENTIFIER_COLOURS[(index // len(DOT_IDENTIFIER_ADJECTIVES)) % len(DOT_IDENTIFIER_COLOURS)]
    noun = DOT_IDENTIFIER_NOUNS[
        (index // (len(DOT_IDENTIFIER_ADJECTIVES) * len(DOT_IDENTIFIER_COLOURS)))
        % len(DOT_IDENTIFIER_NOUNS)
    ]
    return f"{adjective}-{colour}-{noun}"


class Command(BaseCommand):
    help = "Seeds initial development teams, users, memberships, and dots."

    def handle(self, *args, **options):
        user_model = get_user_model()

        ensure_team_tree(TEAM_TREE)

        created_users = 0
        created_memberships = 0
        created_dots = 0

        rng = random.Random(20260518)
        user_model = get_user_model()
        users = {user.username: user for user in user_model.objects.all()}

        dot_index = 0

        for username, explicit_teams in USERS_AND_TEAMS.items():
            user, user_created = user_model.objects.get_or_create(username=username)
            if user_created:
                user.set_password(username)
                user.save(update_fields=["password"])
                created_users += 1
            users[username] = user

            for team_name in explicit_teams:
                team = Team.objects.get(name=team_name)
                _, membership_created = TeamMembership.objects.get_or_create(user=user, team=team)
                if membership_created:
                    created_memberships += 1

        for username, explicit_team_names in USERS_AND_TEAMS.items():
            user = users[username]
            explicit_teams = list(Team.objects.explicit_for_user(user).order_by("id"))
            visible_teams = list(Team.objects.visible_for_user(user, include_implicit=True).order_by("id"))
            implicit_only_teams = [
                team for team in visible_teams if team.id not in {t.id for t in explicit_teams}
            ]

            # Seed a small but useful deterministic set for each user.
            for dot_number in range(4):
                identifier = _identifier_for_index(dot_index)
                dot_index += 1

                dot, dot_created = Dot.objects.get_or_create(
                    identifier=identifier,
                    defaults={
                        "x": rng.randint(0, 100),
                        "y": rng.randint(0, 100),
                    },
                )
                if dot_created:
                    created_dots += 1

                if dot_number < 3:
                    target_teams = explicit_teams
                else:
                    target_teams = implicit_only_teams or explicit_teams

                dot.teams.set(target_teams)

                age_in_days = rng.randint(0, 6)
                created_at = timezone.now() - timedelta(
                    days=age_in_days,
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )
                Dot.objects.filter(pk=dot.pk).update(created_at=created_at)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed completed: "
                f"users created={created_users}, "
                f"memberships created={created_memberships}, "
                f"dots created={created_dots}"
            )
        )
