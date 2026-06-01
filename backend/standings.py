from __future__ import annotations
from models import StandingsEntry
from google.cloud import firestore as _firestore

DEFAULT_POINTS_SYSTEM = {"win": 3, "draw": 1, "loss": 0, "draws_allowed": True}
DEFAULT_TIEBREAKER_RULES = ("goal_difference", "goals_for", "head_to_head")


def compute_standings(
    matches: list[dict],
    teams: dict[str, str],
    points_system: dict,
    tiebreaker_rules: list[str],
) -> dict[str, list[StandingsEntry]]:
    by_group: dict[str, list[dict]] = {}
    for m in matches:
        g = m.get("girone", "?")
        by_group.setdefault(g, []).append(m)

    result: dict[str, list[StandingsEntry]] = {}
    for group_id, group_matches in by_group.items():
        team_ids: set[str] = set()
        for m in group_matches:
            team_ids.update(m["squadre"])

        stats: dict[str, dict] = {
            tid: {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
            for tid in team_ids
        }

        for m in group_matches:
            if m.get("home_goals") is None or m.get("away_goals") is None:
                continue
            home, away = m["squadre"][0], m["squadre"][1]
            hg, ag = int(m["home_goals"]), int(m["away_goals"])
            stats[home]["played"] += 1
            stats[away]["played"] += 1
            stats[home]["gf"] += hg
            stats[home]["ga"] += ag
            stats[away]["gf"] += ag
            stats[away]["ga"] += hg
            if hg > ag:
                stats[home]["wins"] += 1
                stats[away]["losses"] += 1
            elif ag > hg:
                stats[away]["wins"] += 1
                stats[home]["losses"] += 1
            else:
                stats[home]["draws"] += 1
                stats[away]["draws"] += 1

        win_pts = points_system.get("win", 3)
        draw_pts = points_system.get("draw", 1)
        loss_pts = points_system.get("loss", 0)

        entries = []
        for tid, s in stats.items():
            pts = s["wins"] * win_pts + s["draws"] * draw_pts + s["losses"] * loss_pts
            entries.append({
                "team_id": tid,
                "team_name": teams.get(tid, tid),
                "played": s["played"],
                "wins": s["wins"],
                "draws": s["draws"],
                "losses": s["losses"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_difference": s["gf"] - s["ga"],
                "points": pts,
            })

        sorted_entries = _sort_entries(entries, group_matches, points_system, tiebreaker_rules)

        result[group_id] = [
            StandingsEntry(position=i + 1, **e)
            for i, e in enumerate(sorted_entries)
        ]

    return result


def _sort_entries(
    entries: list[dict],
    group_matches: list[dict],
    points_system: dict,
    tiebreaker_rules: list[str],
) -> list[dict]:
    def non_h2h_key(e: dict) -> tuple:
        key: list = [-e["points"]]
        for rule in tiebreaker_rules:
            if rule == "goal_difference":
                key.append(-e["goal_difference"])
            elif rule == "goals_for":
                key.append(-e["goals_for"])
        return tuple(key)

    sorted_entries = sorted(entries, key=non_h2h_key)

    if "head_to_head" not in tiebreaker_rules:
        return sorted_entries

    h2h_idx = tiebreaker_rules.index("head_to_head")
    pre_h2h_rules = tiebreaker_rules[:h2h_idx]

    def pre_h2h_key(e: dict) -> tuple:
        key: list = [-e["points"]]
        for rule in pre_h2h_rules:
            if rule == "goal_difference":
                key.append(-e["goal_difference"])
            elif rule == "goals_for":
                key.append(-e["goals_for"])
        return tuple(key)

    result: list[dict] = []
    i = 0
    while i < len(sorted_entries):
        j = i + 1
        while j < len(sorted_entries) and pre_h2h_key(sorted_entries[j]) == pre_h2h_key(sorted_entries[i]):
            j += 1
        group = sorted_entries[i:j]
        if len(group) > 1:
            group = _apply_head_to_head(group, group_matches, points_system)
        result.extend(group)
        i = j

    return result


def _apply_head_to_head(
    tied: list[dict],
    all_matches: list[dict],
    points_system: dict,
) -> list[dict]:
    tied_ids = {e["team_id"] for e in tied}
    h2h_matches = [
        m for m in all_matches
        if set(m["squadre"]) <= tied_ids
        and m.get("home_goals") is not None
        and m.get("away_goals") is not None
    ]
    mini: dict[str, dict] = {tid: {"pts": 0, "gd": 0, "gf": 0} for tid in tied_ids}
    win_pts = points_system.get("win", 3)
    draw_pts = points_system.get("draw", 1)
    loss_pts = points_system.get("loss", 0)

    for m in h2h_matches:
        home, away = m["squadre"][0], m["squadre"][1]
        hg, ag = int(m["home_goals"]), int(m["away_goals"])
        mini[home]["gf"] += hg
        mini[home]["gd"] += hg - ag
        mini[away]["gf"] += ag
        mini[away]["gd"] += ag - hg
        if hg > ag:
            mini[home]["pts"] += win_pts
            mini[away]["pts"] += loss_pts
        elif ag > hg:
            mini[away]["pts"] += win_pts
            mini[home]["pts"] += loss_pts
        else:
            mini[home]["pts"] += draw_pts
            mini[away]["pts"] += draw_pts

    return sorted(
        tied,
        key=lambda e: (
            -mini[e["team_id"]]["pts"],
            -mini[e["team_id"]]["gd"],
            -mini[e["team_id"]]["gf"],
        ),
    )


@_firestore.transactional
def _update_standings_in_transaction(
    transaction,
    tournament_ref,
    team_names: dict[str, str],
    points_system: dict,
    tiebreaker_rules: list[str],
) -> None:
    match_docs = list(tournament_ref.collection("matches").stream(transaction=transaction))
    match_dicts = [{"id": m.id, **m.to_dict()} for m in match_docs]

    standings = compute_standings(match_dicts, team_names, points_system, tiebreaker_rules)

    standings_col = tournament_ref.collection("standings")
    for group_id, entries in standings.items():
        transaction.set(
            standings_col.document(group_id),
            {
                "group_name": group_id,
                "computed_at": _firestore.SERVER_TIMESTAMP,
                "entries": [e.model_dump() for e in entries],
            },
        )


def compute_and_cache_standings(db, tournament_id: str) -> None:
    t_ref = db.collection("tournaments").document(tournament_id)

    schema_doc = t_ref.collection("config").document("schema").get()
    config = schema_doc.to_dict() or {}
    points_system = config.get("points_system", DEFAULT_POINTS_SYSTEM)
    tiebreaker_rules = config.get("tiebreaker_rules", list(DEFAULT_TIEBREAKER_RULES))

    team_names = {
        d.id: d.to_dict().get("nome", d.id)
        for d in t_ref.collection("teams").stream()
    }

    _update_standings_in_transaction(
        db.transaction(),
        t_ref,
        team_names,
        points_system,
        tiebreaker_rules,
    )
