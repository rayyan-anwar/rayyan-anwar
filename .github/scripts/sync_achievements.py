import json
import os

with open("achievements.json", encoding="utf-8") as f:
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

lines = []

for item in earned:
    slug = item["slug"]
    name = item["name"]
    tier = item.get("officialTier", 1)

    tier_names = {
        1: "Default",
        2: "Bronze",
        3: "Silver",
        4: "Gold",
    }
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

if not lines:
    content = "_No public achievements detected yet._"
else:
    content = "\n".join(lines)

readme_path = "README.md"

with open(readme_path, encoding="utf-8") as f:
    readme = f.read()

start = "<!-- GITHUB-ACHIEVEMENTS:START -->"
end = "<!-- GITHUB-ACHIEVEMENTS:END -->"

if start not in readme or end not in readme:
    raise SystemExit("README markers missing. No changes made.")

before, rest = readme.split(start, 1)
_, after = rest.split(end, 1)

updated = before + start + "\n" + content + "\n" + end + after

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(updated)
