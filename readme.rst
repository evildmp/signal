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

Anonymity is key. The backend can't connect a dot to a user unless the user explicitly chooses that.

Working with Signal
===================

Get started
-----------

Install the dependencies with ``pip install -r requirements_dev.txt`` (ideally in a clean Python virtual environment).

``settings.py`` expects to load key settings from environment variables, so *for development purposes only* copy ``.env.development`` to ``.env`` (``.gitignore`` stops ``.env`` from being committed accidentally).

Run the migrations with ``python manage.py migrate``.

Seed initial development data with ``python manage.py seed_initial_data``.

Start the app with ``python manage.py runserver``, (or ``python manage.py runserver 0.0.0.0:8080`` if you need a particular local port, or will access the server from another host).


Users
~~~~~

You'll need to log in. Multiple users exist in the system. Log in as ``jerry`` with the password ``jerry`` - ``jerry`` is the only admin user.

You can see all the users listed at http://localhost:8000/admin/auth/user/. Everyu user's password is their user name.


How to run tests
----------------

Tests use Playwright. By default, this uses Chromium, which in turn may require further dependencies.

Install browser binaries in the virtual environment::

    python -m playwright install --with-deps chromium  # or webkit, or firefix

Run ``python -m pytest``. (Use e.g. ``--browser webkit`` to specify another browser engine.)

Internals
=========

A dot is anonymous by default, but can be associated with an owner through an ``owner_user`` relation.

In order to make dot management possible without that relation, the user who creates the dot gets an ``ownership_token`` with a UUID, that's stored in the browser's Local Storage. This allows the browser to prove that the user owns a particular dot, without any backend association with a user.

An *adjective-colour-noun* claim token is shown to the user when a dot is first created. This is a convenient way of claiming a particular dot without having an ``owner_user`` relation (for example, in a new browser or on another device).

Optionally, *if* the owner of the dot selects the *Show my name option*, then the ``owner_user`` relation is set on the dot. This is convenient, because it's more robust and persistent.
