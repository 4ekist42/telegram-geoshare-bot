import asyncio
import logging
from datetime import datetime, timezone

from .context import CONFIG, bot, user_states, absent_notified
from .notify import resolve_sender_label, get_admin_effective_flags


async def absence_watcher():
    global absent_notified
    while True:
        try:
            await asyncio.sleep(60)
            if not user_states:
                continue

            now = datetime.now(timezone.utc)
            for user_id, state in list(user_states.items()):
                delta_min = (now - state.last_time).total_seconds() / 60.0

                for adm in CONFIG.telegram.admins:
                    eff = get_admin_effective_flags(adm)
                    if not eff.notify_absent_enabled:
                        continue
                    if delta_min < eff.notify_absent_minutes:
                        continue

                    key = (user_id, adm.id)
                    if key in absent_notified:
                        continue

                    label = resolve_sender_label(user_id, None)
                    text = f"⏰ Нет локации от {label} уже {int(delta_min)} минут"
                    try:
                        await bot.send_message(adm.id, text)
                        if eff.send_current_location_with_alert:
                            await bot.send_location(
                                adm.id,
                                latitude=state.last_lat,
                                longitude=state.last_lng,
                            )
                    except Exception as e:
                        logging.warning("Не удалось отправить absent-сообщение админу %s: %s", adm.id, e)

                    absent_notified.add(key)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.exception("Ошибка в absence_watcher: %s", e)