# Plan

1. [x] Scaffold the project foundation: Django project, app, config, pytest/django-pytest, Playwright, templates, static files, and Vanilla integration. This is the only blocking setup phase.

2. [x] Model the core domain: hierarchical teams, explicit memberships, dots, team publication, claim tokens, identifier generation, implied ancestor membership, and seven-day fade logic.

3. [ ] Extend the domain model to cover sentiments: two lists (feelings; relational wishes), free-text option, and association with dots.

4. [x] Add a seed data management command: organisation tree and users.

5. [ ] Extend seed data to produce realistic dots matching the brief's counts and percentages (4-12 dots per user over the last week, 66% explicit teams, 70% anonymous, 40% feelings, 20% relational wishes).

6. [x] Implement authentication as the first end-to-end slice so the rest of the story can be verified in the browser.

7. [x] Build the main view and drawer: default team selection for explicit memberships, display of implicit parent teams, Organisation descendant filtering, and My dots only clearing other selections.

8. [x] Add owned-dot behaviour: create by clicking/tapping the grid, publish to currently selected teams, persist claim tokens client-side, and visually pulse owned dots.

9. [ ] Add dot management: edit/delete, show identifier, toggle published name, change published teams within the user's allowed hierarchy, manage sentiments/free text, and drag-to-move.

10. [ ] Add claim-by-identifier for unowned dots: prompt for the identifier, issue a claim token if it matches, then allow edits.

11. [ ] Harden and verify: seed determinism, anonymity guarantees, responsive drawer behaviour, and full story coverage.
