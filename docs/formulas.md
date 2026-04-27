# Fórmulas internas v1

AVG = H / AB
OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
SLG = TB / AB
OPS = OBP + SLG
ISO = SLG - AVG
BABIP = (H - HR) / (AB - K - HR + SF)
BB% = BB / PA
K% = SO / PA
wOBA interno = pesos de evento ajustables
wRAA = ((wOBA - league_wOBA) / wOBA_scale) * PA
wRC+ interno = ((wRC / PA) / league_runs_per_pa) * 100
WHIP = (BB + H) / IP
FIP = ((13*HR) + (3*(BB+HBP)) - (2*K)) / IP + FIP_constant
