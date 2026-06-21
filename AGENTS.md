## Working practices

Do not act unless the user gives an explicit imperative. You may discuss and plan, but do not implement a plan without explicit go-ahead.

Always create or update tests before writing functional code.

Work in small, discrete, complete steps. Each implementation step must leave the codebase independently committable and must not bundle unrelated fixes, refactors, configuration changes, dependency changes, test-environment changes, tooling changes, or documentation changes.

Do only the requested change. Do not make silent supporting changes. If implementation or validation exposes another issue, stop and report the issue, the failing command or symptom, and the smallest options for proceeding. Wait for explicit approval before making secondary changes.

After any failed validation command, do not edit files until you have decided whether the proposed fix is clearly within the current request's scope. If it is not clearly within scope, ask first.

Every final response must identify each changed file and why it belonged to the requested change.

Commit messages are in the past tense.

Do not use numbered lists in responses. Avoid lists unless actually listing things. Use normal prose and meaningful headings.
