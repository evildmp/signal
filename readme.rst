======
Signal
======

A web application to surface wellbeing cues in a distributed organisation — from excitement to stress — without requiring people to make them explicit.

Overview
========

The problem
-----------

Remote work means we miss everyday clues about each other — body language, tone, energy. Those cues can signal anything from happiness and excitement to tiredness or stress. Online, these signals often have to be made explicit, which is a barrier  to sharing.

The idea
--------

A shared 2D grid where anyone can place a dot. The dot represents a signal — position encodes meaning along two axes. Dots are anonymous by default. The system never knows who placed which dot unless the author explicitly chooses to reveal themselves.

The two axes are good/bad feeling, and low/high energy.

How it works
------------

You place a dot on the grid. It's anonymous by default (but your browser gets a claim token so you can edit it later).

You decide which teams it will be published for.

Dots fade over time.

Anonymity
---------

Anonymity is key. The backend can't connect a dot to a user; it's only possible with a claim token.

Working with Signal
===================

Get started
-----------

Install the dependencies with `pip install -r requirements.txt` (ideally in a clean Python virtual environment).

Run the migrations with `python manage.py migrate`.

Seed the default teams with `python initialise_data.py`.

Start the app with `python manage.py runserver`, (or `python manage.py runserver 0.0.0.0:8080` if you need a different local port).

How to run tests
----------------

The backend unit tests require no running server. Run them with `python -m pytest dots/tests.py`.

The browser tests in `test_frontend.py` use Playwright and require both a running server and Playwright's browser binaries. Before running the frontend tests for the first time, install the Chromium binary with `playwright install chromium`. Then start the dev server in one terminal with `python manage.py runserver`, and in another run `python -m pytest test_frontend.py`.
