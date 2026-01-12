import logging
from typing import Optional

from aiogram.types import Message

from .context import dp, CONFIG, active_live_locations
from .geo import update_user_state, user_states
from .notify import (
    is_sender_allowed,
    send_event_to_admins,
    describe_zone,
    get_effective_zone_notify,
)


async def handle_location_event(
    msg: Message,
    *,
    kind: str,
):
    if not msg.location:
        return

    user_id = msg.from_user.id
    full_name: Optional[str] = msg.from_user.full_name

    if not is_sender_allowed(user_id):
        logging.info("Локация от %s проигнорирована (accept_from)", user_id)
        return

    lat = msg.location.latitude
    lon = msg.location.longitude

    entered, exited = update_user_state(user_id, lat, lon)
    state = user_states.get(user_id)
    current_zone_ids = state.current_zone_ids if state else set()

    secure_zone_for_msg = None
    danger_zone_for_msg = None

    for zid in current_zone_ids:
        zone = CONFIG.zones_by_id.get(zid)
        if not zone:
            continue
        if zone.type == "secure" and secure_zone_for_msg is None:
            secure_zone_for_msg = zone
        if zone.type == "danger" and danger_zone_for_msg is None:
            danger_zone_for_msg = zone

    if kind == "start":
        if secure_zone_for_msg and not danger_zone_for_msg:
            text = f"▶️ Начал вещание из безопасной зоны {describe_zone(secure_zone_for_msg)}"
        elif danger_zone_for_msg and not secure_zone_for_msg:
            text = f"▶️ Начал вещание из опасной зоны {describe_zone(danger_zone_for_msg)}"
        elif secure_zone_for_msg and danger_zone_for_msg:
            text = "▶️ Начал вещание: одновременно в безопасной и опасной зоне"
        else:
            text = "▶️ Начал вещание вне заданных зон"

        await send_event_to_admins(
            text,
            sender_id=user_id,
            sender_name=full_name,
            is_start_stop_absent=True,
        )

    elif kind == "end":
        await send_event_to_admins(
            "⏹ Окончание вещания live-location",
            sender_id=user_id,
            sender_name=full_name,
            location=(lat, lon),
            is_start_stop_absent=True,
        )

    for zid in entered:
        zone = CONFIG.zones_by_id.get(zid)
        if not zone:
            continue

        notify_enter, _ = get_effective_zone_notify(zone)
        if not notify_enter:
            continue

        if zone.type == "danger":
            text = f"🔴 Вход в опасную зону {describe_zone(zone)}"
        else:
            text = f"✅ Возврат в безопасную зону {describe_zone(zone)}"

        await send_event_to_admins(
            text,
            sender_id=user_id,
            sender_name=full_name,
            location=(lat, lon),
            zone=zone,
        )

    for zid in exited:
        zone = CONFIG.zones_by_id.get(zid)
        if not zone:
            continue
        _, notify_exit = get_effective_zone_notify(zone)
        if not notify_exit:
            continue

        if zone.type == "danger":
            text = f"⚠️ Выход из опасной зоны {describe_zone(zone)}"
        else:
            text = f"⚠️ Выход из безопасной зоны {describe_zone(zone)}"

        await send_event_to_admins(
            text,
            sender_id=user_id,
            sender_name=full_name,
            location=(lat, lon),
            zone=zone,
        )


@dp.message()
async def on_message(msg: Message):
    if not msg.location:
        logging.info("[NEW] %s: %r", msg.from_user.id, msg)
        return

    loc = msg.location

    if loc.live_period:
        active_live_locations.add(msg.message_id)
        logging.info(
            "[LIVE LOCATION START] user=%s msg_id=%s lat=%s lon=%s live_period=%s",
            msg.from_user.id,
            msg.message_id,
            loc.latitude,
            loc.longitude,
            loc.live_period,
        )
        await handle_location_event(msg, kind="start")
    else:
        logging.info(
            "[LOCATION] user=%s lat=%s lon=%s",
            msg.from_user.id,
            loc.latitude,
            loc.longitude,
        )
        await handle_location_event(msg, kind="single")


@dp.edited_message()
async def on_edited(msg: Message):
    if not msg.location:
        logging.info("[EDITED] %s: %r", msg.from_user.id, msg)
        return

    loc = msg.location

    if msg.message_id in active_live_locations and loc.live_period is None:
        logging.info(
            "[LIVE LOCATION END] user=%s msg_id=%s lat=%s lon=%s",
            msg.from_user.id,
            msg.message_id,
            loc.latitude,
            loc.longitude,
        )
        active_live_locations.discard(msg.message_id)
        await handle_location_event(msg, kind="end")
        return

    if loc.live_period is not None:
        logging.info(
            "[LIVE LOCATION UPDATE] user=%s msg_id=%s lat=%s lon=%s live_period=%s",
            msg.from_user.id,
            msg.message_id,
            loc.latitude,
            loc.longitude,
            loc.live_period,
        )
        await handle_location_event(msg, kind="update")
        return

    logging.info("[EDITED NON-LIVE] %s: %r", msg.from_user.id, msg)