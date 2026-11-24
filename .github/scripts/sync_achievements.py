import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

achievements_path = ROOT / "achievements.json"
readme_path = ROOT / "README.md"

with achievements_path.open(encoding="utf-8") as f:
    report = json.load(f)

if report.get("achievementsHidden"):
    raise SystemExit("Achievements are hidden. README was not changed.")

badges = {
    "pull-shark": "pull-shark-default-498c279a747d.png",
    "starstruck": "starstruck-default-b6610abad518.png",
    "pair-extraordinaire": "pair-extraordinaire-default-579438a20e01.png",
    "galaxy-brain": "galaxy-brain-default-847262c21056.png",
    "quickdraw": "quickdraw-default-39c6aec8ff89.png",
    "yolo": "yolo-default-be0bbff04951.png",
    "public-sponsor": "public-sponsor-default-9fa68986b057.png",
}

earned = [
    item for item in report.get("achievements", [])
    if item.get("status") == "earned"
    and item.get("officialTier", 0) > 0
]

tier_names = {
    1: "Default",
    2: "Bronze",
    3: "Silver",
    4: "Gold",
}

lines = []

for item in earned:
    slug = item["slug"]
    name = item["name"]
    tier = item.get("officialTier", 1)
    tier_name = tier_names.get(tier, f"Tier {tier}")

    if slug in badges:
        image = (
            "https://github.githubassets.com/assets/"
            + badges[slug]
        )

        lines.append(
            f'<a href="https://github.com/users/'
            f'{report["user"]}/achievements/{slug}">'
            f'<img src="{image}" width="72" height="72" '
            f'alt="{name}" title="{name} - {tier_name}">'
            f'</a>'
        )
    else:
        lines.append(f"- **{name}** — {tier_name}")

content = (
    "\n".join(lines)
    if lines
    else "_No public achievements detected yet._"
)

if not readme_path.exists():
    raise SystemExit(f"README not found: {readme_path}")

readme = readme_path.read_text(encoding="utf-8")

start = "<!-- GITHUB-ACHIEVEMENTS:START -->"
end = "<!-- GITHUB-ACHIEVEMENTS:END -->"

if start not in readme or end not in readme:
    raise SystemExit(
        "README markers missing.\n"
        f"README checked: {readme_path}\n"
        f"START marker found: {start in readme}\n"
        f"END marker found: {end in readme}\n"
        "No changes made."
    )

before, rest = readme.split(start, 1)
_, after = rest.split(end, 1)

updated = before + start + "\n" + content + "\n" + end + after

readme_path.write_text(updated, encoding="utf-8")

print(f"Achievements synced successfully: {len(earned)} earned")
print(f"README updated: {readme_path}")
