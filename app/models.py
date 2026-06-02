import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

import random


def reparent_to_grandparent(collector, field, sub_objs, using):
    teams = sub_objs.model._base_manager.using(using)
    deleted_parent_ids = list(sub_objs.values_list("parent_id", flat=True).distinct())
    parent_map = dict(
        teams.filter(id__in=deleted_parent_ids).values_list("id", "parent_id")
    )
    for deleted_parent_id, new_parent_id in parent_map.items():
        collector.add_field_update(
            field,
            new_parent_id,
            sub_objs.filter(parent_id=deleted_parent_id),
        )


class Team(models.Model):
    class TeamQuerySet(models.QuerySet):
        def explicit_for_user(self, user):
            explicit_team_ids = TeamMembership.objects.filter(user=user).values_list(
                "team_id", flat=True
            )
            return self.filter(id__in=explicit_team_ids)

        def visible_for_user(self, user, include_implicit=True):
            explicit_team_ids = list(
                self.explicit_for_user(user).values_list("id", flat=True)
            )
            if not include_implicit:
                return self.filter(id__in=explicit_team_ids)

            all_team_ids = set(explicit_team_ids)
            parent_by_id = dict(Team.objects.values_list("id", "parent_id"))
            for team_id in explicit_team_ids:
                parent_id = parent_by_id.get(team_id)
                while parent_id is not None:
                    all_team_ids.add(parent_id)
                    parent_id = parent_by_id.get(parent_id)

            return self.filter(id__in=all_team_ids)

    objects = TeamQuerySet.as_manager()

    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=reparent_to_grandparent,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="team_memberships"
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team"], name="unique_user_team_membership"
            ),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.team.name}"


class SignalOnboardingState(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="signal_onboarding_state",
    )
    using_signal_seen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}: using_signal_seen={self.using_signal_seen}"


DOT_IDENTIFIER_ADJECTIVES = (
    "calm",
    "bright",
    "quiet",
    "gentle",
    "steady",
    "brave",
    "kind",
    "clear",
    "quick",
    "warm",
)

DOT_IDENTIFIER_COLOURS = (
    "red",
    "blue",
    "green",
    "amber",
    "teal",
    "gray",
    "white",
    "black",
    "silver",
    "gold",
)

DOT_IDENTIFIER_NOUNS = (
    "moon",
    "tree",
    "frog",
    "sea",
    "hill",
    "stone",
    "river",
    "cloud",
    "leaf",
    "bird",
)


def generate_claim_token():
    return "-".join(
        [
            random.choice(DOT_IDENTIFIER_ADJECTIVES),
            random.choice(DOT_IDENTIFIER_COLOURS),
            random.choice(DOT_IDENTIFIER_NOUNS),
        ]
    )


# Alias preserved for historical migrations (0002, 0010).
generate_dot_identifier = generate_claim_token


FEELINGS = [
    "anxious",
    "bored",
    "calm",
    "cheerful",
    "confused",
    "content",
    "confident",
    "delighted",
    "disconnected",
    "dismayed",
    "drained",
    "embarrassed",
    "energised",
    "enraged",
    "excited",
    "frustrated",
    "grateful",
    "happy",
    "hopeful",
    "inspired",
    "irritated",
    "lonely",
    "melancholy",
    "optimistic",
    "overwhelmed",
    "peaceful",
    "proud",
    "quiet",
    "relaxed",
    "resigned",
    "restless",
    "sad",
    "tired",
    "vulnerable",
    "worried",
]

ACTION_SENTIMENTS = [
    "I need help",
    "I wish I could talk to someone",
    "I don't know how to talk about this",
    "I would love to talk about this",
    "I would like people to know",
    "I would be really happy to share my news",
]


class Dot(models.Model):
    x = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    y = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    owner_user = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_dots",
    )
    teams = models.ManyToManyField(Team, related_name="dots")
    claim_token = models.CharField(
        max_length=64, default=generate_claim_token, editable=False
    )
    ownership_token = models.UUIDField(default=uuid.uuid4, editable=False)
    feeling = models.JSONField(default=list, blank=True)
    action_sentiment = models.JSONField(default=list, blank=True)
    feeling_free_text = models.TextField(blank=True, default="")
    action_sentiment_free_text = models.TextField(blank=True, default="")
    flagged_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flagged_dots",
    )
    flagged_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.TextField(blank=True, default="")

    @property
    def is_flagged(self):
        return self.flagged_by_id is not None

    def clean(self):
        super().clean()
        if len(self.feeling) > 1:
            raise ValidationError({"feeling": "Only one feeling value is allowed."})

        if len(self.action_sentiment) > 1:
            raise ValidationError(
                {"action_sentiment": "Only one action sentiment value is allowed."}
            )

        invalid_feelings = [value for value in self.feeling if value not in FEELINGS]
        if invalid_feelings:
            raise ValidationError({"feeling": "Contains invalid feeling values."})

        invalid_action_sentiments = [
            value for value in self.action_sentiment if value not in ACTION_SENTIMENTS
        ]
        if invalid_action_sentiments:
            raise ValidationError(
                {"action_sentiment": "Contains invalid action sentiment values."}
            )
