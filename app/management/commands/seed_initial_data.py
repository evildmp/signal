from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from datetime import timedelta
import hashlib
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


USER_DOT_COUNTS = {
    "jerry": 5,
    "tina": 9,
    "david_b": 6,
    "chris": 7,
    "lou": 4,
    "sterling": 3,
    "moe": 2,
    "john": 6,
    "jonathan": 8,
    "ernie": 5,
    "david_r": 2,
    "rik": 5,
    "benjamin": 5,
    "elliot": 5,
    "greg": 5,
    "florian": 4,
    "ralf": 4,
    "wolfgan": 4,
    "karl": 4,
    "john_l": 8,
    "ringo": 7,
    "paul": 6,
    "george": 4,
}


EMOTION_POSITION_ANCHORS = {
    "empty": (8, 8),
    "sad": (18, 22),
    "melancholy": (20, 24),
    "lonely": (22, 30),
    "relaxed": (78, 22),
    "calm": (62, 28),
    "content": (64, 36),
    "tired": (45, 24),
    "quiet": (50, 30),
    "worried": (28, 58),
    "anxious": (32, 72),
    "irritated": (18, 78),
    "frustrated": (24, 74),
    "enraged": (10, 92),
    "optimistic": (64, 72),
    "excited": (84, 86),
    "energised": (82, 78),
    "cheerful": (72, 74),
    "happy": (76, 70),
    "hopeful": (66, 76),
    "delighted": (80, 82),
    "grateful": (68, 68),
    "inspired": (70, 84),
    "peaceful": (70, 34),
    "resigned": (30, 26),
    "overwhelmed": (38, 84),
}


USER_MOOD_PLANS = {
    "jerry": ["calm", "content", "worried", "optimistic", "tired"],
    "tina": [
        "excited",
        "anxious",
        "optimistic",
        "enraged",
        "cheerful",
        "overwhelmed",
        "inspired",
        "irritated",
        "happy",
    ],
    "david_b": ["calm", "content", "tired", "quiet", "worried", "relaxed"],
    "chris": [
        "cheerful",
        "optimistic",
        "happy",
        "hopeful",
        "delighted",
        "grateful",
        "excited",
    ],
    "lou": ["sad", "melancholy", "worried", "resigned"],
    "sterling": [None, None, None],
    "moe": [None, None],
    "john": [
        "custom:empty",
        "custom:Need alignment",
        "custom:Need focus",
        "custom:Need backup",
        "custom:Need context",
        "custom:Need a check-in",
    ],
    "jonathan": [
        "sad",
        "lonely",
        "melancholy",
        "optimistic",
        "excited",
        "sad",
        "hopeful",
        "anxious",
    ],
    "ernie": ["custom:cheerful", "calm", "content", "quiet", "optimistic"],
    "david_r": ["calm", "content"],
    "rik": ["excited", "sad", "optimistic", "melancholy", "energised"],
    "benjamin": ["happy", "sad", "hopeful", "anxious", "cheerful"],
    "elliot": ["optimistic", "lonely", "excited", "melancholy", "content"],
    "greg": ["grateful", "sad", "energised", "resigned", "hopeful"],
    "florian": ["calm", "content", "quiet", "worried"],
    "ralf": ["calm", "relaxed", "quiet", "content"],
    "wolfgan": ["content", "calm", "worried", "quiet"],
    "karl": ["calm", "content", "quiet", "relaxed"],
    "john_l": [
        "anxious",
        "irritated",
        "sad",
        "frustrated",
        "worried",
        "enraged",
        "melancholy",
        "overwhelmed",
    ],
    "ringo": ["content", "peaceful", "relaxed", "grateful", "happy", "calm", "hopeful"],
    "paul": ["happy", "excited", "optimistic", "inspired", "energised", "cheerful"],
    "george": ["sad", "resigned", "melancholy", "calm"],
}


USER_BASE_POSITIONS = {
    "john": (50, 72),
    "moe": (50, 50),
    "sterling": (50, 52),
    "david_b": (50, 34),
    "florian": (52, 46),
    "ralf": (50, 48),
    "wolfgan": (48, 48),
    "karl": (52, 44),
    "ernie": (52, 50),
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


def _deterministic_rng(*parts):
    key = "|".join(str(part) for part in parts)
    seed = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")
    return random.Random(seed)


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


def _resolve_dot_position(username, mood, dot_number):
    base_x, base_y = USER_BASE_POSITIONS.get(username, (50, 50))

    if mood:
        mood_key = mood.replace("custom:", "") if mood.startswith("custom:") else mood
        if mood_key in EMOTION_POSITION_ANCHORS:
            base_x, base_y = EMOTION_POSITION_ANCHORS[mood_key]

    jitter_rng = _deterministic_rng("dot-position", username, dot_number)
    x = int(round(base_x + jitter_rng.randint(-7, 7)))
    y = int(round(base_y + jitter_rng.randint(-7, 7)))
    x = max(0, min(100, x))
    y = max(0, min(100, y))
    return x, y


def _apply_dot_mood(dot, mood):
    if not mood:
        dot.feeling = []
        dot.feeling_free_text = ""
        return

    if mood.startswith("custom:"):
        dot.feeling = []
        dot.feeling_free_text = mood.split(":", 1)[1].strip()
        return

    if mood in FEELINGS:
        dot.feeling = [mood]
        dot.feeling_free_text = ""
        return

    dot.feeling = []
    dot.feeling_free_text = mood


class Command(BaseCommand):
    help = "Seeds initial development teams, users, memberships, and dots."

    def handle(self, *args, **options):
        ensure_team_tree(TEAM_TREE)
        all_team_names = list(Team.objects.order_by("id").values_list("name", flat=True))

        created_users = 0
        created_memberships = 0
        created_dots = 0

        rng = random.Random(20260518)
        user_model = get_user_model()
        users = {user.username: user for user in user_model.objects.all()}

        Dot.objects.all().delete()
        dot_index = 0
        run_anchor = timezone.now().replace(minute=0, second=0, microsecond=0)

        for username, explicit_teams in USERS_AND_TEAMS.items():
            user, user_created = user_model.objects.get_or_create(username=username)
            if user_created:
                user.set_password(username)
                user.save(update_fields=["password"])
                created_users += 1

            if username == "jerry":
                user_changed = False
                if not user.is_staff:
                    user.is_staff = True
                    user_changed = True
                if not user.is_superuser:
                    user.is_superuser = True
                    user_changed = True
                if user_changed:
                    user.save(update_fields=["is_staff", "is_superuser"])

            users[username] = user

            team_names = all_team_names if username == "jerry" else explicit_teams
            for team_name in team_names:
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

            dot_count = USER_DOT_COUNTS[username]
            mood_plan = USER_MOOD_PLANS[username]
            explicit_publication_indices = _pick_ratio_indices(
                _deterministic_rng("explicit", username), dot_count, 0.66
            )
            named_indices = _pick_ratio_indices(
                _deterministic_rng("named", username), dot_count, 0.30
            )
            action_indices = _pick_ratio_indices(
                _deterministic_rng("action", username), dot_count, 0.20
            )

            for dot_number in range(dot_count):
                claim_token = _identifier_for_index(dot_index)
                dot_index += 1
                mood = mood_plan[dot_number % len(mood_plan)]
                x, y = _resolve_dot_position(username, mood, dot_number)

                dot = Dot.objects.create(
                    claim_token=claim_token,
                    x=x,
                    y=y,
                )
                created_dots += 1

                if dot_number in explicit_publication_indices:
                    target_teams = explicit_teams
                else:
                    target_teams = _pick_alternative_teams(
                        _deterministic_rng("team-alternative", username, dot_number),
                        explicit_teams,
                        implicit_only_teams,
                    )

                dot.teams.set(target_teams)

                if dot_number in named_indices:
                    dot.owner_user = user
                else:
                    dot.owner_user = None

                _apply_dot_mood(dot, mood)

                if dot_number in action_indices:
                    action_rng = _deterministic_rng("action-text", username, dot_number)
                    if action_rng.random() < 0.3:
                        dot.action_sentiment = []
                        dot.action_sentiment_free_text = action_rng.choice(
                            [
                                "I could use a quick chat",
                                "I need a sounding board",
                                "I want help",
                                "I want to share this",
                            ]
                        )
                    else:
                        dot.action_sentiment = [action_rng.choice(ACTION_SENTIMENTS)]
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

                age_rng = _deterministic_rng("created-at", username, dot_number)
                age_in_days = age_rng.randint(0, 12)
                created_at = run_anchor - timedelta(
                    days=age_in_days,
                    hours=age_rng.randint(0, 23),
                    minutes=age_rng.randint(0, 59),
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
