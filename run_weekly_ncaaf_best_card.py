"""Publish Friday NCAAF Top 25 Best Card and prior-week results."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from ncaaf_best_card import build_card, grade_archive, load_player_data, load_scoreboard, now, parse_games
from ncaaf_common import read_records_sheet, rows_to_sheet, upsert_records_sheet


def main():
    payload = load_scoreboard()
    season = int(payload["leagues"][0]["season"]["year"])
    week = int(payload.get("week", {}).get("number") or payload["leagues"][0]["season"].get("type", {}).get("week", {}).get("number", 0))
    if not week:
        first = payload.get("events", [{}])[0]
        week = int(first.get("week", {}).get("number", 0))
    if not week:
        raise RuntimeError("Unable to determine the current NCAAF week.")
    games = parse_games(load_scoreboard(season, week))
    stats, roster = load_player_data(season)
    cards = build_card(games, stats, roster)

    snapshot = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    archive = []
    for card_number, card in enumerate(cards, 1):
        base = {"season": season, "week": week, "card": card_number, "event_id": card["event_id"],
                "matchup": f"{card['away']} at {card['home']}", "snapshot_utc": snapshot}
        archive += [
            {**base, "component": "Spread", "selection": card["spread_team"], "line": card["spread_line"], "position": ""},
            {**base, "component": "RB Touchdown", "selection": card["rb"]["player"], "line": "", "position": card["rb"]["position"]},
            {**base, "component": "WR/TE Touchdown", "selection": card["receiver"]["player"], "line": "", "position": card["receiver"]["position"]},
        ]
    upsert_records_sheet("NCAAF Best Card Archive", archive, ("season", "week", "card", "component"))

    previous = [r for r in read_records_sheet("NCAAF Best Card Archive") if int(r.get("season", 0) or 0) == season and int(r.get("week", 0) or 0) == week - 1]
    results = []
    if previous:
        prior_games = parse_games(load_scoreboard(season, week - 1), require_odds=False)
        prior_stats = stats[pd.to_numeric(stats.week, errors="coerce") == week - 1].copy()
        results = grade_archive(previous, prior_games, prior_stats)
        upsert_records_sheet("NCAAF Best Card Results", results, ("season", "week", "card", "component"))
    else:
        rows_to_sheet(
            "NCAAF Best Card Results",
            [["Status"], ["No completed prior-week card is available yet. Results begin after the first card is played."]],
        )

    pacific_now = now().astimezone(ZoneInfo("America/Los_Angeles"))
    generated = pacific_now.strftime("%Y-%m-%d %H:%M %Z")
    rows = [["Weekly NCAAF Top 25 Best Card", ""], ["Season", season], ["Week", week],
            ["Generated Date", pacific_now.strftime("%Y-%m-%d")], ["Generated", generated],
            ["Card Policy", "5 games involving AP Top 25 teams; ranked-vs-ranked matchups always receive first priority"],
            ["Selections", "Spread + one RB TD scorer + one WR/TE TD scorer per game"], ["", ""],
            ["LAST WEEK'S RESULTS", ""]]
    if results:
        hits = sum(r["result"] == "HIT" for r in results); misses = sum(r["result"] == "MISS" for r in results); pushes = sum(r["result"] == "PUSH" for r in results)
        rows.append(["Overall", f"{hits}-{misses}-{pushes} (H-M-P)"])
        for r in results:
            rows.append([f"Card {r['card']} — {r['component']}", f"{r['selection']} {r.get('line', '')} — {r['result']} ({r['actual']})"])
    else:
        rows.append(["Status", "No completed prior-week card is available yet."])
    rows += [["", ""], ["THIS WEEK'S BEST CARD", ""]]
    for i, card in enumerate(cards, 1):
        rank_bits = [f"#{card['away_rank']}" if card['away_rank'] <= 25 else "NR", f"#{card['home_rank']}" if card['home_rank'] <= 25 else "NR"]
        rows += [[f"GAME {i}: {card['away']} at {card['home']}", f"{rank_bits[0]} at {rank_bits[1]} | {card['kickoff']}"],
                 ["Spread Pick", f"{card['spread_team']} {card['spread_line']:+g} ({card['odds_provider']}; frozen Friday)"],
                 ["RB Touchdown", f"{card['rb']['player']} ({card['rb']['team']}) — score {card['rb']['score']}"],
                 ["WR/TE Touchdown", f"{card['receiver']['player']} ({card['receiver']['team']}, {card['receiver']['position']}) — score {card['receiver']['score']}"], ["", ""]]
    rows_to_sheet("NCAAF Best Card Email Summary", rows)


if __name__ == "__main__":
    main()
