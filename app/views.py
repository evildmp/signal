from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction
from django.db.models import Q

import json
from datetime import timedelta
from uuid import UUID

from app.forms import DotEditorForm, DrawerFilterForm
from app.models import Dot, Team

LABEL_LEFT_EDGE_THRESHOLD = 20
LABEL_RIGHT_EDGE_THRESHOLD = 80
LABEL_TOP_EDGE_THRESHOLD = 80


def user_can_manage_dot(request, dot, ownership_token=None):
    token = ownership_token or ""
    return dot.owner_user_id == request.user.id or str(dot.ownership_token) == token


def request_ownership_token(request):
    header_token = request.headers.get("X-Ownership-Token", "")
    if header_token:
        return header_token

    if request.method == "POST":
        return request.POST.get("ownership_token", "")

    return ""


def build_dot_label_position_class_from_coordinates(x, y):
    label_y = "below" if y > LABEL_TOP_EDGE_THRESHOLD else "above"
    if x < LABEL_LEFT_EDGE_THRESHOLD:
        label_x = "right"
    elif x > LABEL_RIGHT_EDGE_THRESHOLD:
        label_x = "left"
    else:
        label_x = "center"

    if label_x != "center":
        label_y = "side"

    return f"signal-dot-label--{label_y} signal-dot-label--x-{label_x}"


def build_dot_label_position_class(dot):
    return build_dot_label_position_class_from_coordinates(dot.x, dot.y)


def _split_label_values(value):
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _dedupe_label_values(values):
    deduped = []
    seen = set()

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)

    return deduped


def build_published_label_groups(dot):
    feeling_values = _dedupe_label_values(
        list(dot.feeling) + _split_label_values(dot.feeling_free_text)
    )
    action_values = _dedupe_label_values(
        list(dot.action_sentiment) + _split_label_values(dot.action_sentiment_free_text)
    )

    return {
        "username": dot.owner_user.username if dot.owner_user else "",
        "feelings": ", ".join(feeling_values),
        "actions": ", ".join(action_values),
    }


def build_published_label_parts(dot):
    groups = build_published_label_groups(dot)
    parts = []

    if groups["username"]:
        parts.append(groups["username"])
    if groups["feelings"]:
        parts.append(groups["feelings"])
    if groups["actions"]:
        parts.append(groups["actions"])

    return parts


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
@require_http_methods(["GET", "POST"])
def home(request):
    visible_teams = list(
        Team.objects.visible_for_user(request.user, include_implicit=True)
    )
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
            drawer_filter_form = DrawerFilterForm(
                request.POST, team_choices=team_choices
            )

        if drawer_filter_form.is_valid():
            my_dots_only = drawer_filter_form.cleaned_data.get("enabled", False)
            selected_team_ids = (
                set() if my_dots_only else drawer_filter_form.cleaned_team_ids()
            )
        else:
            my_dots_only = False
            selected_team_ids = set()
    else:
        my_dots_only = False
        selected_team_ids = explicit_team_ids

    if request.method != "POST":
        drawer_filter_form = DrawerFilterForm(
            initial={
                "enabled": my_dots_only,
                "team_ids": [str(team_id) for team_id in selected_team_ids],
            },
            team_choices=team_choices,
        )

    visibility_cutoff = timezone.now() - timedelta(days=7)
    if my_dots_only:
        raw_tokens = (
            request.POST.getlist("ownership_token") if request.method == "POST" else []
        )
        ownership_tokens = []
        for raw_token in raw_tokens:
            try:
                ownership_tokens.append(UUID(str(raw_token)))
            except (TypeError, ValueError):
                continue

        management_filter = Q(owner_user=request.user)
        if ownership_tokens:
            management_filter |= Q(ownership_token__in=ownership_tokens)

        dots = list(
            Dot.objects.filter(management_filter, created_at__gte=visibility_cutoff)
            .select_related("owner_user")
            .distinct()
            .order_by("id")
        )
    elif selected_team_ids:
        dots = list(
            Dot.objects.filter(
                teams__id__in=selected_team_ids, created_at__gte=visibility_cutoff
            )
            .select_related("owner_user")
            .distinct()
            .order_by("id")
        )
    else:
        dots = []

    for dot in dots:
        dot.published_label_groups = build_published_label_groups(dot)
        dot.published_label_parts = build_published_label_parts(dot)
        dot.published_label_class = build_dot_label_position_class(dot)

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
            "label_left_edge_threshold": LABEL_LEFT_EDGE_THRESHOLD,
            "label_right_edge_threshold": LABEL_RIGHT_EDGE_THRESHOLD,
            "label_top_edge_threshold": LABEL_TOP_EDGE_THRESHOLD,
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

    dot.published_label_class = build_dot_label_position_class(dot)
    dot_html = render_to_string(
        "app/_dot.html",
        {"dot": dot},
        request=request,
    )
    notification_html = render_to_string(
        "app/_dot_notification.html",
        {"dot": dot, "team_list": team_list},
        request=request,
    )

    response = HttpResponse(dot_html + notification_html)
    response["HX-Trigger-After-Swap"] = json.dumps(
        {"dotClaimed": {"dotId": dot.id, "token": str(dot.ownership_token)}}
    )

    return response


@login_required
@require_POST
def move_dot(request, dot_id):
    dot = get_object_or_404(Dot, id=dot_id)

    ownership_token = request_ownership_token(request)
    if not user_can_manage_dot(request, dot, ownership_token):
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
def delete_dot(request, dot_id):
    dot = get_object_or_404(Dot, id=dot_id)

    ownership_token = request_ownership_token(request)
    if not user_can_manage_dot(request, dot, ownership_token):
        return HttpResponse(status=403)

    dot.delete()

    response = HttpResponse("")
    response["HX-Trigger"] = json.dumps({"dotDeleted": {"dotId": dot_id}})
    return response


@login_required
@require_http_methods(["GET", "POST"])
def dot_edit(request, dot_id):
    dot = get_object_or_404(Dot, id=dot_id)
    ownership_token = request_ownership_token(request)
    if not user_can_manage_dot(request, dot, ownership_token):
        return HttpResponse(status=403)

    visible_teams = list(
        Team.objects.visible_for_user(request.user, include_implicit=True)
    )
    team_tree = build_team_tree(visible_teams)

    if request.method == "POST":
        form = DotEditorForm(request.POST, dot=dot, user=request.user)
        if form.is_valid():
            selected_team_ids = form.cleaned_team_ids()
            with transaction.atomic():
                dot.teams.set(Team.objects.filter(id__in=selected_team_ids))
                dot.owner_user = (
                    request.user if form.cleaned_data.get("include_name", False) else None
                )
                dot.feeling = form.cleaned_data.get("feeling", [])
                dot.feeling_free_text = form.cleaned_data.get("feeling_free_text", "")
                dot.action_sentiment = form.cleaned_data.get("action_sentiment", [])
                dot.action_sentiment_free_text = form.cleaned_data.get(
                    "action_sentiment_free_text", ""
                )
                dot.save(
                    update_fields=[
                        "owner_user",
                        "feeling",
                        "feeling_free_text",
                        "action_sentiment",
                        "action_sentiment_free_text",
                    ]
                )

            payload = {
                "dotId": dot.id,
                "ownedByUser": dot.owner_user_id == request.user.id,
                "labelParts": build_published_label_parts(dot),
                "labelGroups": build_published_label_groups(dot),
                "labelClass": build_dot_label_position_class(dot),
            }
            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({"dotUpdated": payload})
            return response
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
