# Plan

This plan exists to keep an LLM agent on track.

1. [x] Scaffold the project foundation: Django project, app, config, pytest/django-pytest, Playwright, templates, static files, and Vanilla integration. This is the only blocking setup phase.

2. [x] Model the core domain: hierarchical teams, explicit memberships, dots, team publication, claim tokens, identifier generation, implied ancestor membership, and seven-day fade logic.

3. [x] Extend the domain model to cover sentiments: two lists (feelings; relational wishes), free-text option, and association with dots.

4. [x] Add a seed data management command: organisation tree and users.

5. [x] Implement authentication as the first end-to-end slice so the rest of the story can be verified in the browser.

6. [x] Build the main view and drawer: default team selection for explicit memberships, display of implicit parent teams, Organisation descendant filtering, and My dots only clearing other selections.

7. [x] Add owned-dot behaviour: create by clicking/tapping the grid, publish to currently selected teams, persist claim tokens client-side, and visually pulse owned dots.

8. [x] Add dot editing: edit owned dots, toggle "include my name", change published teams within the user's allowed hierarchy, and manage sentiments/free text (including one sentiment per field).

9. [x] Add owned-dot deletion and repositioning: delete owned dots and drag to move them.

10. [x] Add published-dot label display: show name label only when enabled, render selected sentiments/free text clearly, and keep labels readable without breaking click/drag interactions.

11. [x] Add claim-by-identifier for unowned dots: prompt for the identifier, issue a claim token if it matches, then allow edits.

12. [x] Add an initial help screen that shows the first a user encounters the application; a "Using Signal" button or link appears in case the user needs to see it again.

13. [ ] Add Team admin membership editing: in Team admin, allow adding/removing user memberships for the selected team; do the same for User admin; create tests for both.