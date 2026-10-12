from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytz
from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.types import ContentType, FSInputFile

from .content import ContentBlock
from .context import AppContext
from .keyboards import (
    begin_keyboard,
    contact_keyboard,
    next_block_keyboard,
    quiz_keyboard,
    start_quiz_keyboard,
)
from .quiz import VisitorSession
from .texts import FAREWELL, INTRODUCTION, QUIZ_INVITATION, WELCOME

LOGGER = logging.getLogger(__name__)


def build_visitor_router(context: AppContext) -> Router:
    router = Router(name="visitor")

    @router.message(Command("start"))
    async def start(message: types.Message) -> None:
        if not message.from_user:
            return
        user_id = message.from_user.id
        if user_id == context.settings.admin_id:
            return
        if context.database.has_result(user_id):
            await message.answer(
                "Вы уже проходили викторину. Её можно пройти один раз."
            )
            return
        context.sessions.start(user_id)
        await message.answer(WELCOME, reply_markup=contact_keyboard())

    @router.message(F.content_type == ContentType.CONTACT)
    async def contact(message: types.Message) -> None:
        if not message.from_user or not message.contact:
            return
        if message.contact.user_id not in (None, message.from_user.id):
            await message.answer("Пожалуйста, отправьте собственный контакт.")
            return
        try:
            session = context.sessions.require(message.from_user.id)
        except LookupError:
            await message.answer("Сначала отправьте команду /start.")
            return
        session.phone_number = message.contact.phone_number
        await message.answer(
            INTRODUCTION,
            reply_markup=begin_keyboard(),
        )
        await message.answer(
            "Контакт сохранён.", reply_markup=types.ReplyKeyboardRemove()
        )

    @router.callback_query(F.data.in_({"content:start", "content:next"}))
    async def show_content(callback: types.CallbackQuery, bot: Bot) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        try:
            session = context.sessions.require(callback.from_user.id)
        except LookupError:
            await callback.message.answer("Сначала отправьте команду /start.")
            return
        await _remove_old_keyboard(bot, callback, session)
        if session.content_index >= len(context.content_blocks):
            await callback.message.answer(
                QUIZ_INVITATION, reply_markup=start_quiz_keyboard()
            )
            return

        block = context.content_blocks[session.content_index]
        await _send_block(callback.message, block)
        session.content_index += 1

        if session.content_index < len(context.content_blocks):
            text = block.transition or "Перейдите к следующему разделу экспозиции."
            transition = await callback.message.answer(
                text, reply_markup=next_block_keyboard()
            )
            session.previous_message_id = transition.message_id
        else:
            await callback.message.answer(
                QUIZ_INVITATION, reply_markup=start_quiz_keyboard()
            )

    @router.callback_query(F.data == "quiz:start")
    async def start_quiz(callback: types.CallbackQuery) -> None:
        await callback.answer()
        await _send_question(context, callback)

    @router.callback_query(F.data.startswith("quiz:"))
    async def answer_quiz(callback: types.CallbackQuery) -> None:
        if callback.data == "quiz:answered":
            await callback.answer("Ответ уже принят.")
            return
        if not callback.from_user:
            return
        try:
            _, question_raw, option_raw = callback.data.split(":", 2)
            question_index = int(question_raw)
            option_index = int(option_raw)
            session = context.sessions.require(callback.from_user.id)
        except (ValueError, LookupError):
            await callback.answer("Этот ответ больше не доступен.", show_alert=True)
            return

        if question_index != session.question_index:
            await callback.answer("Перейдите к текущему вопросу.")
            return
        question = context.questions[question_index]
        try:
            is_correct = session.answer(option_index, question)
        except ValueError:
            await callback.answer("Ответ уже принят.")
            return

        await callback.answer("Верно!" if is_correct else "Ответ принят.")
        await callback.message.edit_reply_markup(
            reply_markup=quiz_keyboard(question_index, question, option_index)
        )
        if is_correct:
            await callback.message.answer("Да, всё верно!")
        else:
            await callback.message.answer(f"Правильный ответ: {question.correct}")

        session.advance_question()
        if session.question_index < len(context.questions):
            await _send_question(context, callback)
            return
        await _finish_quiz(context, callback, session)

    @router.message(Command("help"))
    async def help_command(message: types.Message) -> None:
        await message.answer(
            "Чтобы начать, отправьте /start. Если бот не отвечает, обратитесь к "
            "организатору экспозиции."
        )

    return router


async def _send_block(message: types.Message, block: ContentBlock) -> types.Message:
    if block.photo:
        photo = _telegram_media(block.photo)
        sent = await message.answer_photo(photo, caption=block.title)
    else:
        sent = await message.answer(f"Раздел: {block.title}")
    if block.audio:
        await message.answer_audio(_telegram_media(block.audio))
    return sent


def _telegram_media(value: str) -> str | FSInputFile:
    path = Path(value)
    return FSInputFile(path) if path.exists() else value


async def _remove_old_keyboard(
    bot: Bot,
    callback: types.CallbackQuery,
    session: VisitorSession,
) -> None:
    if session.previous_message_id is None or callback.message is None:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=session.previous_message_id,
            reply_markup=None,
        )
    except Exception:
        LOGGER.debug("Previous content keyboard is already unavailable.", exc_info=True)


async def _send_question(context: AppContext, callback: types.CallbackQuery) -> None:
    session = context.sessions.require(callback.from_user.id)
    if session.question_index >= len(context.questions):
        await callback.message.answer("Викторина уже завершена.")
        return
    question = context.questions[session.question_index]
    await callback.message.answer(
        question.text,
        reply_markup=quiz_keyboard(session.question_index, question),
    )


async def _finish_quiz(
    context: AppContext,
    callback: types.CallbackQuery,
    session: VisitorSession,
) -> None:
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    context.database.save_result(
        name=callback.from_user.full_name,
        telegram_id=callback.from_user.id,
        score=session.score,
        test_date=now.date().isoformat(),
        test_time=now.strftime("%H:%M:%S"),
        phone_number=session.phone_number,
    )
    await callback.message.answer(
        f"Вы правильно ответили на {session.score}/{len(context.questions)} вопросов."
    )
    if (
        session.score == len(context.questions)
        and context.settings.prize_deadline is not None
        and now.date() <= context.settings.prize_deadline
    ):
        await callback.message.answer(
            "Получить приз можно на стойке администраторов, показав это сообщение. ❤️"
        )
    await callback.message.answer(FAREWELL)
