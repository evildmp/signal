from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from datetime import timedelta

from app.forms import MyDotsOnlyForm, TeamFilterForm
from app.models import Dot, Team


def build_team_tree(teams):
    nodes_by_id = {
        team.id: {
            "team": team,
            "children": [],
        }
        for team in teams
    }

    roots = []
    for team in teams:
        node = nodes_by_id[team.id]
        if team.parent_id in nodes_by_id:
            nodes_by_id[team.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


@login_required
def home(request):
    visible_teams = list(Team.objects.visible_for_user(request.user, include_implicit=True))
    team_tree = build_team_tree(visible_teams)
    team_choices = [(team.id, team.name) for team in visible_teams]
    explicit_team_ids = set(
        Team.objects.explicit_for_user(request.user).values_list("id", flat=True)
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "set_my_dots_only":
            my_dots_only_form = MyDotsOnlyForm(request.POST)
            team_filter_form = TeamFilterForm(team_choices=team_choices)
            my_dots_only_form.is_valid()

            my_dots_only = my_dots_only_form.cleaned_data.get("enabled", False)
            if my_dots_only_form.is_valid() and my_dots_only:
                selected_team_ids = set()
            else:
                selected_team_ids = explicit_team_ids
        else:
            team_filter_form = TeamFilterForm(request.POST, team_choices=team_choices)
            my_dots_only_form = MyDotsOnlyForm()
            team_filter_form.is_valid()

            selected_team_ids = (
                team_filter_form.cleaned_team_ids()
                if team_filter_form.is_valid()
                else set()
            )
            my_dots_only = False
    else:
        my_dots_only = False
        selected_team_ids = explicit_team_ids
        team_filter_form = TeamFilterForm(
            initial={"team_ids": [str(team_id) for team_id in selected_team_ids]},
            team_choices=team_choices,
        )
        my_dots_only_form = MyDotsOnlyForm(initial={"enabled": my_dots_only})

    if request.method == "POST":
        if action == "set_my_dots_only":
            my_dots_only_form = MyDotsOnlyForm(initial={"enabled": my_dots_only})
            team_filter_form = TeamFilterForm(
                initial={"team_ids": [str(team_id) for team_id in selected_team_ids]},
                team_choices=team_choices,
            )
        else:
            team_filter_form = TeamFilterForm(
                initial={"team_ids": [str(team_id) for team_id in selected_team_ids]},
                team_choices=team_choices,
            )
            my_dots_only_form = MyDotsOnlyForm(initial={"enabled": my_dots_only})

    visibility_cutoff = timezone.now() - timedelta(days=7)
    if selected_team_ids:
        dots = (
            Dot.objects.filter(teams__id__in=selected_team_ids, created_at__gte=visibility_cutoff)
            .distinct()
            .order_by("identifier")
        )
    else:
        dots = Dot.objects.none()

    return render(
        request,
        "app/home.html",
        {
            "visible_teams": visible_teams,
            "team_tree": team_tree,
            "selected_team_ids": selected_team_ids,
            "my_dots_only": my_dots_only,
            "team_filter_form": team_filter_form,
            "team_field_name": team_filter_form["team_ids"].html_name,
            "my_dots_only_form": my_dots_only_form,
            "dots": dots,
        },
    )
