

import re
import os
import requests
from datetime import datetime, timedelta
from html.parser import HTMLParser
from PIL import Image, ImageDraw

USERNAME = "rayyan-anwar"
OUTPUT = "dist/contribution-snake.gif"

CELL_SIZE = 13
GAP = 4
STEP_DELAY = 110
RESET_DELAY = 2500


class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = []

    def handle_starttag(self, tag, attrs):
        if tag != "td":
            return

        attrs = dict(attrs)
        date = attrs.get("data-date")
        level = attrs.get("data-level")

        if date and level is not None:
            self.cells.append({
                "date": datetime.strptime(date, "%Y-%m-%d").date(),
                "level": int(level)
            })


def get_contributions():
    url = f"https://github.com/users/{USERNAME}/contributions"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    parser = ContributionParser()
    parser.feed(response.text)

    cells = parser.cells

    if len(cells) < 300:
        raise RuntimeError(
            f"Contribution grid could not be read. "
            f"HTTP: {response.status_code}, "
            f"Cells found: {len(cells)}, "
            f"Response length: {len(response.text)}"
        )

    cells.sort(key=lambda cell: cell["date"])

    first_date = cells[0]["date"]
    first_sunday = first_date - timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    for cell in cells:
        days = (cell["date"] - first_sunday).days
        cell["x"] = (days // 7) * (CELL_SIZE + GAP)
        cell["y"] = (days % 7) * (CELL_SIZE + GAP)

    return cells

def generate():
    cells = get_contributions()

    columns = sorted(set(c["x"] for c in cells))

    grid = []
    for col_index, x in enumerate(columns):
        column = sorted(
            [c for c in cells if c["x"] == x],
            key=lambda c: c["y"],
            reverse=bool(col_index % 2)
        )
        grid.extend(column)

    width = max(c["x"] for c in cells) + CELL_SIZE + 20
    height = max(c["y"] for c in cells) + CELL_SIZE + 20

    os.makedirs("dist", exist_ok=True)

    background = Image.new("RGB", (width, height), "#0D1117")

    draw = ImageDraw.Draw(background)

    colors = [
        "#161B22",
        "#0E4429",
        "#006D32",
        "#26A641",
        "#39D353"
    ]

    for cell in cells:
        x, y = cell["x"], cell["y"]
        color = colors[cell["level"]]
        draw.rounded_rectangle(
            (x, y, x + CELL_SIZE, y + CELL_SIZE),
            radius=3,
            fill=color
        )

    frames = []
    body = [0, 1, 2]

    def make_frame():
        frame = background.copy()
        draw = ImageDraw.Draw(frame)

        for index in body:
            cell = grid[index]
            x, y = cell["x"], cell["y"]

            draw.rounded_rectangle(
                (x - 1, y - 1,
                 x + CELL_SIZE + 1,
                 y + CELL_SIZE + 1),
                radius=5,
                fill="#38BDF8",
                outline="#BAE6FD",
                width=1
            )

        head = grid[body[-1]]
        x, y = head["x"], head["y"]

        draw.ellipse(
            (x - 2, y - 2,
             x + CELL_SIZE + 2,
             y + CELL_SIZE + 2),
            fill="#FFFFFF",
            outline="#38BDF8",
            width=2
        )

        frames.append(frame)

    make_frame()

        for index in range(3, len(grid)):
        cell = grid[index]

        body.append(index)

        if cell["level"] == 0:
            body.pop(0)

        make_frame()

    # Hold the completed snake.
    frames.extend([frames[-1]] * 8)

    # Reset to the original short snake.
    reset_body = [0, 1, 2]
    reset_frame = background.copy()
    draw = ImageDraw.Draw(reset_frame)

    for index in reset_body:
        cell = grid[index]
        x, y = cell["x"], cell["y"]

        draw.ellipse(
            (x - 1, y - 1,
             x + CELL_SIZE + 1,
             y + CELL_SIZE + 1),
            fill="#38BDF8"
        )

    frames.extend([reset_frame] * 25)

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=STEP_DELAY,
        loop=0,
        optimize=True
    )

    print(f"Snake animation saved: {OUTPUT}")
    print(f"Grid cells: {len(grid)}")
    print(f"Frames: {len(frames)}")


if __name__ == "__main__":
    generate()
