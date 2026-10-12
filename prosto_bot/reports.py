from __future__ import annotations

from pathlib import Path

import xlsxwriter

from .database import Result

HEADERS = (
    "Имя в Telegram",
    "ID",
    "Баллы",
    "Попытки",
    "Дата прохождения",
    "Время прохождения (МСК)",
    "Номер телефона",
)


def write_xlsx(path: Path, results: list[Result]) -> None:
    with xlsxwriter.Workbook(path) as workbook:
        worksheet = workbook.add_worksheet("Результаты")
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAD3"})
        for column, title in enumerate(HEADERS):
            worksheet.write(0, column, title, header)
        for row_index, result in enumerate(results, start=1):
            values = (
                result.name,
                result.telegram_id,
                result.score,
                result.attempts,
                result.test_date,
                result.test_time,
                result.phone_number or "",
            )
            for column, value in enumerate(values):
                worksheet.write(row_index, column, value)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(results), len(HEADERS) - 1)
        worksheet.set_column(0, 0, 28)
        worksheet.set_column(1, 6, 20)
