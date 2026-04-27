from datetime import date
from shared.db import fetch_all, execute_many
from features.formulas import batting_metrics

WINDOWS = {'L1': 1, 'L3': 3, 'L5': 5, 'L7': 7, 'L10': 10}

def _sum_rows(rows):
    keys = ['ab','pa','h','doubles','triples','hr','bb','ibb','hbp','sf','so','tb']
    out = {k: sum(int(r.get(k) or 0) for r in rows) for k in keys}
    out['runs_scored'] = sum(int(r.get('r') or 0) for r in rows)
    return out

def build_daily_team_profiles(profile_date: date) -> int:
    teams_today = fetch_all('''
        select game_pk, away_team_id as team_id, home_team_id as opponent_team_id, 'away' as home_away from core.games where game_date=%s
        union all
        select game_pk, home_team_id as team_id, away_team_id as opponent_team_id, 'home' as home_away from core.games where game_date=%s
    ''', (profile_date, profile_date))
    rows = []
    for t in teams_today:
        team_id = t['team_id']
        hist = fetch_all('''
            select b.*, g.away_score, g.home_score, g.away_team_id, g.home_team_id
            from core.team_boxscore_batting b join core.games g on g.game_pk=b.game_pk
            where b.team_id=%s and b.game_date < %s
            order by b.game_date desc, b.game_pk desc limit 10
        ''', (team_id, profile_date))
        for stat_window, n in WINDOWS.items():
            sample = hist[:n]
            totals = _sum_rows(sample)
            m = batting_metrics(totals)
            gs = len(sample)
            runs = [int(r.get('r') or 0) for r in sample]
            allowed = []
            wins = 0
            for r in sample:
                tr = int(r.get('r') or 0)
                opp = int(r.get('home_score') or 0) if int(r.get('away_team_id')) == int(team_id) else int(r.get('away_score') or 0)
                allowed.append(opp)
                wins += 1 if tr > opp else 0
            rows.append({
                'profile_date': profile_date, 'team_id': team_id, 'opponent_team_id': t['opponent_team_id'], 'game_pk': t['game_pk'], 'home_away': t['home_away'], 'stat_window': stat_window, 'games_sample': gs,
                'runs_scored_avg': round(sum(runs)/gs,4) if gs else None, 'runs_allowed_avg': round(sum(allowed)/gs,4) if gs else None,
                'run_diff_avg': round((sum(runs)-sum(allowed))/gs,4) if gs else None, 'hit_avg': round(totals['h']/gs,4) if gs else None,
                'win_rate': round(wins/gs,4) if gs else None, 'scored_3plus_rate': round(sum(1 for x in runs if x>=3)/gs,4) if gs else None,
                'scored_5plus_rate': round(sum(1 for x in runs if x>=5)/gs,4) if gs else None, **totals, **m, 'metric_status': 'OK_INTERNAL' if gs else 'NO_SAMPLE'
            })
    return execute_many('''
        insert into propicks.daily_team_profile (profile_date,team_id,opponent_team_id,game_pk,home_away,stat_window,games_sample,runs_scored_avg,runs_allowed_avg,run_diff_avg,hit_avg,win_rate,scored_3plus_rate,scored_5plus_rate,ab,pa,h,doubles,triples,hr,bb,ibb,hbp,sf,so,tb,avg,obp,slg,ops,iso,babip,bb_rate,k_rate,bb_k_ratio,woba_internal,wraa_internal,wrc_internal,wrc_plus_internal,metric_status,calculated_at)
        values (%(profile_date)s,%(team_id)s,%(opponent_team_id)s,%(game_pk)s,%(home_away)s,%(stat_window)s,%(games_sample)s,%(runs_scored_avg)s,%(runs_allowed_avg)s,%(run_diff_avg)s,%(hit_avg)s,%(win_rate)s,%(scored_3plus_rate)s,%(scored_5plus_rate)s,%(ab)s,%(pa)s,%(h)s,%(doubles)s,%(triples)s,%(hr)s,%(bb)s,%(ibb)s,%(hbp)s,%(sf)s,%(so)s,%(tb)s,%(avg)s,%(obp)s,%(slg)s,%(ops)s,%(iso)s,%(babip)s,%(bb_rate)s,%(k_rate)s,%(bb_k_ratio)s,%(woba_internal)s,%(wraa_internal)s,%(wrc_internal)s,%(wrc_plus_internal)s,%(metric_status)s,now())
        on conflict (profile_date,team_id,stat_window) do update set games_sample=excluded.games_sample,runs_scored_avg=excluded.runs_scored_avg,runs_allowed_avg=excluded.runs_allowed_avg,run_diff_avg=excluded.run_diff_avg,hit_avg=excluded.hit_avg,win_rate=excluded.win_rate,scored_3plus_rate=excluded.scored_3plus_rate,scored_5plus_rate=excluded.scored_5plus_rate,avg=excluded.avg,obp=excluded.obp,slg=excluded.slg,ops=excluded.ops,iso=excluded.iso,babip=excluded.babip,bb_rate=excluded.bb_rate,k_rate=excluded.k_rate,woba_internal=excluded.woba_internal,wraa_internal=excluded.wraa_internal,wrc_internal=excluded.wrc_internal,wrc_plus_internal=excluded.wrc_plus_internal,metric_status=excluded.metric_status,updated_at=now()
    ''', rows)

