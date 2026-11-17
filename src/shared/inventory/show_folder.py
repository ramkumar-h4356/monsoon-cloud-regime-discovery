
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "inventory" / "folder_inventory.txt"

lines = []
total_files = 0
total_size = 0

def scan_folder(folder, level=0):
    global total_files, total_size

    entries = sorted(
        folder.iterdir(),
        key=lambda p: (p.is_file(), p.name.lower())
    )

    for entry in entries:
        if entry == REPORT:
            continue

        indent = "    " * level

        if entry.is_dir():
            lines.append(f"{indent}[FOLDER] {entry.name}")
            scan_folder(entry, level + 1)

        elif entry.is_file():
            size = entry.stat().st_size
            total_files += 1
            total_size += size

            size_mb = size / (1024 ** 2)
            lines.append(
                f"{indent}[FILE] {entry.name} | {size_mb:.2f} MB"
            )

lines.append(f"ROOT: {ROOT}")
lines.append("=" * 80)

scan_folder(ROOT)

lines.append("\n" + "=" * 80)
lines.append("SUMMARY")
lines.append(f"Total files: {total_files}")
lines.append(f"Total size: {total_size / (1024 ** 3):.2f} GB")

report_text = "\n".join(lines)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(report_text, encoding="utf-8")

print(report_text)
print(f"\nReport saved at: {REPORT}")
