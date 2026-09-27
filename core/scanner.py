from pathlib import Path


def scan_folder(folder_path):

    folder = Path(folder_path)

    if not folder.exists():
        return {
            "files": 0,
            "folders": 0,
            "size": 0
        }

    file_count = 0
    folder_count = 0
    total_size = 0

    for item in folder.rglob("*"):

        if item.is_file():

            file_count += 1

            try:
                total_size += item.stat().st_size
            except:
                pass

        elif item.is_dir():

            folder_count += 1

    return {
        "files": file_count,
        "folders": folder_count,
        "size": total_size
    }