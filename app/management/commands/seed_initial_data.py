from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app.models import Team, TeamMembership


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
    "david_r": ["Blue"],
}


def ensure_team_tree(tree, parent=None):
    for team_name, children in tree.items():
        team, _ = Team.objects.get_or_create(name=team_name, defaults={"parent": parent})
        if team.parent_id != (parent.id if parent else None):
            team.parent = parent
            team.save(update_fields=["parent"])
        ensure_team_tree(children, parent=team)


class Command(BaseCommand):
    help = "Seeds initial development teams and users."

    def handle(self, *args, **options):
        user_model = get_user_model()

        ensure_team_tree(TEAM_TREE)

        created_users = 0
        created_memberships = 0

        for username, explicit_teams in USERS_AND_TEAMS.items():
            user, user_created = user_model.objects.get_or_create(username=username)
            if user_created:
                user.set_password(username)
                user.save(update_fields=["password"])
                created_users += 1

            for team_name in explicit_teams:
                team = Team.objects.get(name=team_name)
                _, membership_created = TeamMembership.objects.get_or_create(user=user, team=team)
                if membership_created:
                    created_memberships += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed completed: users created={created_users}, memberships created={created_memberships}"
            )
        )
