import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management import BaseCommand, call_command
from django.db import transaction

from app.models import Dot

DEFAULT_FIXTURE_PATH = Path("app/fixtures/initial_data.json")


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_timestamp(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dot_records(records):
    return [record for record in records if record.get("model") == "app.dot"]


def build_updated_timestamp_map(records, target_latest):
    dots = dot_records(records)
    if not dots:
        return {}, None, None

    existing_timestamps = [parse_timestamp(dot["fields"]["created_at"]) for dot in dots]
    current_latest = max(existing_timestamps)
    delta = target_latest - current_latest

    updated = {}
    for dot in dots:
        updated[int(dot["pk"])] = parse_timestamp(dot["fields"]["created_at"]) + delta

    updated_timestamps = list(updated.values())
    return updated, min(updated_timestamps), max(updated_timestamps)


def rewrite_fixture(records, updated_timestamps, fixture_path):
    for record in records:
        if record.get("model") != "app.dot":
            continue
        record["fields"]["created_at"] = format_timestamp(
            updated_timestamps[int(record["pk"])]
        )

    with fixture_path.open("w") as handle:
        json.dump(records, handle, indent=2)
        handle.write("\n")


def refresh_database(fixture_path, updated_timestamps, skip_load):
    if not skip_load:
        call_command("loaddata", str(fixture_path))

    with transaction.atomic():
        dots = {dot.id: dot for dot in Dot.objects.filter(id__in=updated_timestamps)}
        missing_ids = sorted(set(updated_timestamps) - set(dots))
        if missing_ids:
            missing_list = ", ".join(str(dot_id) for dot_id in missing_ids)
            raise SystemExit(
                f"Missing app.dot rows in database for ids: {missing_list}"
            )

        for dot_id, created_at in updated_timestamps.items():
            dot = dots[dot_id]
            dot.created_at = created_at

        Dot.objects.bulk_update(dots.values(), ["created_at"])


class Command(BaseCommand):
    help = (
        "Load the initial data fixture and shift all app.dot created_at timestamps "
        "so they fall within the last seven days."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "fixture_path",
            nargs="?",
            default=str(DEFAULT_FIXTURE_PATH),
            help="Path to the JSON fixture file to load.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the timestamp range that would be applied without changing the DB or fixture.",
        )
        parser.add_argument(
            "--rewrite-fixture",
            action="store_true",
            help="Rewrite the fixture file instead of loading it and updating the database.",
        )
        parser.add_argument(
            "--skip-load",
            action="store_true",
            help="Do not run loaddata before updating database rows.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture_path"])

        with fixture_path.open() as handle:
            records = json.load(handle)

        target_latest = datetime.now(timezone.utc).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        updated_timestamps, earliest, latest = build_updated_timestamp_map(
            records,
            target_latest,
        )

        if not updated_timestamps:
            self.stdout.write(f"No app.dot records found in {fixture_path}")
            return

        if not options["dry_run"]:
            if options["rewrite_fixture"]:
                rewrite_fixture(records, updated_timestamps, fixture_path)
            else:
                refresh_database(
                    fixture_path,
                    updated_timestamps,
                    options["skip_load"],
                )

        if options["dry_run"]:
            action = "Would update"
        elif options["rewrite_fixture"]:
            action = "Updated fixture timestamps for"
        else:
            action = "Loaded fixture and updated database timestamps for"

        self.stdout.write(f"{action} {len(updated_timestamps)} dots")
        self.stdout.write(f"Earliest created_at: {format_timestamp(earliest)}")
        self.stdout.write(f"Latest created_at:   {format_timestamp(latest)}")
