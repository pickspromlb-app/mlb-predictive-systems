from datetime import date
from fastapi import APIRouter, Query
from shared.db import fetch_all, fetch_one
from shared.time_utils import today_local

router = APIRouter()


@router.get('/profiles/today')
def profiles_today(
    profile_date: date | None = Query(default=None),
    stat_window: str = 'L5'
):
    d = profile_date or today_local()

    rows = fetch_all(
        '''
        select
          p.*,
          t.abbreviation as team,
          o.abbreviation as opponent
        from propicks.daily_team_profile p
        left join core.teams t
          on t.team_id = p.team_id
        left join core.teams o
          on o.team_id = p.opponent_team_id
        where p.profile_date = %s
          and p.stat_window = %s
        order by p.game_pk, p.home_away
        ''',
        (d, stat_window)
    )

    return {
        'date': d,
        'stat_window': stat_window,
        'count': len(rows),
        'rows': rows
    }


@router.get('/edges/today')
def edges_today(
    evaluation_date: date | None = Query(default=None)
):
    d = evaluation_date or today_local()

    rows = fetch_all(
        '''
        select
          r.*,
          t.abbreviation as team,
          o.abbreviation as opponent
        from propicks.market_results r
        left join core.teams t
          on t.team_id = r.team_id
        left join core.teams o
          on o.team_id = r.opponent_team_id
        where r.evaluation_date = %s
          and r.target_metric = 'pre_game_offensive_edge'
        order by r.score desc nulls last
        ''',
        (d,)
    )

    return {
        'date': d,
        'count': len(rows),
        'rows': rows
    }


@router.get('/team-runs/today')
def team_runs_today(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    rows = fetch_all(
        '''
        select
          s.id,
          s.analysis_date,
          s.game_pk,
          s.market_type,
          s.target_metric,
          s.score,
          s.confidence_tier,
          s.status,
          s.grade_status,
          s.actual_result,
          s.success,
          s.filters_passed,
          s.filters_failed,
          s.metrics_snapshot,
          s.risk_flags,
          s.analysis_text,
          s.created_at,
          s.graded_at,

          t.abbreviation as team,
          t.team_name as team_name,
          o.abbreviation as opponent,
          o.team_name as opponent_name,

          g.away_team_id,
          g.home_team_id,
          at.abbreviation as away_team,
          ht.abbreviation as home_team,

          gl.away_runs,
          gl.home_runs,
          gl.away_f5_runs,
          gl.home_f5_runs

        from propicks.analysis_snapshots s

        left join core.teams t
          on t.team_id = s.team_id

        left join core.teams o
          on o.team_id = s.opponent_team_id

        left join core.games g
          on g.game_pk = s.game_pk

        left join core.teams at
          on at.team_id = g.away_team_id

        left join core.teams ht
          on ht.team_id = g.home_team_id

        left join core.game_linescore gl
          on gl.game_pk = s.game_pk

        where s.analysis_date = %s
          and s.target_metric in ('team_3plus_runs', 'team_5plus_runs')

        order by
          s.game_pk,
          s.team_id,
          s.target_metric
        ''',
        (d,)
    )

    return {
        'date': d,
        'count': len(rows),
        'rows': rows
    }


@router.get('/postgame/summary')
def postgame_summary(
    summary_date: date | None = Query(default=None)
):
    d = summary_date or today_local()

    row = fetch_one(
        '''
        select
          *
        from ops.postgame_daily_summary
        where summary_date = %s
          and system_name = 'ProPicksMLB'
          and system_version = 'v1.0'
        ''',
        (d,)
    )

    return {
        'date': d,
        'summary': row
    }


@router.get('/postgame/summaries')
def postgame_summaries(
    limit: int = Query(default=30, ge=1, le=100)
):
    rows = fetch_all(
        '''
        select
          summary_date,
          system_name,
          system_version,
          total_records,
          wins,
          losses,
          pushes,
          success_rate,
          by_target_metric,
          by_confidence_tier,
          top_wins,
          top_losses,
          summary_text,
          created_at,
          updated_at
        from ops.postgame_daily_summary
        where system_name = 'ProPicksMLB'
        order by summary_date desc
        limit %s
        ''',
        (limit,)
    )

    return {
        'count': len(rows),
        'rows': rows
    }


@router.get('/performance')
def performance():
    rows = fetch_all(
        '''
        select
          system_name,
          system_version,
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          best_filters,
          worst_filters,
          common_failure_reasons,
          last_updated
        from ops.system_performance_summary
        where system_name = 'ProPicksMLB'
        order by
          case
            when target_metric = 'team_3plus_runs' then 1
            when target_metric = 'team_5plus_runs' then 2
            when target_metric = 'pre_game_offensive_edge' then 3
            else 99
          end,
          target_metric
        '''
    )

    return {
        'system': 'ProPicksMLB',
        'count': len(rows),
        'rows': rows
    }


@router.get('/audit/team-runs/global')
def team_runs_global_audit():
    rows = fetch_all(
        '''
        select
          target_metric,
          count(*) as sample_size,
          count(*) filter (where success = true) as wins,
          count(*) filter (where success = false) as losses,
          round(
            count(*) filter (where success = true)::numeric / nullif(count(*), 0),
            4
          ) as success_rate
        from propicks.analysis_snapshots
        where target_metric in ('team_3plus_runs', 'team_5plus_runs')
          and grade_status = 'GRADED'
        group by target_metric
        order by target_metric
        '''
    )

    total = fetch_one(
        '''
        select
          count(*) as sample_size,
          count(*) filter (where success = true) as wins,
          count(*) filter (where success = false) as losses,
          round(
            count(*) filter (where success = true)::numeric / nullif(count(*), 0),
            4
          ) as success_rate
        from propicks.analysis_snapshots
        where target_metric in ('team_3plus_runs', 'team_5plus_runs')
          and grade_status = 'GRADED'
        '''
    )

    return {
        'system': 'ProPicksMLB',
        'module': 'Team Runs Pressure Filter v1',
        'total': total,
        'by_target_metric': rows
    }

@router.get('/moneyline-core/signals')
def moneyline_core_signals(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    rows = fetch_all(
        '''
        select
          analysis_snapshot_id,
          analysis_date,
          game_pk,
          moneyline_tier,

          team_id,
          team_abbr,
          team_name,

          opponent_team_id,
          opponent_abbr,
          opponent_name,

          home_away,

          team_score,
          opponent_score,
          won_moneyline,

          log5_home_prob,
          whip_edge,
          ra_edge,
          era_edge,
          team_ra_l5,

          team_rs_l5,
          opp_rs_l5,
          team_whip_l5,
          opp_whip_l5,
          team_era_l5,
          opp_era_l5
        from propicks.moneyline_core_v1_signals
        where analysis_date = %s
        order by
          case when moneyline_tier = 'HOME_CORE' then 1 else 2 end,
          log5_home_prob desc
        ''',
        (d,)
    )

    backtest = fetch_all(
        '''
        select
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          last_updated
        from propicks.backtest_results
        where system_id = 'MONEYLINE_CORE_V1'
          and version = 'v1.0'
        order by target_metric
        '''
    )

    return {
        'system_id': 'MONEYLINE_CORE_V1',
        'version': 'v1.0',
        'analysis_date': d,
        'count': len(rows),
        'backtest': backtest,
        'rows': rows
    }

@router.get('/team-runs-core/signals')
def team_runs_core_signals(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    rows = fetch_all(
        '''
        select
          analysis_snapshot_id,
          analysis_date,
          game_pk,

          team_id,
          team_abbr,
          team_name,

          opponent_team_id,
          opponent_abbr,
          opponent_name,

          home_away,
          team_runs_tier,

          team_score,
          hit_3plus,
          hit_5plus,

          team_rs_l5,
          opp_ra_l5,
          opp_whip_l5,
          opp_era_l5
        from propicks.team_runs_core_v1_signals
        where analysis_date = %s
        order by
          case
            when team_runs_tier = 'POWER_5PLUS' then 1
            when team_runs_tier = 'CORE_3PLUS' then 2
            else 3
          end,
          team_rs_l5 desc,
          opp_era_l5 desc
        ''',
        (d,)
    )

    backtest = fetch_all(
        '''
        select
          system_id,
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          last_updated
        from propicks.backtest_results
        where system_id in ('TEAM_RUNS_CORE_V1', 'TEAM_RUNS_POWER_V1')
          and version = 'v1.0'
        order by system_id, target_metric
        '''
    )

    return {
        'systems': ['TEAM_RUNS_CORE_V1', 'TEAM_RUNS_POWER_V1'],
        'version': 'v1.0',
        'analysis_date': d,
        'count': len(rows),
        'backtest': backtest,
        'rows': rows
    }

@router.get('/totals-over-core/signals')
def totals_over_core_signals(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    rows = fetch_all(
        '''
        select
          first_analysis_snapshot_id,
          analysis_date,
          game_pk,

          away_team_id,
          away_team_abbr,
          away_team_name,

          home_team_id,
          home_team_abbr,
          home_team_name,

          totals_over_tier,

          away_score,
          home_score,
          total_runs,
          status,
          detailed_state,
          is_final,

          hit_8plus,
          hit_9plus,
          hit_10plus,

          combined_rs_l5,
          combined_ra_l5,
          combined_whip_l5,
          combined_era_l5,
          combined_fip_l5
        from propicks.totals_over_core_v1_signals
        where analysis_date = %s
        order by
          combined_era_l5 desc,
          combined_whip_l5 desc
        ''',
        (d,)
    )

    backtest = fetch_all(
        '''
        select
          system_id,
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          last_updated
        from propicks.backtest_results
        where system_id = 'TOTALS_OVER_CORE_V1'
          and version = 'v1.0'
        order by target_metric
        '''
    )

    return {
        'system_id': 'TOTALS_OVER_CORE_V1',
        'version': 'v1.0',
        'analysis_date': d,
        'count': len(rows),
        'backtest': backtest,
        'rows': rows
    }

@router.get('/totals-under-core/signals')
def totals_under_core_signals(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    rows = fetch_all(
        '''
        select
          first_analysis_snapshot_id,
          analysis_date,
          game_pk,

          away_team_id,
          away_team_abbr,
          away_team_name,

          home_team_id,
          home_team_abbr,
          home_team_name,

          totals_under_tier,

          away_score,
          home_score,
          total_runs,
          status,
          detailed_state,
          is_final,

          hit_under8,
          hit_under7,
          hit_under6,

          combined_rs_l5,
          combined_ra_l5,
          combined_whip_l5,
          combined_era_l5,
          combined_fip_l5
        from propicks.totals_under_core_v1_signals
        where analysis_date = %s
        order by
          case
            when totals_under_tier = 'UNDER_ELITE' then 1
            when totals_under_tier = 'UNDER_CORE' then 2
            else 3
          end,
          combined_ra_l5 asc,
          combined_whip_l5 asc
        ''',
        (d,)
    )

    backtest = fetch_all(
        '''
        select
          system_id,
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          last_updated
        from propicks.backtest_results
        where system_id in ('TOTALS_UNDER_CORE_V1', 'TOTALS_UNDER_ELITE_V1')
          and version = 'v1.0'
        order by system_id, target_metric
        '''
    )

    return {
        'systems': ['TOTALS_UNDER_CORE_V1', 'TOTALS_UNDER_ELITE_V1'],
        'version': 'v1.0',
        'analysis_date': d,
        'count': len(rows),
        'backtest': backtest,
        'rows': rows
    }

@router.get('/signals/today')
def propicks_signals_today(
    analysis_date: date | None = Query(default=None)
):
    d = analysis_date or today_local()

    moneyline_rows = fetch_all(
        '''
        select *
        from propicks.moneyline_core_v1_signals
        where analysis_date = %s
        order by
          case
            when moneyline_tier = 'HOME_CORE' then 1
            when moneyline_tier = 'AWAY_CORE' then 2
            else 3
          end,
          team_abbr
        ''',
        (d,)
    )

    team_runs_rows = fetch_all(
        '''
        select *
        from propicks.team_runs_core_v1_signals
        where analysis_date = %s
        order by
          case
            when team_runs_tier = 'POWER_5PLUS' then 1
            when team_runs_tier = 'CORE_3PLUS' then 2
            else 3
          end,
          team_rs_l5 desc,
          opp_era_l5 desc
        ''',
        (d,)
    )

    totals_over_rows = fetch_all(
        '''
        select *
        from propicks.totals_over_core_v1_signals
        where analysis_date = %s
        order by
          combined_era_l5 desc,
          combined_whip_l5 desc
        ''',
        (d,)
    )

    totals_under_rows = fetch_all(
        '''
        select *
        from propicks.totals_under_core_v1_signals
        where analysis_date = %s
        order by
          case
            when totals_under_tier = 'UNDER_ELITE' then 1
            when totals_under_tier = 'UNDER_CORE' then 2
            else 3
          end,
          combined_ra_l5 asc,
          combined_whip_l5 asc
        ''',
        (d,)
    )

    backtest = fetch_all(
        '''
        select
          system_id,
          version,
          target_metric,
          sample_size,
          wins,
          losses,
          pushes,
          success_rate,
          last_updated
        from propicks.backtest_results
        where version = 'v1.0'
          and system_id in (
            'MONEYLINE_CORE_V1',
            'TEAM_RUNS_CORE_V1',
            'TEAM_RUNS_POWER_V1',
            'TOTALS_OVER_CORE_V1',
            'TOTALS_UNDER_CORE_V1',
            'TOTALS_UNDER_ELITE_V1'
          )
        order by system_id, target_metric
        '''
    )

    return {
        'system': 'ProPicksMLB',
        'version': 'v1.0',
        'analysis_date': d,
        'counts': {
            'moneyline': len(moneyline_rows),
            'team_runs': len(team_runs_rows),
            'totals_over': len(totals_over_rows),
            'totals_under': len(totals_under_rows),
        },
        'signals': {
            'moneyline': moneyline_rows,
            'team_runs': team_runs_rows,
            'totals_over': totals_over_rows,
            'totals_under': totals_under_rows,
        },
        'backtest': backtest
    }
