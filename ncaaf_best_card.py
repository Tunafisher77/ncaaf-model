"""Build and grade the weekly AP Top 25 NCAAF Best Card."""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from io import StringIO
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd

PACIFIC = ZoneInfo("America/Los_Angeles")
SCOREBOARD = "https://cdn.espn.com/core/college-football/scoreboard"
DATA_ROOT = "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main"


def _json(url: str) -> dict:
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ncaaf-best-card/1.0)",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.espn.com/college-football/scoreboard/",
    })
    with urlopen(request, timeout=45) as response:
        import json
        return json.load(response)


def now() -> datetime:
    override = os.getenv("NCAAF_NOW_ISO", "").strip()
    if override:
        value = datetime.fromisoformat(override.replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def load_scoreboard(season: int | None = None, week: int | None = None) -> dict:
    params = ["xhr=1", "groups=80", "limit=200"]
    if season:
        params += [f"year={season}", "seasontype=2"]
    if week:
        params.append(f"week={week}")
    payload = _json(SCOREBOARD + "?" + "&".join(params))
    try:
        return payload["content"]["sbData"]
    except (KeyError, TypeError):
        raise RuntimeError("ESPN CDN scoreboard response did not contain scoreboard data.")


def load_player_data(season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    stats_url = f"{DATA_ROOT}/player_stats/csv/player_stats_{season}.csv"
    roster_url = f"{DATA_ROOT}/rosters/csv/cfb_rosters_{season}.csv"
    stats = pd.read_csv(StringIO(urlopen(stats_url, timeout=90).read().decode()), low_memory=False)
    roster = pd.read_csv(StringIO(urlopen(roster_url, timeout=90).read().decode()), low_memory=False)
    return stats, roster


def _rank(competitor: dict) -> int:
    value = competitor.get("curatedRank", {}).get("current", 99)
    return int(value) if str(value).isdigit() else 99


def parse_games(payload: dict) -> list[dict]:
    games = []
    for event in payload.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = {c.get("homeAway"): c for c in competition.get("competitors", [])}
        if set(competitors) != {"home", "away"}:
            continue
        home, away = competitors["home"], competitors["away"]
        if min(_rank(home), _rank(away)) > 25:
            continue
        odds = (competition.get("odds") or [])
        if not odds or not odds[0].get("details"):
            continue
        point = odds[0].get("pointSpread", {})
        home_line = point.get("home", {}).get("close", {}).get("line")
        away_line = point.get("away", {}).get("close", {}).get("line")
        if home_line is None or away_line is None:
            continue
        games.append({
            "event_id": str(event["id"]), "kickoff": event.get("date", ""),
            "home_id": str(home["team"]["id"]), "away_id": str(away["team"]["id"]),
            "home": home["team"]["displayName"], "away": away["team"]["displayName"],
            "home_key": home["team"].get("location", home["team"]["displayName"]),
            "away_key": away["team"].get("location", away["team"]["displayName"]),
            "home_abbr": home["team"].get("abbreviation", ""), "away_abbr": away["team"].get("abbreviation", ""),
            "home_rank": _rank(home), "away_rank": _rank(away),
            "home_line": float(home_line), "away_line": float(away_line),
            "odds_detail": odds[0]["details"], "odds_provider": odds[0].get("provider", {}).get("name", "ESPN odds feed"),
            "completed": competition.get("status", {}).get("type", {}).get("completed", False),
            "home_score": float(home.get("score", 0) or 0), "away_score": float(away.get("score", 0) or 0),
        })
    return games


def _team_form(stats: pd.DataFrame) -> dict[str, float]:
    games = stats[["game_id", "team", "team_score", "opponent_score"]].drop_duplicates()
    games["margin"] = pd.to_numeric(games.team_score, errors="coerce") - pd.to_numeric(games.opponent_score, errors="coerce")
    return games.sort_values("game_id").groupby("team").tail(4).groupby("team").margin.mean().to_dict()


def _roster_lookup(roster: pd.DataFrame) -> dict[str, str]:
    name_col = next((c for c in ["full_name", "athlete_name", "player_name", "name"] if c in roster), None)
    pos_col = next((c for c in ["position", "position_abbreviation", "position_name"] if c in roster), None)
    if not name_col and {"first_name", "last_name"}.issubset(roster.columns):
        roster = roster.copy()
        roster["_full_name"] = roster["first_name"].fillna("").astype(str).str.strip() + " " + roster["last_name"].fillna("").astype(str).str.strip()
        name_col = "_full_name"
    if not name_col or not pos_col:
        raise RuntimeError("Current NCAAF roster file is missing player name or position.")
    return {str(r[name_col]).strip(): str(r[pos_col]).upper().strip() for _, r in roster.iterrows()}


def touchdown_candidates(stats: pd.DataFrame, roster: pd.DataFrame, teams: set[str]) -> pd.DataFrame:
    positions = _roster_lookup(roster)
    recent_week = int(pd.to_numeric(stats.week, errors="coerce").max())
    recent = stats[(stats.team.isin(teams)) & (pd.to_numeric(stats.week, errors="coerce") >= recent_week - 3)].copy()
    names = sorted(set(recent.rush_player.dropna().astype(str)) | set(recent.reception_player.dropna().astype(str)))
    rows = []
    for player in names:
        rush = recent[recent.rush_player.astype(str) == player]
        receive = recent[recent.reception_player.astype(str) == player]
        touches = len(rush) + len(receive)
        red_zone = int((pd.to_numeric(rush.yards_to_goal, errors="coerce") <= 20).sum() +
                       (pd.to_numeric(receive.yards_to_goal, errors="coerce") <= 20).sum())
        tds = int((recent.touchdown_player.astype(str) == player).sum())
        source = rush if not rush.empty else receive
        if source.empty:
            continue
        position = positions.get(player, "")
        group = "RB" if position in {"RB", "FB"} else ("WR/TE" if position in {"WR", "TE"} else "")
        if not group:
            continue
        score = 50 + min(25, tds * 7) + min(15, red_zone * 1.5) + min(10, touches / 4)
        rows.append({"player": player, "team": str(source.iloc[0].team), "position": position,
                     "group": group, "tds": tds, "touches": touches, "red_zone": red_zone,
                     "score": round(score, 1)})
    return pd.DataFrame(rows)


def build_card(games: list[dict], stats: pd.DataFrame, roster: pd.DataFrame) -> list[dict]:
    form = _team_form(stats)
    candidates = touchdown_candidates(stats, roster, {g[k] for g in games for k in ("home_key", "away_key")})
    cards = []
    for game in games:
        pool = candidates[candidates.team.isin([game["home_key"], game["away_key"]])] if not candidates.empty else candidates
        rb = pool[pool.group == "RB"].sort_values("score", ascending=False)
        receiver = pool[pool.group == "WR/TE"].sort_values("score", ascending=False)
        if rb.empty or receiver.empty:
            continue
        projected_home_margin = float(form.get(game["home_key"], 0)) - float(form.get(game["away_key"], 0)) + 2.5
        home_edge = projected_home_margin + game["home_line"]
        pick_home = home_edge >= 0
        line = game["home_line"] if pick_home else game["away_line"]
        selection = game["home"] if pick_home else game["away"]
        game.update({"spread_team": selection, "spread_line": line, "projected_home_margin": round(projected_home_margin, 1),
                     "edge": round(abs(home_edge), 1), "rb": rb.iloc[0].to_dict(), "receiver": receiver.iloc[0].to_dict()})
        game["ranked_matchup"] = game["home_rank"] <= 25 and game["away_rank"] <= 25
        rank_strength = 26 - min(game["home_rank"], game["away_rank"])
        game["card_score"] = round(game["edge"] + rank_strength / 5 + (game["rb"]["score"] + game["receiver"]["score"]) / 40, 1)
        cards.append(game)
    # Ranked-vs-ranked games always precede games containing only one Top 25 team.
    cards.sort(key=lambda x: (x["ranked_matchup"], x["card_score"]), reverse=True)
    if len(cards) < 5:
        raise RuntimeError(f"NCAAF Best Card requires 5 complete Top 25 games; only {len(cards)} qualified.")
    return cards[:5]


def grade_archive(archive: list[dict], completed_games: list[dict], stats: pd.DataFrame) -> list[dict]:
    game_map = {g["event_id"]: g for g in completed_games if g["completed"]}
    results = []
    for pick in archive:
        game = game_map.get(str(pick.get("event_id", "")))
        if not game:
            continue
        component = pick.get("component", "")
        result, actual = "PENDING", ""
        if component == "Spread":
            team_score = game["home_score"] if pick["selection"] == game["home"] else game["away_score"]
            opp_score = game["away_score"] if pick["selection"] == game["home"] else game["home_score"]
            covered = team_score + float(pick["line"]) - opp_score
            result = "PUSH" if math.isclose(covered, 0) else ("HIT" if covered > 0 else "MISS")
            actual = f"{game['away']} {game['away_score']:.0f}, {game['home']} {game['home_score']:.0f}"
        else:
            count = int((stats.touchdown_player.astype(str) == str(pick["selection"])).sum())
            result, actual = ("HIT" if count > 0 else "MISS"), f"{count} TD"
        results.append({**pick, "result": result, "actual": actual})
    return results
