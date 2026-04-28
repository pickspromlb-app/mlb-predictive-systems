from datetime import date
import os
import subprocess
import sys

from fastapi import APIRouter, Header, HTTPException, Query

from shared.db import fetch_one, fetch_all

router = APIRouter()


@router.post('/team-runs/save-analysis')
def save_team_runs_analysis(
    analysis_date: date = Query(...),
    x_internal_token: str | None = Header(default=None),
):
    expected_token = os.getenv('API_INTERNAL_TOKEN', 'change_me')

    if x_internal_token != expected_token:
        raise HTTPException(status_code=401, detail='Invalid internal token')

    d = analysis_date.isoformat()

    subprocess.run(
        [sys.executable, "-m", "propicks.create_analysis_snapshots"],
        check=True,
    )

    subprocess.run(
        [sys.executable, "-m", "propicks.create_team_runs_snapshots", d],
        check=True,
    )

    counts = fetch_one(
        """
        select
          count(*) filter (
            where target_metric = 'pre_game_offensive_edge'
          )::int as offensive_snapshots,

          count(*) filter (
            where target_metric = 'team_3plus_runs'
          )::int as team_3plus_snapshots,

          count(*) filter (
            where target_metric = 'team_5plus_runs'
          )::int as team_5plus_snapshots

        from propicks.analysis_snapshots
        where analysis_date = %s::date
          and target_metric in (
            'pre_game_offensive_edge',
            'team_3plus_runs',
            'team_5plus_runs'
          )
        """,
        (d,),
    )

    return {
        "status": "saved",
        "analysis_date": d,
        "offensive_snapshots": counts["offensive_snapshots"],
        "team_3plus_snapshots": counts["team_3plus_snapshots"],
        "team_5plus_snapshots": counts["team_5plus_snapshots"],
    }


@router.post('/run-daily')
def run_daily_propicks(
    analysis_date: date = Query(...),
    x_internal_token: str | None = Header(default=None),
):
    expected_token = os.getenv('API_INTERNAL_TOKEN', 'change_me')

    if x_internal_token != expected_token:
        raise HTTPException(status_code=401, detail='Invalid internal token')

    d = analysis_date.isoformat()

    commands = [
        [sys.executable, "-m", "jobs.run_date", d],
        [sys.executable, "-m", "propicks.build_team_pitching_profiles"],
        [sys.executable, "-m", "propicks.create_analysis_snapshots"],
        [sys.executable, "-m", "propicks.create_team_runs_snapshots", d],
    ]

    command_logs = []

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            command_logs.append({
                "command": " ".join(cmd),
                "status": "ok",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            })
        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "failed",
                    "analysis_date": d,
                    "command": " ".join(cmd),
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                },
            )

    counts = fetch_one(
        """
        select
          (
            select count(*)::int
            from core.games
            where game_date = %s::date
          ) as games,

          (
            select count(*)::int
            from propicks.daily_team_profile
            where profile_date = %s::date
          ) as team_profiles,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'pre_game_offensive_edge'
          ) as offensive_snapshots,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'team_3plus_runs'
          ) as team_3plus_snapshots,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'team_5plus_runs'
          ) as team_5plus_snapshots,

          (
            select count(*)::int
            from propicks.moneyline_core_v1_signals
            where analysis_date = %s::date
          ) as moneyline_signals,

          (
            select count(*)::int
            from propicks.team_runs_core_v1_signals
            where analysis_date = %s::date
          ) as team_runs_signals,

          (
            select count(*)::int
            from propicks.totals_over_core_v1_signals
            where analysis_date = %s::date
          ) as totals_over_signals,

          (
            select count(*)::int
            from propicks.totals_under_core_v1_signals
            where analysis_date = %s::date
          ) as totals_under_signals
        """,
        (d, d, d, d, d, d, d, d, d),
    )

    return {
        "status": "completed",
        "analysis_date": d,
        "counts": counts,
        "commands": command_logs,
    }


@router.post('/save-daily-analysis')
def save_daily_analysis(
    analysis_date: date = Query(...),
    x_internal_token: str | None = Header(default=None),
):
    expected_token = os.getenv('API_INTERNAL_TOKEN', 'change_me')

    if x_internal_token != expected_token:
        raise HTTPException(status_code=401, detail='Invalid internal token')

    d = analysis_date.isoformat()

    moneyline_saved = fetch_one(
        """
        with src as (
          select *
          from propicks.moneyline_core_v1_signals
          where analysis_date = %s::date
        ),
        upserted as (
          insert into propicks.saved_daily_signals (
            analysis_date,
            market_group,
            signal_type,
            system_id,
            version,
            game_pk,
            team_id,
            team_id_key,
            team_abbr,
            team_name,
            opponent_team_id,
            opponent_abbr,
            opponent_name,
            tier,
            display_label,
            primary_target,
            secondary_target,
            is_final,
            result_status,
            score_for,
            score_against,
            hit_primary,
            hit_secondary,
            metrics,
            raw_signal,
            updated_at
          )
          select
            s.analysis_date,
            'MONEYLINE',
            'MONEYLINE',
            'MONEYLINE_CORE_V1',
            'v1.0',
            s.game_pk,
            s.team_id,
            coalesce(s.team_id, 0),
            s.team_abbr,
            s.team_name,
            s.opponent_team_id,
            s.opponent_abbr,
            s.opponent_name,
            s.moneyline_tier,
            s.team_abbr || ' Moneyline',
            'Moneyline',
            null,
            case
              when s.team_score is not null and s.opponent_score is not null then true
              else false
            end,
            case
              when s.won_moneyline is true then 'WIN'
              when s.won_moneyline is false then 'LOSS'
              else 'PENDING'
            end,
            s.team_score,
            s.opponent_score,
            s.won_moneyline,
            null,
            jsonb_build_object(
              'log5_home_prob', s.log5_home_prob,
              'whip_edge', s.whip_edge,
              'ra_edge', s.ra_edge,
              'era_edge', s.era_edge,
              'team_ra_l5', s.team_ra_l5,
              'team_rs_l5', s.team_rs_l5,
              'opp_rs_l5', s.opp_rs_l5,
              'team_whip_l5', s.team_whip_l5,
              'opp_whip_l5', s.opp_whip_l5,
              'team_era_l5', s.team_era_l5,
              'opp_era_l5', s.opp_era_l5
            ),
            to_jsonb(s),
            now()
          from src s
          on conflict (analysis_date, signal_type, game_pk, team_id_key, tier)
          do update set
            display_label = excluded.display_label,
            primary_target = excluded.primary_target,
            secondary_target = excluded.secondary_target,
            is_final = excluded.is_final,
            result_status = excluded.result_status,
            score_for = excluded.score_for,
            score_against = excluded.score_against,
            hit_primary = excluded.hit_primary,
            hit_secondary = excluded.hit_secondary,
            metrics = excluded.metrics,
            raw_signal = excluded.raw_signal,
            updated_at = now()
          returning 1
        )
        select count(*)::int as saved
        from upserted
        """,
        (d,),
    )

    team_runs_saved = fetch_one(
        """
        with src as (
          select *
          from propicks.team_runs_core_v1_signals
          where analysis_date = %s::date
        ),
        normalized as (
          select
            s.*,
            case
              when s.team_runs_tier = 'POWER_5PLUS' then 'TEAM_RUNS_POWER_V1'
              else 'TEAM_RUNS_CORE_V1'
            end as normalized_system_id,

            case
              when s.team_runs_tier = 'POWER_5PLUS' then s.team_abbr || ' mas de 5 carreras'
              else s.team_abbr || ' mas de 3 carreras'
            end as normalized_display_label,

            case
              when s.team_runs_tier = 'POWER_5PLUS' then '5+ carreras del equipo'
              else '3+ carreras del equipo'
            end as normalized_primary_target,

            case
              when s.team_runs_tier = 'POWER_5PLUS' then '3+ carreras del equipo'
              else null
            end as normalized_secondary_target,

            case
              when s.team_runs_tier = 'POWER_5PLUS' then s.hit_5plus
              else s.hit_3plus
            end as normalized_hit_primary,

            case
              when s.team_runs_tier = 'POWER_5PLUS' then s.hit_3plus
              else null
            end as normalized_hit_secondary
          from src s
        ),
        upserted as (
          insert into propicks.saved_daily_signals (
            analysis_date,
            market_group,
            signal_type,
            system_id,
            version,
            game_pk,
            team_id,
            team_id_key,
            team_abbr,
            team_name,
            opponent_team_id,
            opponent_abbr,
            opponent_name,
            tier,
            display_label,
            primary_target,
            secondary_target,
            is_final,
            result_status,
            score_for,
            score_against,
            hit_primary,
            hit_secondary,
            metrics,
            raw_signal,
            updated_at
          )
          select
            s.analysis_date,
            'TEAM_RUNS',
            'TEAM_RUNS',
            s.normalized_system_id,
            'v1.0',
            s.game_pk,
            s.team_id,
            coalesce(s.team_id, 0),
            s.team_abbr,
            s.team_name,
            s.opponent_team_id,
            s.opponent_abbr,
            s.opponent_name,
            s.team_runs_tier,
            s.normalized_display_label,
            s.normalized_primary_target,
            s.normalized_secondary_target,
            case
              when s.team_score is not null then true
              else false
            end,
            case
              when s.normalized_hit_primary is true then 'WIN'
              when s.normalized_hit_primary is false then 'LOSS'
              else 'PENDING'
            end,
            s.team_score,
            null,
            s.normalized_hit_primary,
            s.normalized_hit_secondary,
            jsonb_build_object(
              'team_rs_l5', s.team_rs_l5,
              'opp_ra_l5', s.opp_ra_l5,
              'opp_whip_l5', s.opp_whip_l5,
              'opp_era_l5', s.opp_era_l5,
              'hit_3plus', s.hit_3plus,
              'hit_5plus', s.hit_5plus
            ),
            to_jsonb(s),
            now()
          from normalized s
          on conflict (analysis_date, signal_type, game_pk, team_id_key, tier)
          do update set
            system_id = excluded.system_id,
            display_label = excluded.display_label,
            primary_target = excluded.primary_target,
            secondary_target = excluded.secondary_target,
            is_final = excluded.is_final,
            result_status = excluded.result_status,
            score_for = excluded.score_for,
            score_against = excluded.score_against,
            hit_primary = excluded.hit_primary,
            hit_secondary = excluded.hit_secondary,
            metrics = excluded.metrics,
            raw_signal = excluded.raw_signal,
            updated_at = now()
          returning 1
        )
        select count(*)::int as saved
        from upserted
        """,
        (d,),
    )

    totals_over_saved = fetch_one(
        """
        with src as (
          select *
          from propicks.totals_over_core_v1_signals
          where analysis_date = %s::date
        ),
        upserted as (
          insert into propicks.saved_daily_signals (
            analysis_date,
            market_group,
            signal_type,
            system_id,
            version,
            game_pk,
            team_id,
            team_id_key,
            away_team_id,
            away_team_abbr,
            away_team_name,
            home_team_id,
            home_team_abbr,
            home_team_name,
            tier,
            display_label,
            primary_target,
            secondary_target,
            is_final,
            result_status,
            away_score,
            home_score,
            total_runs,
            hit_primary,
            hit_secondary,
            metrics,
            raw_signal,
            updated_at
          )
          select
            s.analysis_date,
            'TOTALS',
            'TOTALS_OVER',
            'TOTALS_OVER_CORE_V1',
            'v1.0',
            s.game_pk,
            null,
            0,
            s.away_team_id,
            s.away_team_abbr,
            s.away_team_name,
            s.home_team_id,
            s.home_team_abbr,
            s.home_team_name,
            s.totals_over_tier,
            s.away_team_abbr || ' @ ' || s.home_team_abbr || ' mas de 9 carreras',
            '9+ carreras del juego',
            '10+ carreras del juego',
            coalesce(s.is_final, false),
            case
              when s.hit_9plus is true then 'WIN'
              when s.hit_9plus is false then 'LOSS'
              else 'PENDING'
            end,
            s.away_score,
            s.home_score,
            s.total_runs,
            s.hit_9plus,
            s.hit_10plus,
            jsonb_build_object(
              'combined_rs_l5', s.combined_rs_l5,
              'combined_ra_l5', s.combined_ra_l5,
              'combined_whip_l5', s.combined_whip_l5,
              'combined_era_l5', s.combined_era_l5,
              'combined_fip_l5', s.combined_fip_l5,
              'hit_8plus', s.hit_8plus,
              'hit_9plus', s.hit_9plus,
              'hit_10plus', s.hit_10plus
            ),
            to_jsonb(s),
            now()
          from src s
          on conflict (analysis_date, signal_type, game_pk, team_id_key, tier)
          do update set
            display_label = excluded.display_label,
            primary_target = excluded.primary_target,
            secondary_target = excluded.secondary_target,
            is_final = excluded.is_final,
            result_status = excluded.result_status,
            away_score = excluded.away_score,
            home_score = excluded.home_score,
            total_runs = excluded.total_runs,
            hit_primary = excluded.hit_primary,
            hit_secondary = excluded.hit_secondary,
            metrics = excluded.metrics,
            raw_signal = excluded.raw_signal,
            updated_at = now()
          returning 1
        )
        select count(*)::int as saved
        from upserted
        """,
        (d,),
    )

    totals_under_saved = fetch_one(
        """
        with src as (
          select *
          from propicks.totals_under_core_v1_signals
          where analysis_date = %s::date
        ),
        normalized as (
          select
            s.*,
            case
              when s.totals_under_tier = 'UNDER_ELITE' then 'TOTALS_UNDER_ELITE_V1'
              else 'TOTALS_UNDER_CORE_V1'
            end as normalized_system_id,

            case
              when s.totals_under_tier = 'UNDER_ELITE'
                then s.away_team_abbr || ' @ ' || s.home_team_abbr || ' menos de 7/8 carreras'
              else s.away_team_abbr || ' @ ' || s.home_team_abbr || ' menos de 8 carreras'
            end as normalized_display_label,

            case
              when s.totals_under_tier = 'UNDER_ELITE' then 'Under 8'
              else 'Under 8'
            end as normalized_primary_target,

            case
              when s.totals_under_tier = 'UNDER_ELITE' then 'Under 7'
              else null
            end as normalized_secondary_target,

            s.hit_under8 as normalized_hit_primary,

            case
              when s.totals_under_tier = 'UNDER_ELITE' then s.hit_under7
              else null
            end as normalized_hit_secondary
          from src s
        ),
        upserted as (
          insert into propicks.saved_daily_signals (
            analysis_date,
            market_group,
            signal_type,
            system_id,
            version,
            game_pk,
            team_id,
            team_id_key,
            away_team_id,
            away_team_abbr,
            away_team_name,
            home_team_id,
            home_team_abbr,
            home_team_name,
            tier,
            display_label,
            primary_target,
            secondary_target,
            is_final,
            result_status,
            away_score,
            home_score,
            total_runs,
            hit_primary,
            hit_secondary,
            metrics,
            raw_signal,
            updated_at
          )
          select
            s.analysis_date,
            'TOTALS',
            'TOTALS_UNDER',
            s.normalized_system_id,
            'v1.0',
            s.game_pk,
            null,
            0,
            s.away_team_id,
            s.away_team_abbr,
            s.away_team_name,
            s.home_team_id,
            s.home_team_abbr,
            s.home_team_name,
            s.totals_under_tier,
            s.normalized_display_label,
            s.normalized_primary_target,
            s.normalized_secondary_target,
            coalesce(s.is_final, false),
            case
              when s.normalized_hit_primary is true then 'WIN'
              when s.normalized_hit_primary is false then 'LOSS'
              else 'PENDING'
            end,
            s.away_score,
            s.home_score,
            s.total_runs,
            s.normalized_hit_primary,
            s.normalized_hit_secondary,
            jsonb_build_object(
              'combined_rs_l5', s.combined_rs_l5,
              'combined_ra_l5', s.combined_ra_l5,
              'combined_whip_l5', s.combined_whip_l5,
              'combined_era_l5', s.combined_era_l5,
              'combined_fip_l5', s.combined_fip_l5,
              'hit_under8', s.hit_under8,
              'hit_under7', s.hit_under7,
              'hit_under6', s.hit_under6
            ),
            to_jsonb(s),
            now()
          from normalized s
          on conflict (analysis_date, signal_type, game_pk, team_id_key, tier)
          do update set
            system_id = excluded.system_id,
            display_label = excluded.display_label,
            primary_target = excluded.primary_target,
            secondary_target = excluded.secondary_target,
            is_final = excluded.is_final,
            result_status = excluded.result_status,
            away_score = excluded.away_score,
            home_score = excluded.home_score,
            total_runs = excluded.total_runs,
            hit_primary = excluded.hit_primary,
            hit_secondary = excluded.hit_secondary,
            metrics = excluded.metrics,
            raw_signal = excluded.raw_signal,
            updated_at = now()
          returning 1
        )
        select count(*)::int as saved
        from upserted
        """,
        (d,),
    )

    status_normalized = fetch_one(
        """
        with game_state as (
          select
            game_pk,
            (
              lower(coalesce(status, '')) in ('final', 'game over', 'completed')
              or lower(coalesce(detailed_state, '')) in ('final', 'game over', 'completed')
              or lower(coalesce(detailed_state, '')) like 'final%%'
            ) as game_is_final
          from core.games
          where game_date = %s::date
        ),
        updated as (
          update propicks.saved_daily_signals s
          set
            is_final = coalesce(g.game_is_final, false),
            result_status = case
              when coalesce(g.game_is_final, false) = false then 'PENDING'
              when s.hit_primary is true then 'WIN'
              when s.hit_primary is false then 'LOSS'
              else 'PENDING'
            end,
            updated_at = now()
          from game_state g
          where s.analysis_date = %s::date
            and s.game_pk = g.game_pk
          returning 1
        )
        select count(*)::int as normalized
        from updated
        """,
        (d, d),
    )
    counts = fetch_one(
        """
        select
          count(*)::int as total_saved,
          count(*) filter (where signal_type = 'MONEYLINE')::int as moneyline_saved,
          count(*) filter (where signal_type = 'TEAM_RUNS')::int as team_runs_saved,
          count(*) filter (where signal_type = 'TOTALS_OVER')::int as totals_over_saved,
          count(*) filter (where signal_type = 'TOTALS_UNDER')::int as totals_under_saved,
          count(*) filter (where result_status = 'PENDING')::int as pending,
          count(*) filter (where result_status = 'WIN')::int as wins,
          count(*) filter (where result_status = 'LOSS')::int as losses
        from propicks.saved_daily_signals
        where analysis_date = %s::date
        """,
        (d,),
    )

    return {
        "status": "saved",
        "analysis_date": d,
        "saved_now": {
            "moneyline": moneyline_saved["saved"],
            "team_runs": team_runs_saved["saved"],
            "totals_over": totals_over_saved["saved"],
            "totals_under": totals_under_saved["saved"],
        },
        "counts": counts,
    }



@router.get('/saved-signals')
def get_saved_signals(
    analysis_date: date = Query(...),
):
    d = analysis_date.isoformat()

    counts = fetch_one(
        """
        select
          count(*)::int as total_saved,
          count(*) filter (where signal_type = 'MONEYLINE')::int as moneyline_saved,
          count(*) filter (where signal_type = 'TEAM_RUNS')::int as team_runs_saved,
          count(*) filter (where signal_type = 'TOTALS_OVER')::int as totals_over_saved,
          count(*) filter (where signal_type = 'TOTALS_UNDER')::int as totals_under_saved,
          count(*) filter (where result_status = 'PENDING')::int as pending,
          count(*) filter (where result_status = 'WIN')::int as wins,
          count(*) filter (where result_status = 'LOSS')::int as losses,
          case
            when count(*) filter (where result_status in ('WIN', 'LOSS')) = 0 then null
            else round(
              (
                count(*) filter (where result_status = 'WIN')::numeric
                / nullif(count(*) filter (where result_status in ('WIN', 'LOSS')), 0)
              ) * 100,
              2
            )
          end as success_rate
        from propicks.saved_daily_signals
        where analysis_date = %s::date
        """,
        (d,),
    )

    by_market = fetch_all(
        """
        select
          market_group,
          signal_type,
          count(*)::int as total,
          count(*) filter (where result_status = 'PENDING')::int as pending,
          count(*) filter (where result_status = 'WIN')::int as wins,
          count(*) filter (where result_status = 'LOSS')::int as losses,
          case
            when count(*) filter (where result_status in ('WIN', 'LOSS')) = 0 then null
            else round(
              (
                count(*) filter (where result_status = 'WIN')::numeric
                / nullif(count(*) filter (where result_status in ('WIN', 'LOSS')), 0)
              ) * 100,
              2
            )
          end as success_rate
        from propicks.saved_daily_signals
        where analysis_date = %s::date
        group by market_group, signal_type
        order by market_group, signal_type
        """,
        (d,),
    )

    by_system = fetch_all(
        """
        select
          system_id,
          signal_type,
          count(*)::int as total,
          count(*) filter (where result_status = 'PENDING')::int as pending,
          count(*) filter (where result_status = 'WIN')::int as wins,
          count(*) filter (where result_status = 'LOSS')::int as losses,
          case
            when count(*) filter (where result_status in ('WIN', 'LOSS')) = 0 then null
            else round(
              (
                count(*) filter (where result_status = 'WIN')::numeric
                / nullif(count(*) filter (where result_status in ('WIN', 'LOSS')), 0)
              ) * 100,
              2
            )
          end as success_rate
        from propicks.saved_daily_signals
        where analysis_date = %s::date
        group by system_id, signal_type
        order by system_id, signal_type
        """,
        (d,),
    )

    rows = fetch_all(
        """
        select
          id,
          analysis_date,
          market_group,
          signal_type,
          system_id,
          version,
          game_pk,

          team_id,
          team_abbr,
          team_name,
          opponent_team_id,
          opponent_abbr,
          opponent_name,

          away_team_id,
          away_team_abbr,
          away_team_name,
          home_team_id,
          home_team_abbr,
          home_team_name,

          tier,
          display_label,
          primary_target,
          secondary_target,

          is_final,
          result_status,

          score_for,
          score_against,
          away_score,
          home_score,
          total_runs,

          hit_primary,
          hit_secondary,

          metrics,
          saved_at,
          updated_at
        from propicks.saved_daily_signals
        where analysis_date = %s::date
        order by
          case signal_type
            when 'MONEYLINE' then 1
            when 'TEAM_RUNS' then 2
            when 'TOTALS_OVER' then 3
            when 'TOTALS_UNDER' then 4
            else 5
          end,
          display_label
        """,
        (d,),
    )

    return {
        "system": "ProPicksMLB",
        "version": "v1.0",
        "analysis_date": d,
        "counts": counts,
        "by_market": by_market,
        "by_system": by_system,
        "rows": rows,
    }


