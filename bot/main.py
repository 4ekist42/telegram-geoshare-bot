import asyncio

from .context import bot, dp
from .absence import absence_watcher
from . import handlers  # noqa: F401


async def main():
    asyncio.create_task(absence_watcher())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())