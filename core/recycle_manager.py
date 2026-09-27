from pathlib import Path
from datetime import datetime
import shutil


def move_to_recycle_bin(file_path):

    recycle_bin = (
        Path("data")
        / "recycle_bin"
    )

    recycle_bin.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = Path(file_path)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    recycle_target = (
        recycle_bin /
        f"{timestamp}_{file_path.name}"
    )

    shutil.move(
        str(file_path),
        str(recycle_target)
    )

    return recycle_target

def empty_recycle_bin():

    recycle_bin = Path(
        "data/recycle_bin"
    )

    if not recycle_bin.exists():
        return

    count = 0

    for f in recycle_bin.glob("*"):

        if f.is_file():

            f.unlink()

            count += 1

    return count
