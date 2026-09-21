"""Publish a Monday results-only recap for the latest archived NCAAF Best Card."""

from __future__ import annotations

import pandas as pd

from ncaaf_best_card import grade_archive, load_player_data, load_scoreboard, now, parse_games
from ncaaf_common import read_records_sheet, rows_to_sheet, upsert_records_sheet


def _number(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main():
    archive = read_records_sheet("NCAAF Best Card Archive")
    if not archive:
        raise RuntimeError("No archived NCAAF Best Card is available to grade.")

    season, week = max(
        ((_number(row.get("season")), _number(row.get("week"))) for row in archive),
        key=lambda item: item,
    )
    card = [
        row for row in archive
        if _number(row.get("season")) == season and _number(row.get("week")) == week
    ]
    if not season or not week or not card:
        raise RuntimeError("The latest archived NCAAF card has an invalid season or week.")

    games = parse_games(load_scoreboard(season, week), require_odds=False)
    stats, _ = load_player_data(season)
    week_stats = stats[pd.to_numeric(stats.week, errors="coerce") == week].copy()
    results = grade_archive(card, games, week_stats)

    expected = len(card)
    completed = len(results)
    if results:
        upsert_records_sheet(
            "NCAAF Best Card Results",
            results,
            ("season", "week", "card", "component"),
        )

    hits = sum(row["result"] == "HIT" for row in results)
    misses = sum(row["result"] == "MISS" for row in results)
    pushes = sum(row["result"] == "PUSH" for row in results)
    pending = expected - completed
    generated = now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    rows = [
        ["NCAAF Best Card Results", ""],
        ["Season", season],
        ["Week", week],
        ["Generated", generated],
        ["Overall", f"{hits}-{misses}-{pushes} (H-M-P)"],
        ["Graded", f"{completed} of {expected} selections"],
        ["", ""],
        ["RESULTS", ""],
    ]
    for row in sorted(results, key=lambda item: (_number(item.get("card")), str(item.get("component", "")))):
        line = row.get("line", "")
        selection = f"{row.get('selection', '')} {line}".strip()
        rows.append([
            f"Card {row.get('card')} — {row.get('component')}",
            f"{selection} — {row.get('result')} ({row.get('actual', '')})",
        ])
    if pending:
        rows += [
            ["", ""],
            ["Pending", f"{pending} selection(s) are not final yet. The later Monday retry will check again."],
        ]

    rows_to_sheet("NCAAF Results Email Summary", rows)


if __name__ == "__main__":
    main()
