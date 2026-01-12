import math
from datetime import datetime, timezone
from typing import Set, Tuple
from .context import CONFIG, user_states, absent_notified
from .models import UserState
from .models import Zone

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _zone_group_key(zone: Zone):
    if zone.name:
        return (zone.type, "name", zone.name)
    return (zone.type, "id", zone.id)


def update_user_state(user_id: int, lat: float, lon: float) -> Tuple[Set[int], Set[int]]:
    now = datetime.now(timezone.utc)
    prev_state = user_states.get(user_id)
    prev_zones = prev_state.current_zone_ids if prev_state else set()

    new_zones: Set[int] = set()
    for z in CONFIG.zones:
        dist = haversine_m(lat, lon, z.center_lat, z.center_lng)
        if dist <= z.radius_m:
            new_zones.add(z.id)

    prev_groups = {}
    for zid in prev_zones:
        zone = CONFIG.zones_by_id.get(zid)
        if not zone:
            continue
        key = _zone_group_key(zone)
        prev_groups.setdefault(key, []).append(zid)

    new_groups = {}
    for zid in new_zones:
        zone = CONFIG.zones_by_id.get(zid)
        if not zone:
            continue
        key = _zone_group_key(zone)
        new_groups.setdefault(key, []).append(zid)

    prev_group_keys = set(prev_groups.keys())
    new_group_keys = set(new_groups.keys())

    entered_groups = new_group_keys - prev_group_keys
    exited_groups = prev_group_keys - new_group_keys

    entered_final: Set[int] = set()
    exited_final: Set[int] = set()

    for key in entered_groups:
        ids_for_group = new_groups.get(key)
        if ids_for_group:
            entered_final.add(ids_for_group[0])

    for key in exited_groups:
        ids_for_group = prev_groups.get(key)
        if ids_for_group:
            exited_final.add(ids_for_group[0])

    user_states[user_id] = UserState(
        last_lat=lat,
        last_lng=lon,
        last_time=now,
        current_zone_ids=new_zones,
    )

    global absent_notified
    absent_notified = {pair for pair in absent_notified if pair[0] != user_id}

    return entered_final, exited_final