import json
import logging
from typing import List, Dict

from .models import (
    Zone,
    ZoneNotifications,
    GlobalZoneConfig,
    TelegramGlobal,
    TelegramAdmin,
    TelegramAcceptFromUser,
    TelegramAcceptFrom,
    TelegramShowSender,
    TelegramConfig,
    Config,
)


def load_json_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_config(data: dict) -> Config:
    g = data.get("global", {})
    g_secure = g.get("secure", {}) or {}
    g_danger = g.get("danger", {}) or {}

    zone_global = GlobalZoneConfig(
        secure_notify_exit=bool(g_secure.get("notify_exit", True)),
        secure_notify_enter=bool(g_secure.get("notify_enter", True)),
        danger_notify_exit=bool(g_danger.get("notify_exit", True)),
        danger_notify_enter=bool(g_danger.get("notify_enter", True)),
    )

    zones_list: List[Zone] = []
    zones_by_id: Dict[int, Zone] = {}

    for z in data.get("zones", []) or []:
        try:
            zid = int(z.get("id") or 0)
            if zid <= 0:
                continue
            ztype = z.get("type", "secure")
            if ztype not in ("secure", "danger"):
                ztype = "secure"
            zname = z.get("name")
            center = z.get("center", {}) or {}
            lat = float(center.get("lat"))
            lng = float(center.get("lng"))
            radius_m = float(z.get("radius_m"))
            notif_cfg = z.get("notifications", {}) or {}
            zn = Zone(
                id=zid,
                type=ztype,
                name=zname,
                center_lat=lat,
                center_lng=lng,
                radius_m=radius_m,
                notifications=ZoneNotifications(
                    override=bool(notif_cfg.get("override", False)),
                    notify_on_enter=bool(notif_cfg.get("notify_on_enter", False)),
                    notify_on_exit=bool(notif_cfg.get("notify_on_exit", False)),
                ),
            )
        except Exception as e:
            logging.warning("Не удалось распарсить зону %r: %s", z, e)
            continue

        zones_list.append(zn)
        zones_by_id[zn.id] = zn

    tg = data.get("telegram", {}) or {}
    tg_global = tg.get("global", {}) or {}
    tg_global_cfg = TelegramGlobal(
        notify_location_start=bool(tg_global.get("notify_location_start", True)),
        notify_location_stop=bool(tg_global.get("notify_location_stop", True)),
        notify_absent_enabled=bool(tg_global.get("notify_absent_enabled", False)),
        notify_absent_minutes=int(tg_global.get("notify_absent_minutes", 10)),
        send_current_location_with_alert=bool(tg_global.get("send_current_location_with_alert", False)),
    )

    admins = []
    for a in tg.get("admins", []) or []:
        try:
            aid = int(a.get("id"))
        except Exception:
            continue
        name = a.get("name") or None
        zones_raw = a.get("zones") or []
        zones_ids = []
        for z in zones_raw:
            s = str(z)
            if s.isdigit():
                zones_ids.append(int(s))
        admins.append(TelegramAdmin(
            id=aid,
            name=name,
            override=bool(a.get("override", False)),
            notify_location_start=bool(a.get("notify_location_start", True)),
            notify_location_stop=bool(a.get("notify_location_stop", True)),
            notify_absent_enabled=bool(a.get("notify_absent_enabled", False)),
            notify_absent_minutes=int(a.get("notify_absent_minutes", 10)),
            send_current_location_with_alert=bool(a.get("send_current_location_with_alert", False)),
            zones=zones_ids,
        ))

    af = tg.get("accept_from", {}) or {}
    mode = af.get("mode", "any")
    if mode not in ("any", "list"):
        mode = "any"
    users = []
    for u in af.get("users", []) or []:
        try:
            uid = int(u.get("id"))
        except Exception:
            continue
        uname = u.get("name") or None
        users.append(TelegramAcceptFromUser(id=uid, name=uname))
    accept_from = TelegramAcceptFrom(mode=mode, users=users)

    ss = tg.get("show_sender", {}) or {}
    show_sender = TelegramShowSender(
        show_name=bool(ss.get("show_name", True)),
        show_id=bool(ss.get("show_id", True)),
    )

    telegram_cfg = TelegramConfig(
        global_cfg=tg_global_cfg,
        admins=admins,
        accept_from=accept_from,
        show_sender=show_sender,
    )

    return Config(
        zone_global=zone_global,
        zones=zones_list,
        zones_by_id=zones_by_id,
        telegram=telegram_cfg,
    )