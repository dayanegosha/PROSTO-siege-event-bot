from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher

from .admin_handlers import build_admin_router
from .config import Settings
from .content import load_content_blocks
from .context import AppContext
from .database import ResultRepository
from .quiz import SessionStore, load_questions
from .visitor_handlers import build_visitor_router


async def run() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    context = AppContext(
        settings=settings,
        database=ResultRepository(settings.database_path),
        questions=load_questions(settings.quiz_path),
        content_blocks=load_content_blocks(settings.content_path),
        sessions=SessionStore(),
    )
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_admin_router(context))
    dispatcher.include_router(build_visitor_router(context))
    try:
        await dispatcher.start_polling(bot)
    finally:
        context.database.close()
        await bot.session.close()
