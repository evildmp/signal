from django.db import models
from django.contrib.auth import get_user_model


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
			explicit_teams = list(self.explicit_for_user(user))
			if not include_implicit:
				return self.filter(id__in=[team.id for team in explicit_teams])

			all_team_ids = {team.id for team in explicit_teams}
			for team in explicit_teams:
				all_team_ids.update(team.ancestor_ids())
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

	def ancestor_ids(self):
		ids = []
		current = self.parent
		while current is not None:
			ids.append(current.id)
			current = current.parent
		return ids


class TeamMembership(models.Model):
	user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="team_memberships")
	team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "team"], name="unique_user_team_membership"),
		]

	def __str__(self):
		return f"{self.user.username} -> {self.team.name}"
