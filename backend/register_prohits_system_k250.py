from shared.db import execute_many, fetch_all

SYSTEM_ID = "PROHITS_CANDIDATE_A_SEP_L1_GUARD_BP_K250"

execute_many("""
    insert into prohits.systems
    (
        system_id,
        system_name,
        market_group,
        description,
        version,
        active,
        updated_at
    )
    values
    (
        %(system_id)s,
        %(system_name)s,
        %(market_group)s,
        %(description)s,
        %(version)s,
        %(active)s,
        now()
    )
    on conflict (system_id)
    do update set
        system_name = excluded.system_name,
        market_group = excluded.market_group,
        description = excluded.description,
        version = excluded.version,
        active = excluded.active,
        updated_at = now()
""", [{
    "system_id": SYSTEM_ID,
    "system_name": "ProHits Candidate A + Sep L1 Guard + Bullpen K250",
    "market_group": "Player Hits",
    "description": "Candidato operativo para Over 0.5 Hits: hitter volume/contact + opposing starter L5 + September L1 guard + bullpen K-rate <= .250 + market availability filter.",
    "version": "v0.1",
    "active": True,
}])

rows = fetch_all("""
    select system_id, system_name, version, active
    from prohits.systems
    where system_id = %s
""", [SYSTEM_ID])

print("=" * 90)
print("REGISTERED PROHITS SYSTEM")
print("=" * 90)

for r in rows:
    print(dict(r))
