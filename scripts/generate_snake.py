import os
import requests
from collections import deque
from datetime import datetime, timedelta
from html.parser import HTMLParser
from PIL import Image, ImageDraw

USERNAME = "rayyan-anwar"
OUTPUT = "dist/contribution-snake.gif"

CELL_SIZE = 13
GAP = 4
PITCH = CELL_SIZE + GAP
STEP_DELAY = 250
RESET_DELAY = 2500
FRAME_EVERY = 2

COLORS = [
    "#161B22",
    "#0E4429",
    "#006D32",
    "#26A641",
    "#39D353",
]


class ContributionParser(HTMLParser):
    """Read contribution dates from GitHub SVG rect or td elements."""

    def __init__(self):
        super().__init__()
        self.cells = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        date = attrs.get("data-date")
        level = attrs.get("data-level")

        if date and level is not None:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
                parsed_level = int(level)
            except (TypeError, ValueError):
                return

            if 0 <= parsed_level <= 4:
                self.cells.append({
                    "date": parsed_date,
                    "level": parsed_level,
                })


def get_contributions():
    url = f"https://github.com/users/{USERNAME}/contributions"
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        },
        timeout=30,
    )
    response.raise_for_status()

    parser = ContributionParser()
    parser.feed(response.text)

    # Deduplicate dates in case GitHub's markup contains repeated attributes.
    cells_by_date = {cell["date"]: cell for cell in parser.cells}
    cells = list(cells_by_date.values())

    if len(cells) < 300:
        raise RuntimeError(
            "Could not read GitHub contribution grid. "
            f"HTTP={response.status_code}, cells={len(cells)}, "
            f"response_length={len(response.text)}. "
            "GitHub may have returned a sign-in, rate-limit, or changed page."
        )

    cells.sort(key=lambda cell: cell["date"])
    first_sunday = cells[0]["date"] - timedelta(
        days=(cells[0]["date"].weekday() + 1) % 7
    )

    for cell in cells:
        day_index = (cell["date"] - first_sunday).days
        cell["pos"] = (day_index // 7, day_index % 7)

    return cells


def find_path(start, targets, blocked, columns, rows):
    """Find a shortest four-direction path to the nearest green cell."""
    queue = deque([start])
    parents = {start: None}
    target = None
    directions = ((0, -1), (1, 0), (0, 1), (-1, 0))

    while queue:
        current = queue.popleft()

        if current in targets:
            target = current
            break

        for dx, dy in directions:
            nxt = (current[0] + dx, current[1] + dy)

            if not (0 <= nxt[0] < columns and 0 <= nxt[1] < rows):
                continue
            if nxt in parents or nxt in blocked:
                continue

            parents[nxt] = current
            queue.append(nxt)

    if target is None:
        return []

    path = []
    current = target
    while current != start:
        path.append(current)
        current = parents[current]

    return list(reversed(path))


def draw_dashboard(draw, x, y, panel_width, counts, history):
    from PIL import ImageFont

    white = "#E6EDF3"
    muted = "#8B949E"
    blue = "#38BDF8"

    title_font = ImageFont.truetype("DejaVuSans.ttf", 22)
    label_font = ImageFont.truetype("DejaVuSans.ttf", 17)

    draw.text((x, y), "CONTRIBUTION ANALYTICS",
              fill=white, font=title_font)

    draw.text((x, y + 42), "Cells by contribution level",
              fill="#39D353", font=label_font)

    chart_x = x + 8
    chart_y = y + 85
    bar_width = 75
    bar_gap = 35
    chart_height = 150

    maximum = max(counts.values()) if any(counts.values()) else 1
    baseline = chart_y + chart_height

    chart_right = chart_x + 4 * (bar_width + bar_gap) - bar_gap
    draw.line((chart_x, baseline, chart_right, baseline), fill=muted, width=2)

    for level in range(1, 5):
        value = counts[level]
        bar_height = int(chart_height * value / maximum)
        bx = chart_x + (level - 1) * (bar_width + bar_gap)
        top = baseline - bar_height

        draw.rounded_rectangle(
            (bx, top, bx + bar_width, baseline),
            radius=7,
            fill=COLORS[level],
        )

        draw.text((bx + 25, baseline + 10), str(level),
                  fill=white, font=label_font)

        draw.text((bx + 25, max(y + 65, top - 28)), str(value),
                  fill=white, font=label_font)

    line_title_y = y + 285

    draw.text((x, line_title_y), "TOTAL CELLS CONSUMED",
              fill=blue, font=title_font)

    gx = x + 8
    gy = line_title_y + 45
    graph_width = panel_width - 35
    graph_height = 140

    draw.line((gx, gy, gx, gy + graph_height), fill=muted, width=2)
    draw.line(
        (gx, gy + graph_height, gx + graph_width, gy + graph_height),
        fill=muted,
        width=2,
    )

    if history:
        max_total = max(history) or 1
        sample_count = min(len(history), graph_width)

        sampled = [
            history[round(i * (len(history) - 1) / max(1, sample_count - 1))]
            for i in range(sample_count)
        ]

        points = []
        for i, value in enumerate(sampled):
            px = gx + round(i * graph_width / max(1, len(sampled) - 1))
            py = gy + graph_height - round(value * graph_height / max_total)
            points.append((px, py))

        if len(points) > 1:
            draw.line(points, fill=blue, width=5)

        px, py = points[-1]
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=white)

    draw.text(
        (x, y + 475),
        f"Consumed: {sum(counts.values())}",
        fill=white,
        font=label_font,
    )


def generate():
    cells = get_contributions()
    cell_map = {cell["pos"]: cell for cell in cells}

    columns = max(pos[0] for pos in cell_map) + 1
    rows = 7

    remaining = {
        pos: cell["level"]
        for pos, cell in cell_map.items()
        if cell["level"] > 0
    }

    # Find three adjacent empty cells for a clean initial snake position.
    start_body = None
    for row in range(rows):
        for col in range(2, columns):
            candidate = [(col - 2, row), (col - 1, row), (col, row)]
            if all(
                pos in cell_map and cell_map[pos]["level"] == 0
                for pos in candidate
            ):
                start_body = candidate
                break
        if start_body:
            break

    if start_body is None:
        raise RuntimeError(
            "Could not find three adjacent empty cells for the snake start."
        )

    body = list(start_body)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    history = []

    grid_width = columns * PITCH + 20
    panel_width = 500
    panel_gap = 24
    width = grid_width + panel_gap + panel_width + 20
    height = max(rows * PITCH + 24, 500)
    grid_top = (height - rows * PITCH) // 2

    os.makedirs("dist", exist_ok=True)
    frames = []

    def make_frame():
        frame = Image.new("RGB", (width, height), "#0D1117")
        draw = ImageDraw.Draw(frame)

        # Consumed green cells disappear from the grid.
        for pos, cell in cell_map.items():
            col, row = pos
            x = 10 + col * PITCH
            y = grid_top + row * PITCH
            level = remaining.get(pos, 0)

            draw.rounded_rectangle(
                (x, y, x + CELL_SIZE, y + CELL_SIZE),
                radius=3,
                fill=COLORS[level],
            )

        # Snake body and head.
        for col, row in body[:-1]:
            x = 9 + col * PITCH
            y = grid_top + row * PITCH - 1
            draw.rounded_rectangle(
                (x, y, x + CELL_SIZE + 2, y + CELL_SIZE + 2),
                radius=5,
                fill="#38BDF8",
                outline="#BAE6FD",
                width=1,
            )

        col, row = body[-1]
        hx = 8 + col * PITCH
        hy = grid_top + row * PITCH - 2
        draw.ellipse(
            (hx, hy, hx + CELL_SIZE + 4, hy + CELL_SIZE + 4),
            fill="#FFFFFF",
            outline="#38BDF8",
            width=2,
        )

        draw_dashboard(
            draw,
            grid_width + panel_gap,
            12,
            panel_width,
            counts,
            history,
        )
        frames.append(frame)

    make_frame()
    steps = 0
    max_steps = columns * rows * 12

    # Recalculate the route after each move, allowing turns in all four
    # directions and avoiding the snake's current body.
    while remaining and steps < max_steps:
        head = body[-1]
        blocked = set(body[:-1])

        path = find_path(
            head,
            set(remaining),
            blocked,
            columns,
            rows,
        )

        if not path:
            break

        next_pos = path[0]
        level = remaining.get(next_pos, 0)
        body.append(next_pos)

        if level > 0:
            del remaining[next_pos]
            counts[level] += 1
            history.append(sum(counts.values()))
            # Keep the tail in place: consuming a green cell grows the snake.
        else:
            body.pop(0)

        steps += 1

        # Save regular movement frames and every consumption event.
        if steps % FRAME_EVERY == 0 or level > 0:
            make_frame()

    consumed_total = sum(counts.values())

    if not frames:
        raise RuntimeError("No animation frames were generated.")

    # Hold the final state briefly.
    frames.extend([frames[-1]] * 8)

    # Reset the snake, contribution cells, and charts for the next loop.
    body = list(start_body)
    remaining = {
        pos: cell["level"]
        for pos, cell in cell_map.items()
        if cell["level"] > 0
    }
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    history = []
    make_frame()

    reset_frames = max(1, round(RESET_DELAY / STEP_DELAY))
    frames.extend([frames[-1]] * reset_frames)

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=STEP_DELAY,
        loop=0,
        optimize=True,
    )

    print(f"Snake animation saved: {OUTPUT}")
    print(f"Contribution cells: {len(cell_map)}")
    print(f"Green cells consumed: {consumed_total}")
    print(f"Frames: {len(frames)}")

    if remaining:
        print(f"Green cells not reached in this cycle: {len(remaining)}")


if __name__ == "__main__":
    generate()
