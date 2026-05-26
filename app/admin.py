from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import SignalOnboardingState, Team, TeamMembership


class TeamMembershipInlineForTeam(admin.TabularInline):
	model = TeamMembership
	fk_name = "team"
	extra = 0
	raw_id_fields = ("user",)


class TeamMembershipInlineForUser(admin.TabularInline):
	model = TeamMembership
	fk_name = "user"
	extra = 0
	raw_id_fields = ("team",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
	list_display = ("name", "parent")
	search_fields = ("name",)
	inlines = [TeamMembershipInlineForTeam]


@admin.register(SignalOnboardingState)
class SignalOnboardingStateAdmin(admin.ModelAdmin):
	list_display = ("user", "using_signal_seen")
	raw_id_fields = ("user",)


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class SignalUserAdmin(UserAdmin):
	inlines = [TeamMembershipInlineForUser]
