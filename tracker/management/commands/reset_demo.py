from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Clear application data from the selected database while keeping its schema and migrations."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Database connection to clear.")
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")

    def handle(self, *args, **options):
        database = options["database"]
        connection = connections[database]
        database_name = connection.settings_dict["NAME"]
        self.stderr.write(self.style.WARNING(f"This will delete all data from database '{database}': {database_name}"))
        if not options["yes"]:
            answer = input("Type 'yes' to continue: ")
            if answer != "yes":
                raise CommandError("Reset cancelled.")
        call_command("flush", database=database, interactive=False, verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS("Database cleared."))
