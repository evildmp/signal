from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from datetime import timedelta
import random

from app.models import (
    ACTION_SENTIMENTS,
    DOT_IDENTIFIER_ADJECTIVES,
    DOT_IDENTIFIER_COLOURS,
    DOT_IDENTIFIER_NOUNS,
    Dot,
    FEELINGS,
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
        team, _ = Team.objects.get_or_create(
            name=team_name, defaults={"parent": parent}
        )
        if team.parent_id != (parent.id if parent else None):
            team.parent = parent
            team.save(update_fields=["parent"])
        ensure_team_tree(children, parent=team)


def _identifier_for_index(index):
    adjective = DOT_IDENTIFIER_ADJECTIVES[index % len(DOT_IDENTIFIER_ADJECTIVES)]
    colour = DOT_IDENTIFIER_COLOURS[
        (index // len(DOT_IDENTIFIER_ADJECTIVES)) % len(DOT_IDENTIFIER_COLOURS)
    ]
    noun = DOT_IDENTIFIER_NOUNS[
        (index // (len(DOT_IDENTIFIER_ADJECTIVES) * len(DOT_IDENTIFIER_COLOURS)))
        % len(DOT_IDENTIFIER_NOUNS)
    ]
    return f"{adjective}-{colour}-{noun}"


def _pick_ratio_indices(rng, total_count, ratio):
    target_count = int(round(total_count * ratio))
    target_count = max(0, min(total_count, target_count))
    indices = list(range(total_count))
    rng.shuffle(indices)
    return set(indices[:target_count])


def _pick_alternative_teams(rng, explicit_teams, implicit_only_teams):
    if implicit_only_teams and rng.random() < 0.5:
        chosen_implicit = [team for team in implicit_only_teams if rng.random() < 0.5]
        if not chosen_implicit:
            chosen_implicit = [rng.choice(implicit_only_teams)]

        chosen_explicit = [team for team in explicit_teams if rng.random() < 0.35]
        combined = {team.id: team for team in (chosen_implicit + chosen_explicit)}
        return [combined[team_id] for team_id in sorted(combined.keys())]

    if len(explicit_teams) > 1:
        subset = [team for team in explicit_teams if rng.random() < 0.6]
        if not subset:
            subset = [rng.choice(explicit_teams)]
        if len(subset) == len(explicit_teams):
            subset = subset[:-1]
        return sorted(subset, key=lambda team: team.id)

    return explicit_teams


class Command(BaseCommand):
    help = "Seeds initial development teams, users, memberships, and dots."

    def handle(self, *args, **options):
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
                _, membership_created = TeamMembership.objects.get_or_create(
                    user=user, team=team
                )
                if membership_created:
                    created_memberships += 1

        for username, explicit_team_names in USERS_AND_TEAMS.items():
            user = users[username]
            explicit_teams = list(Team.objects.explicit_for_user(user).order_by("id"))
            visible_teams = list(
                Team.objects.visible_for_user(user, include_implicit=True).order_by(
                    "id"
                )
            )
            implicit_only_teams = [
                team
                for team in visible_teams
                if team.id not in {t.id for t in explicit_teams}
            ]

            dot_count = rng.randint(4, 12)
            explicit_publication_indices = _pick_ratio_indices(rng, dot_count, 0.66)
            anonymous_indices = _pick_ratio_indices(rng, dot_count, 0.70)
            feeling_indices = _pick_ratio_indices(rng, dot_count, 0.40)
            action_indices = _pick_ratio_indices(rng, dot_count, 0.20)

            for dot_number in range(dot_count):
                claim_token = _identifier_for_index(dot_index)
                dot_index += 1

                dot, dot_created = Dot.objects.get_or_create(
                    claim_token=claim_token,
                    defaults={
                        "x": rng.randint(0, 100),
                        "y": rng.randint(0, 100),
                    },
                )
                if dot_created:
                    created_dots += 1

                if dot_number in explicit_publication_indices:
                    target_teams = explicit_teams
                else:
                    target_teams = _pick_alternative_teams(
                        rng,
                        explicit_teams,
                        implicit_only_teams,
                    )

                dot.teams.set(target_teams)

                if dot_number in anonymous_indices:
                    dot.owner_user = None
                else:
                    dot.owner_user = user

                if dot_number in feeling_indices:
                    if rng.random() < 0.3:
                        dot.feeling = []
                        dot.feeling_free_text = rng.choice(
                            [
                                "hard to name",
                                "mixed feelings",
                                "in between",
                                "processing",
                                "uncertain",
                            ]
                        )
                    else:
                        dot.feeling = [rng.choice(FEELINGS)]
                        dot.feeling_free_text = ""
                else:
                    dot.feeling = []
                    dot.feeling_free_text = ""

                if dot_number in action_indices:
                    if rng.random() < 0.3:
                        dot.action_sentiment = []
                        dot.action_sentiment_free_text = rng.choice(
                            [
                                "I could use a quick chat",
                                "I need a sounding board",
                                "I want help",
                                "I want to share this",
                            ]
                        )
                    else:
                        dot.action_sentiment = [rng.choice(ACTION_SENTIMENTS)]
                        dot.action_sentiment_free_text = ""
                else:
                    dot.action_sentiment = []
                    dot.action_sentiment_free_text = ""

                dot.save(
                    update_fields=[
                        "owner_user",
                        "feeling",
                        "feeling_free_text",
                        "action_sentiment",
                        "action_sentiment_free_text",
                    ]
                )

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
