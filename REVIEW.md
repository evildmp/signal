# Review

## Your instructions

I want you to take a hard look at the JS code in this project.

I think it can probably be:

simplified
refactored
reorganised

I think that there are quite likely constructs that could be replaced with simpler, cleaner HTMX, and likely there is logic in the JS that could just as easily or better be performed in the Python/Django backend.

I also don't like the fact there is a dot_editor.js file and also a lot of JS in home.html.

All JS should be cleanly placed in separate JS files where appropriate.

Do it as if you were a senior programmer tasked with assessing quality and good practice.

Take an adversarial stance. Your job is to point out anything that could or should be improved. It could be at any level from the architectural to small details of implementation.

Make a report, with detailed recommendations. Don't hesitate to recommend substantial changes in approach if that seems appropriate.

If you see any silly mistakes or potential for error, highlight it.

Take note of this in AGENTS:

You will not use numbered lists in your responses, because they are irritating. Don't use lists at all unless you are actually listing things. When explaining, just write normal prose. Use meaningful headings where appropriate.

Append your review to this file, under a heading ## Review [date]. After each thing that you think needs to be addressed, add a checkbox [ ] (on a new line) so I can note how it has been resolved.

---

## Review 3 June 2026

### Architecture: inline JS vs external files

The project's stated principle is "HTMX for interaction — JavaScript code should be kept to an absolute necessary minimum". The reality falls short. `home.html` contains three separate `<script>` blocks totalling roughly five hundred lines of inline JavaScript. That is more than the external `dot_editor.js` file which weighs in at around one hundred and forty lines. The inline code handles navigation, onboarding, drawer filtering, dot claiming visual state, drag-and-drop, grid-click creation, label positioning, and event-driven DOM surgery for updates and deletions.

All of this inline code should be extracted into separate, focused JS files. Inline scripts defeat caching, complicate CSP configuration, make the template harder to read, and blur the boundary between server-rendered markup and client behaviour.

[x] Extract all inline JS from `home.html` into separate .js files

### Duplicated label-positioning logic

The function `labelPositionClass()` in `grid.js` is a verbatim JavaScript reimplementation of `build_dot_label_position_class_from_coordinates()` in `views.py`. The Python version computes the class server-side and stores it on the dot as `published_label_class`. The JS version recomputes it client-side during drag and after updates.

The JS even reads the threshold constants from data attributes embedded in the HTML — the same values that travel from Python constants, through the template context, into data attributes, only to be parsed back into numbers in JS. The drag path has a legitimate need for client-side positioning for instant visual feedback. But the `dotUpdated` handler already receives `labelClass` in the event payload from the server and ignores it, recomputing instead.

[x] Deduplicate: use server-computed `labelClass` from event payload instead of recomputing in JS (except during live drag)

### `dotUpdated` event handler does unnecessary client-side DOM construction

When a dot is saved, the server responds with an `HX-Trigger` header containing a `dotUpdated` event with `labelGroups`, `labelParts`, `labelClass`, and `notificationHtml`. The JS handler tears down and rebuilds the published label DOM manually: creating elements, appending children, setting text content, reading CSS custom properties to compute position classes.

This is exactly the kind of client-side rendering that HTMX is designed to eliminate. The server could return an OOB (out-of-band) swap element for the label, or use `HX-Reswap`/`HX-Retarget` to replace the label markup directly. The notification label (`signal-dot-label`) is already rendered server-side as HTML and passed in the payload — the published label should be treated the same way.

[x] Replace client-side label DOM construction with server-rendered HTMX OOB swaps or targeted responses

### Dead code: `dot.style.left` / `dot.style.bottom` fallback

In the `dotUpdated` handler, the code attempts to read position from `dot.style.left` and `dot.style.bottom` as a fallback for CSS custom properties. Dot elements are positioned exclusively via `--dot-x` and `--dot-y` custom properties set through the `style` attribute. The `left` and `bottom` style properties are never set on dot elements. These lines always produce `NaN`, so the `Number.isFinite` checks always fall through to the custom-property path. This code cannot work and should not exist.

[x] Remove dead `dot.style.left`/`dot.style.bottom` position fallback

### `localStorage` access is scattered and repetitive

The pattern `JSON.parse(localStorage.getItem('dotTokens') || '{}')` appears four times in `grid.js`, once in `drawer_filter.js`, and once in `dot_editor.js`. Each call site parses, defaults, and catches independently. There is no shared helper and no caching. If the serialisation format ever needed to change, six sites would need updating.

A single small module should export `get(id)`, `set(id, value)`, `remove(id)`, and `all()`. Every consumer imports from it.

[x] Create a shared tokens module for localStorage ownership token access

### Ownership token injection is scattered across multiple mechanisms

Ownership tokens are injected into requests in four different ways: hidden `<input>` elements appended to the drawer filter form; `htmx:configRequest` header injection for edit requests; `hx-vals` JSON on the delete button; and explicit `values` in `htmx.ajax` calls for drag-move. A single `htmx:configRequest` listener that inspects the request path and injects the relevant token into headers for all dot-mutating requests would replace all four mechanisms.

[x] Consolidate ownership token injection into a single `htmx:configRequest` listener

### Drawer mutual-exclusion uses fragile capture-phase hack

The drawer filter script uses a capture-phase `change` listener so mutual exclusion between "My dots only" and team checkboxes runs before HTMX serialises the form. This depends on an undocumented HTMX implementation detail — that `hx-trigger="change"` serialises in the bubble phase. The server already has `cleaned_team_ids()` on `DrawerFilterForm` and the `home` view already handles the `my_dots_only` vs `selected_team_ids` logic. The JS pre-clearing is redundant if the server simply respects the `action` field.

[x] Move drawer mutual-exclusion logic to server-side; remove capture-phase checkbox clearing JS

### Use of `var` throughout

All five JS files use `var` exclusively. Since the project targets modern browsers — HTMX, CSS custom properties, `<dialog>` — there is no reason not to use `let` and `const`. `var` has function scope rather than block scope, which can lead to subtle bugs in the larger files like `grid.js` where variable names could collide across different logical blocks.

[x] Replace `var` with `let`/`const` throughout

### Drag implementation uses mouse events only

The drag system listens for `mousedown`, `mousemove`, and `mouseup`. Touch devices cannot drag dots. Pointer events (`pointerdown`, `pointermove`, `pointerup`) unify mouse and touch and are supported in every browser that supports the other modern features already in use. `setPointerCapture` would also prevent drag breakage if the pointer leaves the grid element.

[ ] Replace mouse events with pointer events for drag to support touch devices

### Grid click suppression relies on a `setTimeout(0)` race

The `suppressNextGridClick` boolean is set in `endDrag()` and cleared via `setTimeout(..., 0)`. This works because click fires after mouseup in the event loop, but it is a timing-dependent hack. A cleaner pattern: track whether a meaningful drag occurred in the drag state, and check that directly in the grid's `click` handler instead of relying on event loop ordering.

[ ] Replace `suppressNextGridClick` / `setTimeout(0)` with an explicit gesture-tracking check

### All five JS files use IIFE wrappers

Every JS file wraps its content in `(function () { ... })();`. For `<script src="...">` tags (not modules), this provides scope isolation and prevents variable leakage between files — so there is a legitimate reason for them. If the files were converted to proper modules (`<script type="module">`), the IIFEs would be unnecessary.

[ ] Convert scripts to ES modules and remove the IIFE

### `wireSentimentPicker` is a large monolithic function

At roughly ninety lines, this function handles checkbox rendering, chip creation, chip removal, free-text input (Enter/comma/blur), and initial state synchronisation. It should be split into smaller, testable pieces: a `ChipList` abstraction with `add`, `remove`, and `getValues` methods, plus a separate binding function that wires checkbox changes and keyboard events to the chip list.

[ ] Refactor `wireSentimentPicker` into smaller, composable functions

### Label threshold constants are defined in two places

`LABEL_LEFT_EDGE_THRESHOLD`, `LABEL_RIGHT_EDGE_THRESHOLD`, and `LABEL_TOP_EDGE_THRESHOLD` are module-level constants in `views.py`. They are passed as template context, embedded as data attributes on the grid, and parsed back into numbers by `thresholdFromData()` in JS — which also has hardcoded fallback values that must be manually kept in sync with the Python constants.

[ ] Extract label threshold fallbacks to a single shared configuration or remove the JS fallback defaults entirely

### `clearTransientDotLabels` uses a semantically ambiguous class selector

The function `clearTransientDotLabels()` removes all elements matching `.signal-dot-label`. This class is used exclusively by the notification template, so it works, but the selector is semantically ambiguous — if a future developer adds another element with that class, it would be silently destroyed. The intent should be explicit.

[ ] Rename or scope `clearTransientDotLabels` to target notification elements specifically

### The onboarding dialog dismiss call should use HTMX

The dialog content is already server-rendered as part of the page — there is nothing to load asynchronously, so replacing content loading with HTMX is not the right recommendation here. The show/hide JS is small and legitimate. What is wrong is the dismiss call: it manually invokes `htmx.ajax` and reads the CSRF token from a meta tag. A simple form with `hx-post` and `hx-swap="none"` on the continue button would replace those lines entirely without any JS.

[ ] Replace manual `htmx.ajax` dismiss call with a `hx-post` form submission

### `dotDeleted` handler does DOM removal that HTMX could handle

When a dot is deleted the server returns empty content with an `HX-Trigger` header. The JS handler manually finds and removes the dot element, its label, and cleans localStorage. The dot and its label could instead be targeted with `hx-swap="delete"` or `hx-swap="outerHTML"` returning empty content. The localStorage cleanup would still need JS, but the DOM removal wouldn't.

[ ] Replace DOM removal in `dotDeleted` handler with HTMX-native swap mechanisms

### `signal-dot--claimed` uses `z-index: 12` as a magic number

Claimed dots get `z-index: 12`, regular dots `z-index: 2`, published labels `z-index: 6`, notification labels `z-index: 10`, and the claimed-dot halo pseudo-element `z-index: 1`. These values form an undocumented layering system. Any new layered element requires reverse-engineering the stack.

[ ] Document or systematise the z-index scale with named CSS custom properties

### `labelParts` in the `dotUpdated` payload is dead data

The `build_dot_updated_payload` function in `views.py` includes `labelParts` alongside `labelGroups` in the JSON payload sent on every dot save. The JS `dotUpdated` handler uses `labelGroups` and never reads `labelParts`. It is serialised and transmitted on every edit without being consumed. `build_dot_updated_payload` should be audited and `labelParts` removed from the payload.

[ ] Remove unused `labelParts` from `dotUpdated` event payload

### Two `dotClaimed` listeners are split across separate script blocks

The two `dotClaimed` event listeners on `document.body` both live in `grid.js` but are separated by hundreds of lines of unrelated code, making the full handling of the event invisible at any single point of reading. Both should be together, or collapsed into one listener.

[ ] Consolidate the two `dotClaimed` event listeners into one place

### Inline `onclick` in `_dot_editor.html`

The cancel button in `_dot_editor.html` uses `onclick="this.closest('dialog').close()"` — an inline event handler. The review criticised inline scripts in `home.html` but this one was missed. It should be wired in JS alongside the rest of the dialog behaviour.

[ ] Replace inline `onclick` on cancel button with a JS event listener

### Ownership tokens accumulate in localStorage without expiry

The `dotDeleted` handler cleans up a token when a dot is explicitly deleted. But dots that age out of the 14-day visibility window disappear from the view without any event firing, so their tokens are never removed. Every dot a user has ever created in this browser leaves a token in localStorage indefinitely. The drawer filter form submits all of them as hidden inputs on every filter change — a payload that grows without bound and reveals historical dot activity. A simple approach would be to store tokens with a creation timestamp and evict any older than the visibility window.

[ ] Expire ownership tokens from localStorage after the visibility window has passed

### `ownershipTokenForDotId` has a hidden DOM dependency

The function name implies a data lookup by ID, but it first queries the DOM for the corresponding element, then reads localStorage. If the dot element has been removed from the DOM before this is called — possible in edge cases after deletion — it silently returns an empty string. The DOM lookup and the token lookup should be separated, or the function should be renamed to reflect what it actually does.

[ ] Separate DOM lookup from token lookup in `ownershipTokenForDotId`

### `syncOwnershipToken` and `syncOwnershipTokens` are easy to confuse

`dot_editor.js` has `syncOwnershipToken` (singular) and `drawer_filter.js` has `syncOwnershipTokens` (plural). The similar names describe materially different operations: one reads a single token for a specific dot and populates a form input; the other reads all stored tokens and generates a set of hidden inputs for the drawer form. The naming obscures this distinction when reading across the codebase.

[ ] Rename to make the distinction between single-token and all-tokens operations clear


## Review questions to be answered in due course

[ ] is all of onboarding.js really necessary just to show a modal?