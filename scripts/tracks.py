"""Single registry for forward tracks; historical references remain R1/R5 only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = {
    'r1': {'name': 'Çekirdek', 'description': '3 coin · 3 pozisyon', 'slots': 3, 'strategy': 'R1_TSMomentum'},
    'r5': {'name': '33 coin', 'description': '33 coin · 5 pozisyon', 'slots': 5, 'strategy': 'R5_TSMomentum'},
    'r6': {'name': 'Büyük coinler', 'description': 'Piyasa değeri ilk 10 · 5 pozisyon', 'slots': 5, 'strategy': 'R5_TSMomentum'},
    'r7': {'stress_fee': 0.0025, 'name': 'Geniş evren', 'description': '30 günlük hacim ilk 70 · 5 pozisyon', 'slots': 5, 'strategy': 'R5_TSMomentum'},
    'r8': {'stress_fee': 0.0025, 'name': 'Geniş + çok pozisyon', 'description': 'R7 evreni · 10 pozisyon', 'slots': 10, 'strategy': 'R5_TSMomentum'},
}
REFERENCE_TRACKS = ('r1', 'r5')


def configs(root=ROOT):
    result = {t: json.loads((root / f'user_data/config_{t}.json').read_text()) for t in TRACKS}
    for t, config in result.items():
        if not config['exchange']['pair_whitelist']:
            raise ValueError(f'{t}: universe snapshot pending; refusing forward run')
    return result


def all_pairs(configurations):
    return list(dict.fromkeys(p for c in configurations.values() for p in c['exchange']['pair_whitelist']))
