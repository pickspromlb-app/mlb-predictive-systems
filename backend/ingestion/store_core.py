from datetime import date
import json
from shared.db import execute_many, fetch_all

def as_int(v, default=0):
    try:
        if v in (None, '', '--'):
            return default
        return int(float(v))
    except Exception:
        return default

def parse_ip_outs(v):
    if v in (None, '', '--'):
        return 0
    s = str(v)
    if '.' in s:
        a,b = s.split('.',1)
        return as_int(a)*3 + as_int(b)
    return as_int(s)*3

def store_schedule(payload: dict, target_date: date) -> int:
    teams = {}
    venues = {}
    games = []
    for d in payload.get('dates', []):
        for g in d.get('games', []):
            away = g.get('teams', {}).get('away', {})
            home = g.get('teams', {}).get('home', {})
            at = away.get('team', {})
            ht = home.get('team', {})
            for t in (at, ht):
                if t.get('id'):
                    teams[t['id']] = {'team_id': t['id'], 'team_name': t.get('name',''), 'abbreviation': t.get('abbreviation')}
            venue = g.get('venue') or {}
            if venue.get('id'):
                venues[venue['id']] = {'venue_id': venue['id'], 'venue_name': venue.get('name','')}
            games.append({
                'game_pk': g.get('gamePk'), 'season': as_int(g.get('season') or target_date.year), 'game_date': target_date,
                'game_datetime': g.get('gameDate'), 'status': (g.get('status') or {}).get('abstractGameState'),
                'detailed_state': (g.get('status') or {}).get('detailedState'), 'away_team_id': at.get('id'), 'home_team_id': ht.get('id'),
                'away_score': away.get('score'), 'home_score': home.get('score'), 'venue_id': venue.get('id'),
                'away_probable_pitcher_id': (away.get('probablePitcher') or {}).get('id'), 'home_probable_pitcher_id': (home.get('probablePitcher') or {}).get('id')
            })
    execute_many('insert into core.teams (team_id, team_name, abbreviation) values (%(team_id)s,%(team_name)s,%(abbreviation)s) on conflict (team_id) do update set team_name=excluded.team_name, abbreviation=excluded.abbreviation, updated_at=now()', teams.values())
    execute_many('insert into core.venues (venue_id, venue_name) values (%(venue_id)s,%(venue_name)s) on conflict (venue_id) do update set venue_name=excluded.venue_name, updated_at=now()', venues.values())
    execute_many('''insert into core.games (game_pk,season,game_date,game_datetime,status,detailed_state,away_team_id,home_team_id,away_score,home_score,venue_id,away_probable_pitcher_id,home_probable_pitcher_id,source_timestamp)
    values (%(game_pk)s,%(season)s,%(game_date)s,%(game_datetime)s,%(status)s,%(detailed_state)s,%(away_team_id)s,%(home_team_id)s,%(away_score)s,%(home_score)s,%(venue_id)s,%(away_probable_pitcher_id)s,%(home_probable_pitcher_id)s,now())
    on conflict (game_pk) do update set status=excluded.status,detailed_state=excluded.detailed_state,away_score=excluded.away_score,home_score=excluded.home_score,away_probable_pitcher_id=excluded.away_probable_pitcher_id,home_probable_pitcher_id=excluded.home_probable_pitcher_id,updated_at=now()''', games)
    return len(games)

def store_linescore(game_pk: int, payload: dict):
    innings = payload.get('innings') or []
    away_f5 = sum(as_int((i.get('away') or {}).get('runs')) for i in innings[:5])
    home_f5 = sum(as_int((i.get('home') or {}).get('runs')) for i in innings[:5])
    away = (payload.get('teams') or {}).get('away') or {}
    home = (payload.get('teams') or {}).get('home') or {}
    row = {'game_pk': game_pk, 'away_runs': as_int(away.get('runs')), 'home_runs': as_int(home.get('runs')), 'away_hits': as_int(away.get('hits')), 'home_hits': as_int(home.get('hits')), 'away_errors': as_int(away.get('errors')), 'home_errors': as_int(home.get('errors')), 'away_f5_runs': away_f5, 'home_f5_runs': home_f5, 'innings': json.dumps(innings)}
    execute_many('''insert into core.game_linescore (game_pk,away_runs,home_runs,away_hits,home_hits,away_errors,home_errors,away_f5_runs,home_f5_runs,innings,source_timestamp) values (%(game_pk)s,%(away_runs)s,%(home_runs)s,%(away_hits)s,%(home_hits)s,%(away_errors)s,%(home_errors)s,%(away_f5_runs)s,%(home_f5_runs)s,%(innings)s::jsonb,now()) on conflict (game_pk) do update set away_runs=excluded.away_runs,home_runs=excluded.home_runs,away_hits=excluded.away_hits,home_hits=excluded.home_hits,away_errors=excluded.away_errors,home_errors=excluded.home_errors,away_f5_runs=excluded.away_f5_runs,home_f5_runs=excluded.home_f5_runs,innings=excluded.innings,updated_at=now()''', [row])

def games_for_date(target_date: date):
    return fetch_all('select * from core.games where game_date=%s order by game_datetime', (target_date,))


def store_boxscore(game_pk: int, game_date: date, away_team_id: int, home_team_id: int, payload: dict):
    batting_rows = []
    pitching_rows = []
    player_pitching_rows = []

    for side, team_id, opp_id in [
        ('away', away_team_id, home_team_id),
        ('home', home_team_id, away_team_id)
    ]:
        team_data = ((payload.get('teams') or {}).get(side) or {})
        team_stats = team_data.get('teamStats') or {}

        batting = team_stats.get('batting') or {}
        batting_rows.append({
            'game_pk': game_pk,
            'team_id': team_id,
            'opponent_team_id': opp_id,
            'game_date': game_date,
            'home_away': side,
            'ab': as_int(batting.get('atBats')),
            'r': as_int(batting.get('runs')),
            'h': as_int(batting.get('hits')),
            'doubles': as_int(batting.get('doubles')),
            'triples': as_int(batting.get('triples')),
            'hr': as_int(batting.get('homeRuns')),
            'rbi': as_int(batting.get('rbi')),
            'bb': as_int(batting.get('baseOnBalls')),
            'ibb': as_int(batting.get('intentionalWalks')),
            'hbp': as_int(batting.get('hitByPitch')),
            'sf': as_int(batting.get('sacFlies')),
            'so': as_int(batting.get('strikeOuts')),
            'sb': as_int(batting.get('stolenBases')),
            'cs': as_int(batting.get('caughtStealing')),
            'lob': as_int(batting.get('leftOnBase')),
            'tb': as_int(batting.get('totalBases')),
            'pa': as_int(batting.get('plateAppearances'))
        })

        pitching = team_stats.get('pitching') or {}
        pitching_rows.append({
            'game_pk': game_pk,
            'team_id': team_id,
            'opponent_team_id': opp_id,
            'game_date': game_date,
            'home_away': side,
            'ip_outs': parse_ip_outs(pitching.get('inningsPitched')),
            'h': as_int(pitching.get('hits')),
            'r': as_int(pitching.get('runs')),
            'er': as_int(pitching.get('earnedRuns')),
            'bb': as_int(pitching.get('baseOnBalls')),
            'ibb': as_int(pitching.get('intentionalWalks')),
            'so': as_int(pitching.get('strikeOuts')),
            'hr': as_int(pitching.get('homeRuns')),
            'hbp': as_int(pitching.get('hitBatsmen') or pitching.get('hitByPitch')),
            'bf': as_int(pitching.get('battersFaced')),
            'pitches': as_int(pitching.get('numberOfPitches') or pitching.get('pitchesThrown')),
            'strikes': as_int(pitching.get('strikes'))
        })

        players = team_data.get('players') or {}
        pitcher_ids = team_data.get('pitchers') or []

        for idx, pitcher_id in enumerate(pitcher_ids):
            player_key = f"ID{pitcher_id}"
            player_data = players.get(player_key) or {}
            stats = player_data.get('stats') or {}
            player_pitching = stats.get('pitching') or {}

            if not player_pitching:
                continue

            player_pitching_rows.append({
                'game_pk': game_pk,
                'player_id': int(pitcher_id),
                'team_id': team_id,
                'opponent_team_id': opp_id,
                'game_date': game_date,
                'started': idx == 0,
                'ip_outs': parse_ip_outs(player_pitching.get('inningsPitched')),
                'h': as_int(player_pitching.get('hits')),
                'r': as_int(player_pitching.get('runs')),
                'er': as_int(player_pitching.get('earnedRuns')),
                'bb': as_int(player_pitching.get('baseOnBalls')),
                'ibb': as_int(player_pitching.get('intentionalWalks')),
                'so': as_int(player_pitching.get('strikeOuts')),
                'hr': as_int(player_pitching.get('homeRuns')),
                'hbp': as_int(player_pitching.get('hitBatsmen') or player_pitching.get('hitByPitch')),
                'bf': as_int(player_pitching.get('battersFaced')),
                'pitches': as_int(player_pitching.get('numberOfPitches') or player_pitching.get('pitchesThrown')),
                'strikes': as_int(player_pitching.get('strikes')),
                'data_quality_status': 'OK',
            })

    execute_many(
        """insert into core.team_boxscore_batting
        (game_pk,team_id,opponent_team_id,game_date,home_away,ab,r,h,doubles,triples,hr,rbi,bb,ibb,hbp,sf,so,sb,cs,lob,tb,pa,source_timestamp)
        values (%(game_pk)s,%(team_id)s,%(opponent_team_id)s,%(game_date)s,%(home_away)s,%(ab)s,%(r)s,%(h)s,%(doubles)s,%(triples)s,%(hr)s,%(rbi)s,%(bb)s,%(ibb)s,%(hbp)s,%(sf)s,%(so)s,%(sb)s,%(cs)s,%(lob)s,%(tb)s,%(pa)s,now())
        on conflict (game_pk,team_id) do update set
        ab=excluded.ab,r=excluded.r,h=excluded.h,doubles=excluded.doubles,triples=excluded.triples,hr=excluded.hr,rbi=excluded.rbi,bb=excluded.bb,ibb=excluded.ibb,hbp=excluded.hbp,sf=excluded.sf,so=excluded.so,sb=excluded.sb,cs=excluded.cs,lob=excluded.lob,tb=excluded.tb,pa=excluded.pa,updated_at=now()""",
        batting_rows
    )

    execute_many(
        """insert into core.team_boxscore_pitching
        (game_pk,team_id,opponent_team_id,game_date,home_away,ip_outs,h,r,er,bb,ibb,so,hr,hbp,bf,pitches,strikes,source_timestamp)
        values (%(game_pk)s,%(team_id)s,%(opponent_team_id)s,%(game_date)s,%(home_away)s,%(ip_outs)s,%(h)s,%(r)s,%(er)s,%(bb)s,%(ibb)s,%(so)s,%(hr)s,%(hbp)s,%(bf)s,%(pitches)s,%(strikes)s,now())
        on conflict (game_pk,team_id) do update set
        ip_outs=excluded.ip_outs,h=excluded.h,r=excluded.r,er=excluded.er,bb=excluded.bb,ibb=excluded.ibb,so=excluded.so,hr=excluded.hr,hbp=excluded.hbp,bf=excluded.bf,pitches=excluded.pitches,strikes=excluded.strikes,updated_at=now()""",
        pitching_rows
    )

    execute_many(
        """insert into core.player_boxscore_pitching
        (game_pk,player_id,team_id,opponent_team_id,game_date,started,ip_outs,h,r,er,bb,ibb,so,hr,hbp,bf,pitches,strikes,data_quality_status,source_timestamp)
        values (%(game_pk)s,%(player_id)s,%(team_id)s,%(opponent_team_id)s,%(game_date)s,%(started)s,%(ip_outs)s,%(h)s,%(r)s,%(er)s,%(bb)s,%(ibb)s,%(so)s,%(hr)s,%(hbp)s,%(bf)s,%(pitches)s,%(strikes)s,%(data_quality_status)s,now())
        on conflict (game_pk,player_id) do update set
        team_id=excluded.team_id,opponent_team_id=excluded.opponent_team_id,game_date=excluded.game_date,started=excluded.started,ip_outs=excluded.ip_outs,h=excluded.h,r=excluded.r,er=excluded.er,bb=excluded.bb,ibb=excluded.ibb,so=excluded.so,hr=excluded.hr,hbp=excluded.hbp,bf=excluded.bf,pitches=excluded.pitches,strikes=excluded.strikes,data_quality_status=excluded.data_quality_status,updated_at=now()""",
        player_pitching_rows
    )

    return {
        'team_batting': len(batting_rows),
        'team_pitching': len(pitching_rows),
        'player_pitching': len(player_pitching_rows)
    }
