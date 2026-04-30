import json
import unicodedata
from collections import defaultdict
from shared.db import fetch_all, execute_many

import sys
EVAL_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-30"
BOOK_KEY = sys.argv[2] if len(sys.argv) > 2 else "draftkings"
BULLPEN_K_MAX = 0.250
SYSTEM_ID = "PROHITS_CANDIDATE_A_SEP_L1_GUARD_BP_K250"
MARKET_TYPE = "batter_hits_o05"
CALC_VERSION = "v0.1-market-filter"

def safe_div(a, b):
    return a / b if b else 0

def norm_name(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace(".", "").replace(",", "").split())

def hitter_features(hist):
    l10 = hist[-10:]
    l5 = hist[-5:]
    l3 = hist[-3:]

    ab10 = sum(int(x["ab"] or 0) for x in l10)
    pa10 = sum(int(x["pa"] or 0) for x in l10)
    h10 = sum(int(x["h"] or 0) for x in l10)
    so10 = sum(int(x["so"] or 0) for x in l10)

    ab5 = sum(int(x["ab"] or 0) for x in l5)
    pa5 = sum(int(x["pa"] or 0) for x in l5)
    h5 = sum(int(x["h"] or 0) for x in l5)
    so5 = sum(int(x["so"] or 0) for x in l5)

    pa3 = sum(int(x["pa"] or 0) for x in l3)
    so3 = sum(int(x["so"] or 0) for x in l3)

    avg_ab_l10 = safe_div(ab10, len(l10))
    avg_pa_l10 = safe_div(pa10, len(l10))
    avg_l10 = safe_div(h10, ab10)
    avg_l5 = safe_div(h5, ab5)
    k_rate_l5 = safe_div(so5, pa5)
    k_rate_l3 = safe_div(so3, pa3)

    games_with_hit_l10 = sum(1 for x in l10 if int(x["h"] or 0) >= 1)
    multi_hit_games_l10 = sum(1 for x in l10 if int(x["h"] or 0) >= 2)
    multi_hit_dependency_l10 = safe_div(multi_hit_games_l10, games_with_hit_l10)

    raw_l5_ab10 = 1 - ((1 - avg_l5) ** avg_ab_l10) if avg_ab_l10 else 0
    raw_l10_ab10 = 1 - ((1 - avg_l10) ** avg_ab_l10) if avg_ab_l10 else 0

    return {
        "avg_ab_l10": avg_ab_l10,
        "avg_pa_l10": avg_pa_l10,
        "avg_l10": avg_l10,
        "avg_l5": avg_l5,
        "k_rate_l5": k_rate_l5,
        "k_rate_l3": k_rate_l3,
        "games_with_hit_l10": games_with_hit_l10,
        "multi_hit_dependency_l10": multi_hit_dependency_l10,
        "raw_l5_ab10": raw_l5_ab10,
        "raw_l10_ab10": raw_l10_ab10,
    }

def get_starter_l5(rows):
    last5 = rows[-5:]
    if len(last5) < 5:
        return None

    ip_outs = sum(int(r["ip_outs"] or 0) for r in last5)
    h = sum(int(r["h"] or 0) for r in last5)
    bb = sum(int(r["bb"] or 0) for r in last5)
    so = sum(int(r["so"] or 0) for r in last5)
    bf = sum(int(r["bf"] or 0) for r in last5)

    innings = ip_outs / 3

    return {
        "starter_h9_l5": safe_div(h * 9, innings),
        "starter_whip_l5": safe_div(h + bb, innings),
        "starter_k_rate_l5": safe_div(so, bf),
        "starter_h_per_bf_l5": safe_div(h, bf),
    }

def get_bullpen_l10(rows):
    last10 = rows[-10:]
    if len(last10) < 10:
        return None

    ip_outs = sum(int(r["ip_outs"] or 0) for r in last10)
    h = sum(int(r["h"] or 0) for r in last10)
    bb = sum(int(r["bb"] or 0) for r in last10)
    so = sum(int(r["so"] or 0) for r in last10)
    bf = sum(int(r["bf"] or 0) for r in last10)

    innings = ip_outs / 3

    return {
        "bullpen_h9_l10": safe_div(h * 9, innings),
        "bullpen_whip_l10": safe_div(h + bb, innings),
        "bullpen_k_rate_l10": safe_div(so, bf),
    }

games = {
    r["game_pk"]: dict(r)
    for r in fetch_all("""
        select
            game_pk,
            game_date,
            away_team_id,
            home_team_id,
            away_probable_pitcher_id,
            home_probable_pitcher_id,
            game_datetime
        from core.games
        where game_date = %s;
    """, [EVAL_DATE])
}

lineups = [dict(r) for r in fetch_all("""
    select
        lv.game_pk,
        lv.team_id,
        lv.player_id,
        lv.player_name,
        lv.lineup_spot,
        lv.position
    from prohits.lineup_validation lv
    join core.games g on g.game_pk = lv.game_pk
    where g.game_date = %s
      and lv.lineup_spot between 1 and 2
    order by lv.game_pk, lv.team_id, lv.lineup_spot;
""", [EVAL_DATE])]

player_logs = [dict(r) for r in fetch_all("""
    select
        player_id,
        game_date,
        game_pk,
        ab,
        pa,
        h,
        so
    from prohits.player_game_logs
    where game_date < %s
    order by player_id, game_date, game_pk;
""", [EVAL_DATE])]

hist_by_player = defaultdict(list)
for r in player_logs:
    hist_by_player[r["player_id"]].append(r)

starter_rows = [dict(r) for r in fetch_all("""
    select
        game_pk,
        player_id,
        game_date,
        ip_outs,
        h,
        bb,
        so,
        bf
    from core.player_boxscore_pitching
    where started = true
      and game_date < %s
      and ip_outs is not null
      and ip_outs > 0
    order by player_id, game_date, game_pk;
""", [EVAL_DATE])]

starter_by_pitcher = defaultdict(list)
for r in starter_rows:
    starter_by_pitcher[r["player_id"]].append(r)

bullpen_rows = [dict(r) for r in fetch_all("""
    select
        game_pk,
        team_id,
        game_date,
        sum(ip_outs)::int as ip_outs,
        sum(h)::int as h,
        sum(bb)::int as bb,
        sum(so)::int as so,
        sum(bf)::int as bf
    from core.player_boxscore_pitching
    where started = false
      and game_date < %s
      and ip_outs is not null
      and ip_outs > 0
    group by game_pk, team_id, game_date
    order by team_id, game_date, game_pk;
""", [EVAL_DATE])]

bullpen_by_team = defaultdict(list)
for r in bullpen_rows:
    bullpen_by_team[r["team_id"]].append(r)

market_rows = [dict(r) for r in fetch_all("""
    select
        m.game_pk,
        mba.book_key,
        mba.book_title,
        mba.player_name,
        mba.market_status,
        mba.has_o05,
        mba.o05_over_price,
        mba.has_o15,
        mba.o15_over_price
    from prohits.market_batter_hits_availability mba
    join prohits.market_event_game_map m
      on m.market_date = mba.market_date
     and m.event_id = mba.event_id
    where mba.market_date = %s
      and mba.book_key = %s;
""", [EVAL_DATE, BOOK_KEY])]

market_by_game_player = {}
for r in market_rows:
    market_by_game_player[(r["game_pk"], norm_name(r["player_name"]))] = r

insert_rows = []

for row in lineups:
    game = games.get(row["game_pk"])
    if not game:
        continue

    if row["team_id"] == game["home_team_id"]:
        opposing_starter_id = game["away_probable_pitcher_id"]
        opponent_team_id = game["away_team_id"]
    elif row["team_id"] == game["away_team_id"]:
        opposing_starter_id = game["home_probable_pitcher_id"]
        opponent_team_id = game["home_team_id"]
    else:
        continue

    hist = hist_by_player.get(row["player_id"], [])
    if len(hist) < 10:
        continue

    hf = hitter_features(hist)
    sf = get_starter_l5(starter_by_pitcher.get(opposing_starter_id, []))
    bp = get_bullpen_l10(bullpen_by_team.get(opponent_team_id, []))

    if not sf or not bp:
        continue

    checks = [
        ("lineup_spot_1_2", row["lineup_spot"] in (1, 2)),
        ("avg_ab_l10>=4.00", hf["avg_ab_l10"] >= 4.00),
        ("avg_pa_l10>=4.20", hf["avg_pa_l10"] >= 4.20),
        ("raw_l5_ab10>=.72", hf["raw_l5_ab10"] >= 0.72),
        ("raw_l10_ab10>=.58", hf["raw_l10_ab10"] >= 0.58),
        ("k_rate_l5<=.25", hf["k_rate_l5"] <= 0.25),
        ("games_with_hit_l10>=5", hf["games_with_hit_l10"] >= 5),
        ("avg_l10>=.300", hf["avg_l10"] >= 0.300),
        ("avg_l5>=.260", hf["avg_l5"] >= 0.260),
        ("k_rate_l3<=.270", hf["k_rate_l3"] <= 0.270),
        ("multi_hit_dependency_l10<=.750", hf["multi_hit_dependency_l10"] <= 0.750),
        ("starter_h9_l5>=8.5", sf["starter_h9_l5"] >= 8.5),
        ("starter_whip_l5>=1.35", sf["starter_whip_l5"] >= 1.35),
        ("starter_k_rate_l5<=.220", sf["starter_k_rate_l5"] <= 0.220),
        ("starter_h_per_bf_l5>=.220", sf["starter_h_per_bf_l5"] >= 0.220),
        ("bullpen_k_rate_l10<=.250", bp["bullpen_k_rate_l10"] <= BULLPEN_K_MAX),
    ]

    filters_passed = [label for label, ok in checks if ok]
    filters_failed = [label for label, ok in checks if not ok]

    if filters_failed:
        continue

    market = market_by_game_player.get((row["game_pk"], norm_name(row["player_name"])))

    if market is None:
        book_title = None
        market_status = "NOT_LISTED"
        has_o05 = False
        o05_over_price = None
        has_o15 = False
        o15_over_price = None
        market_filter_status = "MARKET_NOT_LISTED"
        activation_status = "MARKET_EXCLUDED"
    else:
        book_title = market["book_title"]
        market_status = market["market_status"]
        has_o05 = market["has_o05"]
        o05_over_price = market["o05_over_price"]
        has_o15 = market["has_o15"]
        o15_over_price = market["o15_over_price"]

        if market_status == "AVAILABLE_O05":
            market_filter_status = "MARKET_OK_O05"
            activation_status = "ACTIVE_O05"
        elif market_status == "ONLY_O15":
            market_filter_status = "MARKET_EXCLUDED_ONLY_O15"
            activation_status = "MARKET_EXCLUDED"
        else:
            market_filter_status = "MARKET_OTHER"
            activation_status = "MARKET_EXCLUDED"

    hit_score = 100.0

    insert_rows.append({
        "evaluation_date": EVAL_DATE,
        "game_pk": row["game_pk"],
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "team_id": row["team_id"],
        "opponent_team_id": opponent_team_id,
        "system_id": SYSTEM_ID,
        "market_type": MARKET_TYPE,
        "hit_score": hit_score,
        "filters_passed": json.dumps({
            "rules": filters_passed,
            "hitter": hf,
            "starter": sf,
            "bullpen": bp,
        }),
        "filters_failed": json.dumps({"rules": filters_failed}),
        "activation_status": activation_status,
        "actual_1plus_hit": None,
        "success": None,
        "data_quality_status": "OK",
        "calculation_version": CALC_VERSION,
        "book_key": BOOK_KEY,
        "book_title": book_title,
        "market_status": market_status,
        "has_o05": has_o05,
        "o05_over_price": o05_over_price,
        "has_o15": has_o15,
        "o15_over_price": o15_over_price,
        "market_filter_status": market_filter_status,
    })

execute_many("""
    insert into prohits.hit_candidates
    (
        evaluation_date,
        game_pk,
        player_id,
        player_name,
        team_id,
        opponent_team_id,
        system_id,
        market_type,
        hit_score,
        filters_passed,
        filters_failed,
        activation_status,
        actual_1plus_hit,
        success,
        data_quality_status,
        calculation_version,
        book_key,
        book_title,
        market_status,
        has_o05,
        o05_over_price,
        has_o15,
        o15_over_price,
        market_filter_status,
        updated_at
    )
    values
    (
        %(evaluation_date)s,
        %(game_pk)s,
        %(player_id)s,
        %(player_name)s,
        %(team_id)s,
        %(opponent_team_id)s,
        %(system_id)s,
        %(market_type)s,
        %(hit_score)s,
        %(filters_passed)s::jsonb,
        %(filters_failed)s::jsonb,
        %(activation_status)s,
        %(actual_1plus_hit)s,
        %(success)s,
        %(data_quality_status)s,
        %(calculation_version)s,
        %(book_key)s,
        %(book_title)s,
        %(market_status)s,
        %(has_o05)s,
        %(o05_over_price)s,
        %(has_o15)s,
        %(o15_over_price)s,
        %(market_filter_status)s,
        now()
    )
    on conflict (evaluation_date, book_key, system_id, market_type, player_id, game_pk)
    do update set
        player_name = excluded.player_name,
        team_id = excluded.team_id,
        opponent_team_id = excluded.opponent_team_id,
        hit_score = excluded.hit_score,
        filters_passed = excluded.filters_passed,
        filters_failed = excluded.filters_failed,
        activation_status = excluded.activation_status,
        actual_1plus_hit = excluded.actual_1plus_hit,
        success = excluded.success,
        data_quality_status = excluded.data_quality_status,
        calculation_version = excluded.calculation_version,
        book_title = excluded.book_title,
        market_status = excluded.market_status,
        has_o05 = excluded.has_o05,
        o05_over_price = excluded.o05_over_price,
        has_o15 = excluded.has_o15,
        o15_over_price = excluded.o15_over_price,
        market_filter_status = excluded.market_filter_status,
        updated_at = now()
""", insert_rows)

print("=" * 90)
print("PROHITS HIT CANDIDATES SAVED")
print("=" * 90)
print(f"evaluation_date={EVAL_DATE}")
print(f"book_key={BOOK_KEY}")
print(f"system_id={SYSTEM_ID}")
print(f"rows_saved={len(insert_rows)}")

for r in insert_rows:
    print(
        f"{r['player_name']} | game_pk={r['game_pk']} | "
        f"activation={r['activation_status']} | "
        f"market={r['market_status']} | "
        f"O0.5={r['o05_over_price']} | O1.5={r['o15_over_price']}"
    )


