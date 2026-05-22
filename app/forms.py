from django import forms

from app.models import ACTION_SENTIMENTS, FEELINGS, Team


class TeamFilterForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput(), initial="set_team_filters")
    team_ids = forms.MultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, team_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team_ids"].choices = [
            (str(team_id), team_name) for team_id, team_name in team_choices
        ]

    def cleaned_team_ids(self):
        return {int(team_id) for team_id in self.cleaned_data.get("team_ids", [])}


class MyDotsOnlyForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput(), initial="set_my_dots_only")
    enabled = forms.BooleanField(required=False)


class DrawerFilterForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput(), initial="set_filters")
    enabled = forms.BooleanField(required=False)
    team_ids = forms.MultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, team_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team_ids"].choices = [
            (str(team_id), team_name) for team_id, team_name in team_choices
        ]

    def cleaned_team_ids(self):
        return {int(team_id) for team_id in self.cleaned_data.get("team_ids", [])}


class DotEditorForm(forms.Form):
    include_name = forms.BooleanField(required=False)
    feeling = forms.MultipleChoiceField(
        required=False,
        choices=[(value, value) for value in FEELINGS],
        widget=forms.CheckboxSelectMultiple,
    )
    feeling_free_text = forms.CharField(required=False)
    action_sentiment = forms.MultipleChoiceField(
        required=False,
        choices=[(value, value) for value in ACTION_SENTIMENTS],
        widget=forms.CheckboxSelectMultiple,
    )
    action_sentiment_free_text = forms.CharField(required=False)
    private = forms.BooleanField(required=False)
    team_ids = forms.MultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, dot=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dot is not None:
            self.initial["include_name"] = dot.owner_user_id is not None
            self.initial["feeling"] = dot.feeling
            self.initial["feeling_free_text"] = dot.feeling_free_text
            self.initial["action_sentiment"] = dot.action_sentiment
            self.initial["action_sentiment_free_text"] = dot.action_sentiment_free_text
            self.initial["team_ids"] = [str(team_id) for team_id in dot.teams.values_list("id", flat=True)]
            self.initial["private"] = not dot.teams.exists()

        if user is not None:
            visible_teams = Team.objects.visible_for_user(user, include_implicit=True)
            self.fields["team_ids"].choices = [
                (str(team.id), team.name) for team in visible_teams
            ]

    def clean(self):
        cleaned_data = super().clean()
        selected_team_ids = cleaned_data.get("team_ids") or []

        # If no team destination is selected, treat the dot as private.
        if not cleaned_data.get("private") and not selected_team_ids:
            cleaned_data["private"] = True

        return cleaned_data

    def cleaned_team_ids(self):
        if self.cleaned_data.get("private"):
            return set()
        return {int(team_id) for team_id in self.cleaned_data.get("team_ids", [])}