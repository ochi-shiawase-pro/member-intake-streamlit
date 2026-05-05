from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from zoneinfo import ZoneInfo


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

JST = ZoneInfo("Asia/Tokyo")


class SheetsConfigError(RuntimeError):
    pass


@dataclass
class SheetsRepository:
    spreadsheet_name: str
    worksheet_name: str
    client: gspread.Client

    @classmethod
    def from_streamlit_secrets(cls, secrets: Any) -> "SheetsRepository":
        if "gcp_service_account" not in secrets:
            raise SheetsConfigError("`gcp_service_account` が Secrets に設定されていません。")

        service_account_info = dict(secrets["gcp_service_account"])
        spreadsheet_name = secrets.get("spreadsheet_name", "億万長者リスト")
        worksheet_name = secrets.get("worksheet_name", "受付一覧")

        if not spreadsheet_name:
            raise SheetsConfigError("`spreadsheet_name` が設定されていません。")
        if not worksheet_name:
            raise SheetsConfigError("`worksheet_name` が設定されていません。")

        credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        client = gspread.authorize(credentials)
        return cls(
            spreadsheet_name=spreadsheet_name,
            worksheet_name=worksheet_name,
            client=client,
        )

    def append_submission(self, payload: dict[str, str]) -> str:
        worksheet = self.client.open(self.spreadsheet_name).worksheet(self.worksheet_name)
        receipt_id = self._next_receipt_id(worksheet)

        row = [
            receipt_id,
            payload["received_at"],
            payload["procedure"],
            payload["name"],
            payload["furigana"],
            payload["owner_teacher"],
            payload["flow_teacher"],
            payload["current_email"],
            payload["target_email"],
            payload["confirm_email"],
            payload["ghost_target_email"],
            payload["notes"],
            payload["agreement"],
            payload["receipt_status"],
            payload["ghost_status"],
            payload["ghost_processed_at"],
            payload["remarks"],
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return receipt_id

    def update_ghost_result(
        self,
        receipt_id: str,
        *,
        ghost_status: str,
        ghost_processed_at: str | None = None,
        remarks: str | None = None,
    ) -> None:
        worksheet = self.client.open(self.spreadsheet_name).worksheet(self.worksheet_name)
        cell = worksheet.find(receipt_id)
        row_index = cell.row

        processed_at = ghost_processed_at
        if processed_at is None:
            processed_at = datetime.now(JST).strftime("%Y/%m/%d %H:%M:%S")

        values = [
            [ghost_status, processed_at, remarks or ""],
        ]
        worksheet.update(
            f"O{row_index}:Q{row_index}",
            values,
            value_input_option="USER_ENTERED",
        )

    def _next_receipt_id(self, worksheet: gspread.Worksheet) -> str:
        values = worksheet.col_values(1)
        max_number = 0
        for value in values[1:]:
            match = re.fullmatch(r"R(\d{4})", value.strip())
            if not match:
                continue
            max_number = max(max_number, int(match.group(1)))
        return f"R{max_number + 1:04d}"
