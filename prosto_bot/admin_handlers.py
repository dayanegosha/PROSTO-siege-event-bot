from __future__ import annotations

import tempfile
from pathlib import Path

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

from .context import AppContext
from .keyboards import admin_keyboard, cancel_keyboard, confirm_clear_keyboard
from .reports import write_xlsx


def build_admin_router(context: AppContext) -> Router:
    router = Router(name="admin")

    def is_admin(user_id: int) -> bool:
        return context.settings.admin_id != 0 and user_id == context.settings.admin_id

    @router.message(Command("start"), F.from_user.id == context.settings.admin_id)
    async def start(message: types.Message) -> None:
        await message.answer("Панель администратора", reply_markup=admin_keyboard())

    @router.callback_query(F.data == "admin:list")
    async def list_results(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        await callback.answer()
        rows = context.database.list_results()
        if not rows:
            await callback.message.answer("Результатов пока нет.")
            return
        lines = [
            (
                f"{row.name} · {row.telegram_id} · {row.score}/{len(context.questions)} · "
                f"{row.test_date} {row.test_time} МСК · {row.phone_number or 'без телефона'}"
            )
            for row in rows
        ]
        text = "\n".join(lines)
        for start in range(0, len(text), 3900):
            await callback.message.answer(text[start : start + 3900])

    @router.callback_query(F.data == "admin:export")
    async def export_results(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        await callback.answer()
        rows = context.database.list_results()
        with tempfile.TemporaryDirectory(prefix="prosto-results-") as directory:
            path = Path(directory) / "results.xlsx"
            write_xlsx(path, rows)
            await callback.message.answer_document(FSInputFile(path))

    @router.callback_query(F.data == "admin:delete")
    async def request_deletion(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        context.sessions.request_admin_deletion(callback.from_user.id)
        await callback.answer()
        await callback.message.answer(
            "Введите Telegram ID участника:", reply_markup=cancel_keyboard()
        )

    @router.message(
        lambda message: bool(
            message.from_user
            and context.sessions.awaits_admin_deletion(message.from_user.id)
        )
    )
    async def delete_result(message: types.Message) -> None:
        if not message.from_user or not is_admin(message.from_user.id):
            return
        try:
            telegram_id = int(message.text or "")
        except ValueError:
            await message.answer("ID должен состоять только из цифр.")
            return
        deleted = context.database.delete_result(telegram_id)
        context.sessions.cancel_admin_deletion(message.from_user.id)
        await message.answer(
            "Запись удалена." if deleted else "Участник с таким ID не найден.",
            reply_markup=admin_keyboard(),
        )

    @router.callback_query(F.data == "admin:clear:confirm")
    async def request_clear(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        await callback.answer()
        await callback.message.answer(
            "Удалить все результаты без возможности восстановления?",
            reply_markup=confirm_clear_keyboard(),
        )

    @router.callback_query(F.data == "admin:clear")
    async def clear_results(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        deleted = context.database.clear()
        await callback.answer()
        await callback.message.answer(
            f"Удалено записей: {deleted}.", reply_markup=admin_keyboard()
        )

    @router.callback_query(F.data == "admin:cancel")
    async def cancel(callback: types.CallbackQuery) -> None:
        if not is_admin(callback.from_user.id):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        context.sessions.cancel_admin_deletion(callback.from_user.id)
        await callback.answer("Отменено")
        await callback.message.answer(
            "Панель администратора", reply_markup=admin_keyboard()
        )

    return router
