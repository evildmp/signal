# Signal

Signal is a Python/Django application, that records and displays sentiment for a distributed organisation.


## Stack

* Django, using Django's native functionality as much and consistently as possible
* HTMX for interaction - JavaScript code should be kept to an absolute necessary minimum
* CSS based on Vanilla https://vanillaframework.io/
* pytest/django-pytest and Playwright for testing

## Working practices

You will create tests before writing functional code. You can plan well in advance, but each implementation of new code must be discrete and complete before we start tackling the next. We proceed in small steps. I want to be able to commit often, and in each case have a codebase that is a step forward, not a half-baked exploration.

You are not permitted to act on a plan without my explicit go-ahead.

Commit messages are in the past tense.

You will not use numbered lists in your responses, because they are irritating.

### Initial data

We'll need an initial_data file, which could be Python, YAML or JSON, so that while developing we can have some consistent data to work with.

## The picture

This describes the ontology of the application.


### Organisation

The organisation is a hierarchy of teams, for example:

* Organisation
  * Colours
    * Blue
    * Green
    * Red
      * Deep red
      * Faded red
   * Tastes
     * Bitter
     * Sweet
     * Sour
  * Machines

For development and testing purposes, you can create this organisation in the database.

### Users (members)

Users are members of one or more teams. A member of a team is also a member of its parent team, by implication. So for example if Jerry is a member of Sour, he must also be a member of Tastes and Organisation.

Each user can log in to the system. For development and testing purposes, create the following users, as members of the teams indicated:

* Jerry: Deep red, Blue
* Tina: Deep red
* David B: Deep red
* Chris: Deep red
* Lou: Tastes
* Sterling: Tastes
* Moe: Tastes
* John: Tastes
* Jonathan: Blue
* Ernie: Blue
* David R: Blue

Each user's username will be their lower-cased name, and so will their password.

### The interface

For the interface, make sure that you use Vanilla styling and patterns. The interface needs to work equally well on mobile and larger displays.

#### The grid

The main interface is a two-dimensional plane. Its x-axis is energy: quiet on the left, energised on the right. The y axis is feeling negative on the bottom and feeling positive at the top. We just need the axes, no need to display actual grid markers.

At the top of the grid it says:

    Signal
    Place a dot; select to edit; drag to move

#### Dots

The grid displays dots. Each dot is placed by a user, by clicking or tapping on the grid. It's very important that there is no way to know which user placed which dot (there should be no database relationship for example). The x and y positions of the dot are in the range 0-100 (integers)

A dot has a creation date. Dots fade over period of a week. After a week they fade to nothing (and don't actually need to be displayed at all).

A dot has a unique identifier, in the form adjective-colour-noun. All should be short and common words. The nouns should be natural objects: moon, tree, frog, sea, hill, stone, etc.

As well as their x/y positions, dots can have other data associated with them. Some of the data can be displayed as labels next to them on the grid.

A dot can show the user's name, if the user has chosen to do that.

By default, each dot is associated with the team(s) that the user is explcitly associated with. However, the dot can be associated with any team(s) the user belongs to.

A dot can show sentiments that the user chooses.

One is a list of 30 feelings, such as sad, happy, lonely, tired, worried, relaxed, optimistic. The last item should be "I find it hard to describe what I feel". The user can select more than one of these, and also add a sentiment not already listed.

Another is a list of feelings or wishes connected to how they related to others, including:

* I wish I could talk to someone
* I need help
* I'd love to talk about this

And once again, a free text option.

For development and testing purposes, every user needs to have created 4 to 12 dots, on days over the last week. About 66% of those dots should be for their explicit teams, the others can include another team that they are implcitly a member of, or can exclude one or more of their explicit teams.

70% of dots should be anonymous. The rest should include the user's username.

40% should include one or more feeling sentiments, and 20% one or more feelings or wishes connected to how they related to others.

When created, a dot has a "claim token". This is the mechanism by which the interface knows that a dot belongs to a user. The user receives the clain token and that allows the browser to tell the application it is authorised to make future changes to a dot.

#### The drawer

At the left of the grid is a drawer, open by default on wider displays, but closed for narrower ones. When opened, it displays the hierarchical list of teams, showing only those that the user is actually a member of (whether explictly or only a member by implication).

For each team listed there should be a checkbox. The textbox allows the user the team(s) for which data should be displayed. By default, the teams that the user is explictly a member of should be selected.

At the bottom of the list is a checkbox for "My dots only"

At the bottom of the drawer, there is a log out option.

## The story

This describes what must be possible with the functionality you are going to implement.

Each pragraph in the story **must** have at least one automated test associated with it.

### Authentication

When I visit the application in the browser, I amn presented with a login dialog.

I can log in as jerry with password jerry.

### The main view

I see dots associated with the Deep red and Blue teams, because those are the teams jerry is explictly a member of.

jerry's own dots pulsate gently.

The drawer contains a list showing Deep red and Blue selected, but also Organisation, Colours, Red (nor selected).

When jerry selects "My dots only" only the dots that he has created (i.e. has a claim token for) are shown. Also, all the other items in the list are unselected.

When jerry selects "Organisation" he sees all the dots that are published to any of the teams that are descendants of Organisation.

### Managing dots

When jerry clicks or taps on the grid, a dot is placed. The dot is published to the team(s) that jerry is explictly a member of.

An alert message appears, that says "Published to <team> and <team>." and then fades.

jerry can click on the dot, and edit its attributes. He sees its unique identifier. He can delete the dot. He can choose or unchoose the option to have his name published with it. He also sees a hierachical list of teams he is a member of and can choose to alter the teams where his dot is published.

jerry can drag his dot to a different position.

If jerry tries to edit a dot that he doesn't have a claim token for, a dialog box opens inviting him to enter its unique identifier. If be has the right identifier, then he gets a claim token for it.

