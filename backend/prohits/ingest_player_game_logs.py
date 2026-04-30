import asyncio
import sys
from datetime import date

from ingestion.mlb_stats_api import MLBStatsAPI
from shared.db import fetch_all, execute_many


def as_int(value, default=0):
    try:
        if value in (None, "", "--"):
            return default
        return int(float(value))
    except Exception:
        return default


def parse_lineup_spot(player_obj: dict):
    raw = player_obj.get("battingOrder")

    if raw in (None, "", "--"):
        return None

    try:
        # MLB usually stores battingOrder as "100", "200", ..., "900"
        value = int(str(raw))
        if value >= 100:
            return value // 100
        return value
    except Exception:
        return None


def parse_player_rows(
    game_pk: int,
    game_date: date,
    side: str,
    team_id: int,
    opponent_team_id: int,
    boxscore_payload: dict,
) -> list[dict]:
    team_data = ((boxscore_payload.get("teams") or {}).get(side) or {})
    players = team_data.get("players") or {}

    rows = []

    for _, player_obj in players.items():
        person = player_obj.get("person") or {}
        stats = player_obj.get("stats") or {}
        batting = stats.get("batting") or {}

        lineup_spot = parse_lineup_spot(player_obj)

        # Skip players with no batting record and no lineup slot.
        if not batting and lineup_spot is None:
            continue

        player_id = person.get("id")
        if not player_id:
            continue

        position_obj = player_obj.get("position") or {}
        position = position_obj.get("abbreviation") or position_obj.get("code")

        ab = as_int(batting.get("atBats"))
        h = as_int(batting.get("hits"))
        bb = as_int(batting.get("baseOnBalls"))
        ibb = as_int(batting.get("intentionalWalks"))
        hbp = as_int(batting.get("hitByPitch"))
        sf = as_int(batting.get("sacFlies"))
        so = as_int(batting.get("strikeOuts"))

        pa = as_int(batting.get("plateAppearances"))
        if pa == 0:
            pa = ab + bb + hbp + sf

        rows.append({
            "game_pk": game_pk,
            "game_date": game_date,
            "player_id": int(player_id),
            "player_name": person.get("fullName"),
            "team_id": team_id,
            "opponent_team_id": opponent_team_id,
            "home_away": side.upper(),
            "lineup_spot": lineup_spot,
            "position": position,
            "bat_side": None,
            "throw_side": None,
            "ab": ab,
            "r": as_int(batting.get("runs")),
            "h": h,
            "doubles": as_int(batting.get("doubles")),
            "triples": as_int(batting.get("triples")),
            "hr": as_int(batting.get("homeRuns")),
            "rbi": as_int(batting.get("rbi")),
            "bb": bb,
            "ibb": ibb,
            "hbp": hbp,
            "sf": sf,
            "so": so,
            "tb": as_int(batting.get("totalBases")),
            "pa": pa,
            "hit_1plus": h >= 1,
            "data_quality_status": "OK" if pa > 0 or ab > 0 else "NO_PA",
        })

    return rows


async def ingest_player_game_logs(target_date: date) -> dict:
    games = fetch_all("""
        select
          game_pk,
          game_date,
          away_team_id,
          home_team_id,
          status,
          detailed_state
        from core.games
        where game_date = %s
        order by game_datetime
    """, (target_date,))

    api = MLBStatsAPI()

    all_rows = []
    games_processed = 0

    for game in games:
        game_pk = int(game["game_pk"])
        away_team_id = int(game["away_team_id"])
        home_team_id = int(game["home_team_id"])

        boxscore = await api.boxscore(game_pk)

        all_rows.extend(parse_player_rows(
            game_pk=game_pk,
            game_date=target_date,
            side="away",
            team_id=away_team_id,
            opponent_team_id=home_team_id,
            boxscore_payload=boxscore,
        ))

        all_rows.extend(parse_player_rows(
            game_pk=game_pk,
            game_date=target_date,
            side="home",
            team_id=home_team_id,
            opponent_team_id=away_team_id,
            boxscore_payload=boxscore,
        ))

        games_processed += 1

    inserted = execute_many(
        """
        insert into prohits.player_game_logs (
          game_pk,
          game_date,
          player_id,
          player_name,
          team_id,
          opponent_team_id,
          home_away,
          lineup_spot,
          position,
          bat_side,
          throw_side,
          ab,
          r,
          h,
          doubles,
          triples,
          hr,
          rbi,
          bb,
          ibb,
          hbp,
          sf,
          so,
          tb,
          pa,
          hit_1plus,
          data_quality_status,
          source,
          source_timestamp,
          updated_at
        )
        values (
          %(game_pk)s,
          %(game_date)s,
          %(player_id)s,
          %(player_name)s,
          %(team_id)s,
          %(opponent_team_id)s,
          %(home_away)s,
          %(lineup_spot)s,
          %(position)s,
          %(bat_side)s,
          %(throw_side)s,
          %(ab)s,
          %(r)s,
          %(h)s,
          %(doubles)s,
          %(triples)s,
          %(hr)s,
          %(rbi)s,
          %(bb)s,
          %(ibb)s,
          %(hbp)s,
          %(sf)s,
          %(so)s,
          %(tb)s,
          %(pa)s,
          %(hit_1plus)s,
          %(data_quality_status)s,
          'MLB_STATS_API_BOXSCORE',
          now(),
          now()
        )
        on conflict (game_pk, player_id) do update set
          player_name = excluded.player_name,
          team_id = excluded.team_id,
          opponent_team_id = excluded.opponent_team_id,
          home_away = excluded.home_away,
          lineup_spot = excluded.lineup_spot,
          position = excluded.position,
          bat_side = excluded.bat_side,
          throw_side = excluded.throw_side,
          ab = excluded.ab,
          r = excluded.r,
          h = excluded.h,
          doubles = excluded.doubles,
          triples = excluded.triples,
          hr = excluded.hr,
          rbi = excluded.rbi,
          bb = excluded.bb,
          ibb = excluded.ibb,
          hbp = excluded.hbp,
          sf = excluded.sf,
          so = excluded.so,
          tb = excluded.tb,
          pa = excluded.pa,
          hit_1plus = excluded.hit_1plus,
          data_quality_status = excluded.data_quality_status,
          source = excluded.source,
          source_timestamp = now(),
          updated_at = now()
        """,
        all_rows,
    )

    return {
        "system": "ProHitsMLB",
        "target_date": target_date.isoformat(),
        "games_found": len(games),
        "games_processed": games_processed,
        "player_rows_upserted": inserted,
    }


async def main_async():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m prohits.ingest_player_game_logs YYYY-MM-DD")

    target_date = date.fromisoformat(sys.argv[1])
    result = await ingest_player_game_logs(target_date)
    print(result)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
