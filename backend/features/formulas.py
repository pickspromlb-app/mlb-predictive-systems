from dataclasses import dataclass

def safe_div(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num) / float(den)

def r4(x):
    return None if x is None else round(float(x), 4)

@dataclass(frozen=True)
class WobaWeights:
    # Iniciales. En fase 2 se cargan desde FanGraphs Guts o constantes internas de liga.
    wbb: float = 0.690
    whbp: float = 0.720
    w1b: float = 0.880
    w2b: float = 1.247
    w3b: float = 1.578
    whr: float = 2.031
    scale: float = 1.250
    league_woba: float = 0.315
    league_runs_per_pa: float = 0.115

@dataclass(frozen=True)
class FipConstants:
    fip_constant: float = 3.10

def batting_metrics(row: dict, weights: WobaWeights | None = None) -> dict:
    weights = weights or WobaWeights()
    ab = int(row.get('ab') or 0)
    h = int(row.get('h') or 0)
    doubles = int(row.get('doubles') or 0)
    triples = int(row.get('triples') or 0)
    hr = int(row.get('hr') or 0)
    bb = int(row.get('bb') or 0)
    ibb = int(row.get('ibb') or 0)
    hbp = int(row.get('hbp') or 0)
    sf = int(row.get('sf') or 0)
    so = int(row.get('so') or 0)
    tb = int(row.get('tb') or (h + doubles + 2 * triples + 3 * hr))
    pa = int(row.get('pa') or (ab + bb + hbp + sf))
    singles = max(h - doubles - triples - hr, 0)

    avg = safe_div(h, ab)
    obp = safe_div(h + bb + hbp, ab + bb + hbp + sf)
    slg = safe_div(tb, ab)
    ops = None if obp is None or slg is None else obp + slg
    iso = None if slg is None or avg is None else slg - avg
    babip = safe_div(h - hr, ab - so - hr + sf)
    bb_rate = safe_div(bb, pa)
    k_rate = safe_div(so, pa)
    bb_k_ratio = safe_div(bb, so)

    woba_num = (weights.wbb * max(bb - ibb, 0) + weights.whbp * hbp + weights.w1b * singles + weights.w2b * doubles + weights.w3b * triples + weights.whr * hr)
    woba_den = ab + bb - ibb + sf + hbp
    woba = safe_div(woba_num, woba_den)

    wraa = wrc = wrc_plus = None
    if woba is not None and pa > 0:
        wraa = ((woba - weights.league_woba) / weights.scale) * pa
        wrc = wraa + weights.league_runs_per_pa * pa
        wrc_plus = ((wrc / pa) / weights.league_runs_per_pa) * 100

    return {
        'avg': r4(avg), 'obp': r4(obp), 'slg': r4(slg), 'ops': r4(ops), 'iso': r4(iso), 'babip': r4(babip),
        'bb_rate': r4(bb_rate), 'k_rate': r4(k_rate), 'bb_k_ratio': r4(bb_k_ratio),
        'woba_internal': r4(woba), 'wraa_internal': r4(wraa), 'wrc_internal': r4(wrc), 'wrc_plus_internal': r4(wrc_plus),
    }

def pitching_metrics(row: dict, c: FipConstants | None = None) -> dict:
    c = c or FipConstants()
    outs = int(row.get('ip_outs') or 0)
    ip = outs / 3 if outs else 0
    h = int(row.get('h') or 0)
    er = int(row.get('er') or 0)
    bb = int(row.get('bb') or 0)
    hbp = int(row.get('hbp') or 0)
    so = int(row.get('so') or 0)
    hr = int(row.get('hr') or 0)
    bf = int(row.get('bf') or 0)
    era = safe_div(er * 9, ip)
    whip = safe_div(bb + h, ip)
    fip = None if ip == 0 else (((13 * hr) + (3 * (bb + hbp)) - (2 * so)) / ip) + c.fip_constant
    k_rate = safe_div(so, bf)
    bb_rate = safe_div(bb, bf)
    return {'era': r4(era), 'whip': r4(whip), 'fip_internal': r4(fip), 'k_rate': r4(k_rate), 'bb_rate': r4(bb_rate), 'k_bb_rate': r4(None if k_rate is None or bb_rate is None else k_rate - bb_rate), 'k_per_9': r4(safe_div(so*9, ip)), 'bb_per_9': r4(safe_div(bb*9, ip)), 'hr_per_9': r4(safe_div(hr*9, ip)), 'sample_size_ip': r4(ip)}

