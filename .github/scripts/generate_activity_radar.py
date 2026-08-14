#!/usr/bin/env python3
"""Generate a local GitHub contribution radar for the profile README."""

import json
import os
import sys
import urllib.request
from pathlib import Path


USERNAME = "raanariba"
OUTPUT = Path(__file__).resolve().parents[2] / "assets" / "activity-radar.svg"

WIDTH, HEIGHT = 480, 390
CENTER_X, CENTER_Y = 240, 195
AXIS_RADIUS = 110
LABEL_GAP = 16

BACKGROUND = "#0d1117"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
GREEN = "#3fb950"
GREEN_FILL = "#3fb95066"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      totalPullRequestContributions
    }
  }
}
"""


def fetch_contributions(token: str) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "errors" in body:
        raise RuntimeError(f"GitHub GraphQL errors: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]


def axis_points(values: list[float]) -> list[tuple[float, float]]:
    """Return vertices in top, right, bottom, left order."""
    peak = max(values) or 1.0
    radii = [AXIS_RADIUS * value / peak for value in values]
    return [
        (CENTER_X, CENTER_Y - radii[0]),
        (CENTER_X + radii[1], CENTER_Y),
        (CENTER_X, CENTER_Y + radii[2]),
        (CENTER_X - radii[3], CENTER_Y),
    ]


def label_block(x: float, y: float, percent: int, name: str, anchor: str) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="pct">{percent}%</text>'
        f'<text x="{x}" y="{y + 17}" text-anchor="{anchor}" class="name">{name}</text>'
    )


def render(percents: list[int]) -> str:
    vertices = axis_points([float(percent) for percent in percents])
    polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in vertices)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{GREEN}"/>' for x, y in vertices
    )
    top = CENTER_Y - AXIS_RADIUS
    bottom = CENTER_Y + AXIS_RADIUS
    left = CENTER_X - AXIS_RADIUS
    right = CENTER_X + AXIS_RADIUS
    labels = (
        label_block(CENTER_X, top - LABEL_GAP - 17, percents[0], "Code review", "middle")
        + label_block(right + LABEL_GAP, CENTER_Y - 4, percents[1], "Issues", "start")
        + label_block(CENTER_X, bottom + LABEL_GAP + 12, percents[2], "Pull requests", "middle")
        + label_block(left - LABEL_GAP, CENTER_Y - 4, percents[3], "Commits", "end")
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Contribution split: {percents[3]}% commits, {percents[2]}% pull requests, {percents[0]}% code review, {percents[1]}% issues">
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .title {{ font-size: 15px; font-weight: 600; fill: {TEXT}; }}
    .pct {{ font-size: 14px; font-weight: 600; fill: {TEXT}; }}
    .name {{ font-size: 13px; fill: {MUTED}; }}
  </style>
  <rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{BACKGROUND}"/>
  <text x="24" y="32" class="title">Activity overview - last 12 months</text>
  <line x1="{CENTER_X}" y1="{top}" x2="{CENTER_X}" y2="{bottom}" stroke="{GREEN}" stroke-width="1.5"/>
  <line x1="{left}" y1="{CENTER_Y}" x2="{right}" y2="{CENTER_Y}" stroke="{GREEN}" stroke-width="1.5"/>
  <polygon points="{polygon}" fill="{GREEN_FILL}" stroke="{GREEN}" stroke-width="1.5"/>
  {dots}
  {labels}
</svg>
"""


def main() -> int:
    token = os.environ.get("ACTIVITY_RADAR_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: set ACTIVITY_RADAR_TOKEN or GITHUB_TOKEN", file=sys.stderr)
        return 1

    totals = fetch_contributions(token)
    counts = {
        "Code review": totals["totalPullRequestReviewContributions"],
        "Issues": totals["totalIssueContributions"],
        "Pull requests": totals["totalPullRequestContributions"],
        "Commits": totals["totalCommitContributions"],
    }
    total = sum(counts.values())
    if total == 0:
        print("error: no contributions found in the last 12 months", file=sys.stderr)
        return 1

    percents = [round(100 * count / total) for count in counts.values()]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(percents), encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
