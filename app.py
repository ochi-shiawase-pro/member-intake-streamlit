from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from src.form_fields import PROCEDURE_OPTIONS
from src.sheets_repository import SheetsConfigError, SheetsRepository
from src.ui_text import (
    AGREEMENT_LABEL,
    APP_DESCRIPTION,
    APP_TITLE,
    COMPLETION_MESSAGE,
    LINE_WARNING,
)
from src.validators import validate_submission


JST = ZoneInfo("Asia/Tokyo")


def render_procedure_fields(procedure: str) -> dict[str, str]:
    if procedure == "新規登録":
        new_email = st.text_input("新しく登録したいログイン用メールアドレス")
        confirm_email = st.text_input("確認のため、もう一度同じメールアドレスをご入力ください")
        notes = st.text_area("その他・ご連絡事項")
        return {
            "current_email": "",
            "target_email": new_email,
            "confirm_email": confirm_email,
            "notes": notes,
        }

    if procedure == "登録内容の変更":
        current_email = st.text_input("現在登録しているメールアドレス")
        target_email = st.text_input("変更後に使うメールアドレス")
        confirm_email = st.text_input("確認のため、変更後のメールアドレスをもう一度ご入力ください")
        notes = st.text_area("その他・変更内容の詳細")
        return {
            "current_email": current_email,
            "target_email": target_email,
            "confirm_email": confirm_email,
            "notes": notes,
        }

    current_email = st.text_input("現在登録しているメールアドレス")
    notes = st.text_area("その他・ご連絡事項")
    return {
        "current_email": current_email,
        "target_email": "",
        "confirm_email": "",
        "notes": notes,
    }


def build_payload(
    procedure: str,
    name: str,
    furigana: str,
    owner_teacher: str,
    flow_teacher: str,
    current_email: str,
    target_email: str,
    confirm_email: str,
    notes: str,
) -> dict[str, str]:
    if procedure == "新規登録":
        ghost_target_email = target_email.strip()
    elif procedure == "登録内容の変更":
        ghost_target_email = target_email.strip()
    else:
        ghost_target_email = current_email.strip()

    return {
        "procedure": procedure,
        "name": name.strip(),
        "furigana": furigana.strip(),
        "owner_teacher": owner_teacher.strip(),
        "flow_teacher": flow_teacher.strip(),
        "current_email": current_email.strip(),
        "target_email": target_email.strip(),
        "confirm_email": confirm_email.strip(),
        "ghost_target_email": ghost_target_email,
        "notes": notes.strip(),
        "agreement": "同意あり",
        "received_at": datetime.now(JST).strftime("%Y/%m/%d %H:%M:%S"),
        "receipt_status": "未処理",
        "ghost_status": "未",
        "ghost_processed_at": "",
        "remarks": "",
    }


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📝",
        layout="centered",
    )

    st.title(APP_TITLE)
    st.write(APP_DESCRIPTION)
    st.warning(LINE_WARNING)

    with st.form("member_intake_form"):
        procedure = st.radio(
            "ご希望のお手続きをお選びください",
            PROCEDURE_OPTIONS,
            horizontal=False,
        )

        st.subheader("共通項目")
        name = st.text_input("お名前")
        furigana = st.text_input("ふりがな")
        owner_teacher = st.text_input("浄化オーナーの先生")
        flow_teacher = st.text_input("流れの先生")

        st.subheader(procedure)
        procedure_fields = render_procedure_fields(procedure)

        agreement = st.checkbox(AGREEMENT_LABEL)
        submitted = st.form_submit_button("内容を送信する", use_container_width=True)

    if not submitted:
        return

    payload = build_payload(
        procedure=procedure,
        name=name,
        furigana=furigana,
        owner_teacher=owner_teacher,
        flow_teacher=flow_teacher,
        current_email=procedure_fields["current_email"],
        target_email=procedure_fields["target_email"],
        confirm_email=procedure_fields["confirm_email"],
        notes=procedure_fields["notes"],
    )

    errors = validate_submission(payload, agreement_checked=agreement)
    if errors:
        for error in errors:
            st.error(error)
        return

    try:
        repository = SheetsRepository.from_streamlit_secrets(st.secrets)
        receipt_id = repository.append_submission(payload)
    except SheetsConfigError as exc:
        st.error("保存先の設定がまだ完了していません。")
        st.info(str(exc))
        with st.expander("送信内容の確認"):
            st.json(payload, expanded=False)
        return
    except Exception as exc:  # pragma: no cover - runtime safeguard
        st.error("保存時にエラーが発生しました。")
        st.info(f"詳細: {exc}")
        return

    st.success(COMPLETION_MESSAGE)
    st.write(f"受付番号: {receipt_id}")


if __name__ == "__main__":
    main()
