from typing import Optional, Tuple

import logging

from .context import CONFIG, bot
from .models import Zone, TelegramAdmin, TelegramGlobal


def is_sender_allowed(user_id: int) -> bool:
    af = CONFIG.telegram.accept_from
    if af.mode == "any":
        return True
    for u in af.users:
        if u.id == user_id:
            return True
    return False


def resolve_sender_label(user_id: int, full_name: Optional[str]) -> str:
    ss = CONFIG.telegram.show_sender
    parts = []
    config_name: Optional[str] = None
    for a in CONFIG.telegram.admins:
        if a.id == user_id and a.name:
            config_name = a.name
            break
    if config_name is None:
        for u in CONFIG.telegram.accept_from.users:
            if u.id == user_id and u.name:
                config_name = u.name
                break
    if ss.show_name:
        if config_name:
            parts.append(config_name)
        elif full_name:
            parts.append(full_name)
    if ss.show_id:
        parts.append(f"id={user_id}")
    if not parts:
        return str(user_id)
    return ", ".join(parts)


def describe_zone(zone: Zone) -> str:
    if zone.name:
        return f'"{zone.name}"'
    return f"#{zone.id}"


def get_effective_zone_notify(zone: Zone) -> Tuple[bool, bool]:
    zg = CONFIG.zone_global
    if zone.notifications.override:
        enter = zone.notifications.notify_on_enter
        exit_ = zone.notifications.notify_on_exit
    else:
        if zone.type == "danger":
            enter = zg.danger_notify_enter
            exit_ = zg.danger_notify_exit
        else:
            enter = zg.secure_notify_enter
            exit_ = zg.secure_notify_exit
    return enter, exit_


def get_admin_effective_flags(admin: TelegramAdmin) -> TelegramGlobal:
    g = CONFIG.telegram.global_cfg
    if not admin.override:
        return g
    return TelegramGlobal(
        notify_location_start=admin.notify_location_start,
        notify_location_stop=admin.notify_location_stop,
        notify_absent_enabled=admin.notify_absent_enabled,
        notify_absent_minutes=admin.notify_absent_minutes,
        send_current_location_with_alert=admin.send_current_location_with_alert,
    )


def admin_interested_in_zone(admin: TelegramAdmin, zone_id: int) -> bool:
    if not admin.zones:
        return True
    return zone_id in admin.zones


async def send_event_to_admins(
    event_text: str,
    sender_id: int,
    sender_name: Optional[str],
    *,
    location: Optional[Tuple[float, float]] = None,
    zone: Optional[Zone] = None,
    is_start_stop_absent: bool = False,
):
    if not CONFIG.telegram.admins:
        logging.info("Нет админов для отправки уведомления: %s", event_text)
        return

    label = resolve_sender_label(sender_id, sender_name)
    base_text = f"{event_text}\nОт: {label}"

    for adm in CONFIG.telegram.admins:
        if not is_start_stop_absent and zone is not None:
            if not admin_interested_in_zone(adm, zone.id):
                continue

        eff = get_admin_effective_flags(adm)

        if "🔴 Вход в опасную зону" in event_text or "⚠️ Выход из опасной зоны" in event_text \
                or "⚠️ Выход из безопасной зоны" in event_text:
            allowed = True
        else:
            if "▶️ Начало вещания" in event_text:
                allowed = eff.notify_location_start
            elif "⏹ Окончание вещания" in event_text:
                allowed = eff.notify_location_stop
            elif "⏰ Нет локации" in event_text:
                allowed = eff.notify_absent_enabled
            else:
                allowed = True

        if not allowed:
            continue

        try:
            await bot.send_message(adm.id, base_text)
            if location is not None and eff.send_current_location_with_alert:
                lat, lon = location
                await bot.send_location(adm.id, latitude=lat, longitude=lon)
        except Exception as e:
            logging.warning("Не удалось отправить сообщение админу %s: %s", adm.id, e)