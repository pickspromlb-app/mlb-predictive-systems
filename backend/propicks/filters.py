from datetime import date
import json
from shared.db import fetch_all, execute_many

def evaluate_offensive_edge(evaluation_date: date, window: str = 'L5') -> int:
    profiles = fetch_all('select * from propicks.daily_team_profile where profile_date=%s and window=%s and metric_status=%s', (evaluation_date, window, 'OK_INTERNAL'))
    by_game = {}
    for p in profiles:
        by_game.setdefault(p['game_pk'], []).append(p)
    rows = []
    for game_pk, teams in by_game.items():
        if len(teams) != 2:
            continue
        rows.extend([_score(teams[0], teams[1], evaluation_date), _score(teams[1], teams[0], evaluation_date)])
    return execute_many('''
        insert into propicks.market_results (evaluation_date,game_pk,team_id,opponent_team_id,system_id,market_type,target_metric,projected_label,score,filters_passed,filters_failed,activation_status,data_quality_status,calculation_version)
        values (%(evaluation_date)s,%(game_pk)s,%(team_id)s,%(opponent_team_id)s,'PROPICKS_MLB','OFFENSIVE_EDGE','pre_game_offensive_edge',%(projected_label)s,%(score)s,%(filters_passed)s::jsonb,%(filters_failed)s::jsonb,%(activation_status)s,'OK_INTERNAL','offensive_edge_v1')
    ''', rows)

def _score(team, opp, evaluation_date):
    passed, failed = [], []
    def diff(a,b):
        return None if a is None or b is None else float(a)-float(b)
    checks = [
        ('wOBA diff >= .040 + wRC+ diff >= 30', (diff(team.get('woba_internal'), opp.get('woba_internal')) or 0) >= .040 and (diff(team.get('wrc_plus_internal'), opp.get('wrc_plus_internal')) or 0) >= 30),
        ('OPS diff >= .150 + wRC+ diff >= 30', (diff(team.get('ops'), opp.get('ops')) or 0) >= .150 and (diff(team.get('wrc_plus_internal'), opp.get('wrc_plus_internal')) or 0) >= 30),
        ('wRC+ diff >= 50 + wOBA diff >= .070', (diff(team.get('wrc_plus_internal'), opp.get('wrc_plus_internal')) or 0) >= 50 and (diff(team.get('woba_internal'), opp.get('woba_internal')) or 0) >= .070),
        ('scored 3+ rate L5 >= 70%', float(team.get('scored_3plus_rate') or 0) >= .70),
    ]
    for name, ok in checks:
        (passed if ok else failed).append(name)
    score = len(passed) * 25
    label = 'STRONG_OFFENSIVE_EDGE' if score >= 75 else 'MODERATE_OFFENSIVE_EDGE' if score >= 50 else 'NO_EDGE'
    status = 'PRELIMINARY' if score >= 50 else 'PASS'
    return {'evaluation_date': evaluation_date, 'game_pk': team['game_pk'], 'team_id': team['team_id'], 'opponent_team_id': team['opponent_team_id'], 'projected_label': label, 'score': score, 'filters_passed': json.dumps(passed), 'filters_failed': json.dumps(failed), 'activation_status': status}
