from django import forms


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