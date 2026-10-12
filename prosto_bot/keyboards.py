from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .quiz import Question


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def begin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начнём", callback_data="content:start")]
        ]
    )


def next_block_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Готов перейти к следующему блоку",
                    callback_data="content:next",
                )
            ]
        ]
    )


def start_quiz_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать викторину", callback_data="quiz:start")]
        ]
    )


def quiz_keyboard(
    question_index: int,
    question: Question,
    selected_index: int | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for option_index, option in enumerate(question.options):
        prefix = ""
        callback = f"quiz:{question_index}:{option_index}"
        if selected_index is not None:
            if option_index == selected_index:
                prefix = "✅ " if option == question.correct else "❌ "
            else:
                prefix = "• "
            callback = "quiz:answered"
        rows.append(
            [InlineKeyboardButton(text=f"{prefix}{option}", callback_data=callback)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать результаты", callback_data="admin:list"
                )
            ],
            [InlineKeyboardButton(text="Скачать XLSX", callback_data="admin:export")],
            [
                InlineKeyboardButton(
                    text="Удалить пользователя", callback_data="admin:delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Очистить базу", callback_data="admin:clear:confirm"
                )
            ],
        ]
    )


def confirm_clear_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, очистить", callback_data="admin:clear"),
                InlineKeyboardButton(text="Отмена", callback_data="admin:cancel"),
            ]
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="admin:cancel")]
        ]
    )
