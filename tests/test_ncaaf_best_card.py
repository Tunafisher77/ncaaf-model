import unittest

import pandas as pd

from ncaaf_best_card import build_card


class NcaafBestCardTests(unittest.TestCase):
    def test_ranked_vs_ranked_games_are_always_preferred(self):
        games = []
        for index in range(6):
            both_ranked = index == 5
            games.append({
                "event_id": str(index), "home": f"Home {index}", "away": f"Away {index}",
                "home_key": f"Home {index}", "away_key": f"Away {index}",
                "home_rank": 10 if both_ranked else 99, "away_rank": 12 if both_ranked else index + 1,
                "home_line": -3.0, "away_line": 3.0, "kickoff": "", "odds_provider": "test",
            })
        stats_rows = []
        roster_rows = []
        for index in range(6):
            for team in (f"Home {index}", f"Away {index}"):
                roster_rows += [{"full_name": f"{team} Back", "position": "RB"},
                                {"full_name": f"{team} Receiver", "position": "WR"}]
                for play, (column, player) in enumerate((("rush_player", f"{team} Back"),
                                                         ("reception_player", f"{team} Receiver"))):
                    row = {"game_id": index, "season": 2026, "week": 2, "team": team,
                           "team_score": 30, "opponent_score": 20, "rush_player": None,
                           "reception_player": None, "touchdown_player": player, "yards_to_goal": 10}
                    row[column] = player
                    stats_rows.append(row)
        cards = build_card(games, pd.DataFrame(stats_rows), pd.DataFrame(roster_rows))
        self.assertEqual(cards[0]["event_id"], "5")


if __name__ == "__main__":
    unittest.main()
