"""Initialize the SQLite schema and load clone's chart.

  python -m ora.scripts.init
"""

import logging

from ora import db, subjects

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    print("Creating schema…")
    db.init_schema()

    print("Loading clone from data/clone.yaml + computing charts…")
    subject_id = subjects.load_clone_from_yaml()

    print(f"clone loaded as subject id={subject_id}\n")
    print(subjects.render_subject_markdown(subject_id))


if __name__ == "__main__":
    main()
