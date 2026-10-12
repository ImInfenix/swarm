from pathlib import Path

import polib


root = Path(__file__).resolve().parent.parent
catalog = root / "locale" / "fr" / "LC_MESSAGES" / "django.po"
polib.pofile(str(catalog), check_for_duplicates=True).save_as_mofile(str(catalog.with_suffix(".mo")))
