from pathlib import Path
import shutil
from datetime import datetime


def backup_file(file_path):

    file_path = Path(file_path)

    if not file_path.exists():
        return

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        Path("data")
        / "backup"
        / timestamp
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    backup_file = (
        backup_dir
        / file_path.name
    )

    shutil.copy2(
        file_path,
        backup_file
    )

    return backup_file