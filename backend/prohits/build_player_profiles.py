from datetime import date
from shared.db import fetch_all, execute_many
from features.formulas import batting_metrics

WINDOWS = {'L1': 1, 'L3': 3, 'L5': 5, 'L7': 7, 'L10': 10}

def build_player_profiles(stat_date: date) -> int:
    players = fetch_all('select distinct player_id, team_id from core.player_boxscore_batting where game_date < %s', (stat_date,))
    rows = []
    for p in players:
        hist = fetch_all('select * from core.player_boxscore_batting where player_id=%s and game_date < %s order by game_date desc, game_pk desc limit 10', (p['player_id'], stat_date))
        for stat_window, n in WINDOWS.items():
            sample = hist[:n]
            if not sample:
                continue
            totals = {k: sum(int(r.get(k) or 0) for r in sample) for k in ['ab','pa','h','doubles','triples','hr','bb','ibb','hbp','sf','so','tb']}
            m = batting_metrics(totals)
            gs = len(sample)
            games_with_hit = sum(1 for r in sample if int(r.get('h') or 0) >= 1)
            rows.append({'stat_date': stat_date, 'player_id': p['player_id'], 'team_id': p['team_id'], 'stat_window': stat_window, 'games_sample': gs, 'games_with_hit': games_with_hit, 'hit_rate': round(games_with_hit/gs,4), 'avg_hits': round(totals['h']/gs,4), 'avg_plate_appearances': round(totals['pa']/gs,4), 'avg_at_bats': round(totals['ab']/gs,4), **m, 'contact_proxy': round(1 - (m.get('k_rate') or 0),4) if m.get('k_rate') is not None else None})
    return execute_many('''
        insert into prohits.player_derived_stats (stat_date,player_id,team_id,stat_window,games_sample,games_with_hit,hit_rate,avg_hits,avg_plate_appearances,avg_at_bats,avg,obp,slg,ops,iso,babip,strikeout_rate,bb_rate,contact_proxy,calculated_at)
        values (%(stat_date)s,%(player_id)s,%(team_id)s,%(stat_window)s,%(games_sample)s,%(games_with_hit)s,%(hit_rate)s,%(avg_hits)s,%(avg_plate_appearances)s,%(avg_at_bats)s,%(avg)s,%(obp)s,%(slg)s,%(ops)s,%(iso)s,%(babip)s,%(k_rate)s,%(bb_rate)s,%(contact_proxy)s,now())
        on conflict (stat_date,player_id,stat_window) do update set games_sample=excluded.games_sample,games_with_hit=excluded.games_with_hit,hit_rate=excluded.hit_rate,avg_hits=excluded.avg_hits,avg_plate_appearances=excluded.avg_plate_appearances,avg_at_bats=excluded.avg_at_bats,avg=excluded.avg,obp=excluded.obp,slg=excluded.slg,ops=excluded.ops,iso=excluded.iso,babip=excluded.babip,strikeout_rate=excluded.strikeout_rate,bb_rate=excluded.bb_rate,contact_proxy=excluded.contact_proxy,calculated_at=now()
    ''', rows)

