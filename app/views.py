from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

import json
from datetime import timedelta

from app.forms import DotEditorForm, DrawerFilterForm, MyDotsOnlyForm, TeamFilterForm
from app.models import Dot, Team


def user_can_manage_dot(request, dot, claim_token=None):
    token = claim_token or ""
    return dot.owner_user_id == request.user.id or str(dot.claim_token) == token


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
            payload = {
                "action": "set_filters",
                "enabled": request.POST.get("enabled", ""),
                "team_ids": [str(team_id) for team_id in explicit_team_ids],
            }
            drawer_filter_form = DrawerFilterForm(payload, team_choices=team_choices)
        elif action == "set_team_filters":
            payload = {
                "action": "set_filters",
                "team_ids": request.POST.getlist("team_ids"),
            }
            drawer_filter_form = DrawerFilterForm(payload, team_choices=team_choices)
        else:
            drawer_filter_form = DrawerFilterForm(request.POST, team_choices=team_choices)

        if drawer_filter_form.is_valid():
            my_dots_only = drawer_filter_form.cleaned_data.get("enabled", False)
            selected_team_ids = set() if my_dots_only else drawer_filter_form.cleaned_team_ids()
        else:
            my_dots_only = False
            selected_team_ids = set()
    else:
        my_dots_only = False
        selected_team_ids = explicit_team_ids

    drawer_filter_form = DrawerFilterForm(
        initial={
            "enabled": my_dots_only,
            "team_ids": [str(team_id) for team_id in selected_team_ids],
        },
        team_choices=team_choices,
    )

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
            "drawer_filter_form": drawer_filter_form,
            "team_field_name": drawer_filter_form["team_ids"].html_name,
            "dots": dots,
        },
    )


@login_required
@require_POST
def create_dot(request):
    try:
        x = int(request.POST.get("x", ""))
        y = int(request.POST.get("y", ""))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid coordinates")

    if x < 0 or x > 100 or y < 0 or y > 100:
        return HttpResponseBadRequest("Coordinates must be 0–100")

    dot = Dot.objects.create(x=x, y=y)

    explicit_teams = list(Team.objects.explicit_for_user(request.user))
    dot.teams.set(explicit_teams)

    team_names = [team.name for team in explicit_teams]
    team_list = " and ".join(team_names)

    dot_html = (
        f'<span class="signal-dot" '
        f'data-dot-identifier="{dot.identifier}" '
        f'hx-get="/dot/{dot.identifier}/edit/" '
        f'hx-target="#dot-editor-host" '
        f'hx-swap="innerHTML" '
        f'style="left: {dot.x}%; bottom: {dot.y}%;" '
        f'title="{dot.identifier}"></span>'
    )

    # Determine label position class
    label_y = "below" if dot.y > 80 else "above"
    if dot.x < 20:
        label_x = "right"
    elif dot.x > 80:
        label_x = "left"
    else:
        label_x = "center"

    # When label goes left/right, always use "center" vertical mode (side labels are vertically centered)
    if label_x != "center":
        label_y = "side"
    label_class = f"signal-dot-label signal-dot-label--{label_y} signal-dot-label--x-{label_x}"

    notification_html = (
        f'<span class="{label_class}"'
        f' style="left: {dot.x}%; bottom: {dot.y}%;">'
        f'Published to <span class="team-names">{team_list}</span>.'
        '</span>'
    )

    response = HttpResponse(dot_html + notification_html)
    response["HX-Trigger-After-Swap"] = json.dumps({"dotClaimed": {"identifier": dot.identifier, "token": str(dot.claim_token)}})

    return response


@login_required
@require_POST
def move_dot(request, identifier):
    dot = get_object_or_404(Dot, identifier=identifier)

    claim_token = request.POST.get("claim_token", "")
    if not user_can_manage_dot(request, dot, claim_token):
        return HttpResponse(status=403)

    try:
        x = int(request.POST.get("x", ""))
        y = int(request.POST.get("y", ""))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid coordinates")

    if x < 0 or x > 100 or y < 0 or y > 100:
        return HttpResponseBadRequest("Coordinates must be 0-100")

    dot.x = x
    dot.y = y
    dot.save(update_fields=["x", "y"])

    return HttpResponse("")


@login_required
@require_POST
def delete_dot(request, identifier):
    dot = get_object_or_404(Dot, identifier=identifier)

    claim_token = request.POST.get("claim_token", "")
    if not user_can_manage_dot(request, dot, claim_token):
        return HttpResponse(status=403)

    dot.delete()

    response = HttpResponse("")
    response["HX-Trigger"] = json.dumps({"dotDeleted": {"identifier": identifier}})
    return response


@login_required
def dot_edit(request, identifier):
    dot = get_object_or_404(Dot, identifier=identifier)
    claim_token = request.POST.get("claim_token", "") if request.method == "POST" else request.GET.get("claim_token", "")
    if not user_can_manage_dot(request, dot, claim_token):
        return HttpResponse(status=403)

    visible_teams = list(Team.objects.visible_for_user(request.user, include_implicit=True))
    team_tree = build_team_tree(visible_teams)

    if request.method == "POST":
        form = DotEditorForm(request.POST, dot=dot, user=request.user)
        if form.is_valid():
            selected_team_ids = form.cleaned_team_ids()
            dot.teams.set(Team.objects.filter(id__in=selected_team_ids))
            dot.owner_user = request.user if form.cleaned_data.get("include_name", False) else None
            dot.feeling = form.cleaned_data.get("feeling", [])
            dot.feeling_free_text = form.cleaned_data.get("feeling_free_text", "")
            dot.action_sentiment = form.cleaned_data.get("action_sentiment", [])
            dot.action_sentiment_free_text = form.cleaned_data.get("action_sentiment_free_text", "")
            dot.save(
                update_fields=[
                    "owner_user",
                    "feeling",
                    "feeling_free_text",
                    "action_sentiment",
                    "action_sentiment_free_text",
                ]
            )
            return HttpResponse("")
        else:
            selected_team_ids = {
                int(team_id)
                for team_id in request.POST.getlist("team_ids")
                if str(team_id).isdigit()
            }
    else:
        form = DotEditorForm(dot=dot, user=request.user)
        selected_team_ids = set(dot.teams.values_list("id", flat=True))

    return render(
        request,
        "app/_dot_editor.html",
        {
            "dot": dot,
            "form": form,
            "team_tree": team_tree,
            "selected_team_ids": selected_team_ids,
            "team_field_name": form["team_ids"].html_name,
        },
    )
