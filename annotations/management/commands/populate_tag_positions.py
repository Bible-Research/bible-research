"""
Django management command to populate tag_position field for existing
notes.

Converts each note's created_at timestamp to Unix timestamp and sets
it as the tag_position value if:
1. tag_position is null, OR
2. tag_position equals the default migration value (1788499374.590501)

Usage:
    python manage.py populate_tag_positions
    python manage.py populate_tag_positions --dry-run
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from annotations.models import Note

# Default value set by migration that should be replaced
DEFAULT_MIGRATION_VALUE = 1788499374.590501


class Command(BaseCommand):
    help = (
        'Populate tag_position with Unix timestamp from created_at '
        'for notes where tag_position is null or has default value'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find notes where tag_position is null OR equals the default
        # migration value
        notes_to_update = Note.objects.filter(
            Q(tag_position__isnull=True) |
            Q(tag_position=DEFAULT_MIGRATION_VALUE)
        )
        total_count = notes_to_update.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    'No notes found needing tag_position update. '
                    'All notes already have valid positions set.'
                )
            )
            return

        # Count how many of each type
        null_count = Note.objects.filter(
            tag_position__isnull=True
        ).count()
        default_count = Note.objects.filter(
            tag_position=DEFAULT_MIGRATION_VALUE
        ).count()

        self.stdout.write(
            f'Found {total_count} note(s) to update:'
        )
        if null_count > 0:
            self.stdout.write(f'  - {null_count} with null tag_position')
        if default_count > 0:
            self.stdout.write(
                f'  - {default_count} with default migration value '
                f'({DEFAULT_MIGRATION_VALUE})'
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n=== DRY RUN MODE ===')
            )
            self.stdout.write('The following notes would be updated:\n')

        updated_count = 0
        for note in notes_to_update:
            # Convert created_at to Unix timestamp
            unix_timestamp = note.created_at.timestamp()
            old_value = note.tag_position

            if dry_run:
                self.stdout.write(
                    f'  Note {note.id[:8]}: '
                    f'tag_position={old_value} -> {unix_timestamp} '
                    f'(created_at={note.created_at})'
                )
            else:
                note.tag_position = unix_timestamp
                note.save(update_fields=['tag_position'])
                updated_count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDry run complete. {total_count} note(s) '
                    f'would be updated.'
                )
            )
            self.stdout.write(
                'Run without --dry-run to apply changes.'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully updated {updated_count} note(s) '
                    f'with tag_position values based on created_at.'
                )
            )
