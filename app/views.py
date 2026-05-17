from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from app.models import Team


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
    visible_team_ids = {team.id for team in visible_teams}

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "set_my_dots_only":
            my_dots_only = request.POST.get("enabled") in {"1", "true", "on"}
            if my_dots_only:
                selected_team_ids = set()
            else:
                selected_team_ids = {
                    int(team_id)
                    for team_id in request.POST.getlist("team_ids")
                    if team_id.isdigit()
                }
                selected_team_ids = selected_team_ids & visible_team_ids
        else:
            selected_team_ids = {
                int(team_id)
                for team_id in request.POST.getlist("team_ids")
                if team_id.isdigit()
            }
            selected_team_ids = selected_team_ids & visible_team_ids

            my_dots_only_requested = request.POST.get("my_dots_only") in {"1", "true", "on"}
            if selected_team_ids:
                my_dots_only = False
            elif my_dots_only_requested:
                my_dots_only = True
            else:
                my_dots_only = False
    else:
        my_dots_only = False
        selected_team_ids = set(
            Team.objects.explicit_for_user(request.user).values_list("id", flat=True)
        )
    return render(
        request,
        "app/home.html",
        {
            "visible_teams": visible_teams,
            "team_tree": team_tree,
            "selected_team_ids": selected_team_ids,
            "my_dots_only": my_dots_only,
        },
    )
