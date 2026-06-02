from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .models import Dot, SignalOnboardingState, Team, TeamMembership


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


@admin.register(Dot)
class DotAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"x",
		"y",
		"owner_user",
		"flagged_by",
		"flagged_at",
	)
	readonly_fields = (
		"claim_token",
		"ownership_token",
		"flagged_by",
		"flagged_at",
		"flag_reason",
	)
	raw_id_fields = ("owner_user", "flagged_by")
	filter_horizontal = ("teams",)

	def get_urls(self):
		info = self.opts.app_label, self.opts.model_name
		custom_urls = [
			path(
				"<int:dot_id>/unflag/",
				self.admin_site.admin_view(self.unflag_view),
				name="%s_%s_unflag" % info,
			),
		]
		return custom_urls + super().get_urls()

	def unflag_view(self, request, dot_id):
		dot = get_object_or_404(Dot, id=dot_id)
		dot.flagged_by = None
		dot.flagged_at = None
		dot.flag_reason = ""
		dot.save(update_fields=["flagged_by", "flagged_at", "flag_reason"])
		self.message_user(request, "Dot was unflagged.")
		return redirect("admin:app_dot_change", object_id=dot.id)


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class SignalUserAdmin(UserAdmin):
	inlines = [TeamMembershipInlineForUser]
