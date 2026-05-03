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

STAGE_INPUT = "input"
STAGE_CONFIRM = "confirm"
STAGE_COMPLETE = "complete"

FORM_KEYS = (
    "form_procedure",
    "form_name",
    "form_furigana",
    "form_owner_teacher",
    "form_flow_teacher",
    "form_agreement",
    "form_new_email",
    "form_new_email_confirm",
    "form_new_notes",
    "form_change_current",
    "form_change_target",
    "form_change_confirm",
    "form_change_notes",
    "form_stop_current",
    "form_stop_notes",
)


def init_session_state() -> None:
    if "stage" not in st.session_state:
        st.session_state["stage"] = STAGE_INPUT
    if "pending_payload" not in st.session_state:
        st.session_state["pending_payload"] = None
    if "completed_receipt_id" not in st.session_state:
        st.session_state["completed_receipt_id"] = None


def reset_form() -> None:
    for key in FORM_KEYS:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["pending_payload"] = None
    st.session_state["completed_receipt_id"] = None
    st.session_state["stage"] = STAGE_INPUT


def render_procedure_fields(procedure: str) -> dict[str, str]:
    if procedure == "新規登録":
        new_email = st.text_input(
            "新しく登録したいログイン用メールアドレス",
            key="form_new_email",
        )
        confirm_email = st.text_input(
            "確認のため、もう一度同じメールアドレスをご入力ください",
            key="form_new_email_confirm",
        )
        notes = st.text_area("その他・ご連絡事項", key="form_new_notes")
        return {
            "current_email": "",
            "target_email": new_email,
            "confirm_email": confirm_email,
            "notes": notes,
        }

    if procedure == "登録内容の変更":
        current_email = st.text_input(
            "現在登録しているメールアドレス",
            key="form_change_current",
        )
        target_email = st.text_input(
            "変更後に使うメールアドレス",
            key="form_change_target",
        )
        confirm_email = st.text_input(
            "確認のため、変更後のメールアドレスをもう一度ご入力ください",
            key="form_change_confirm",
        )
        notes = st.text_area("その他・変更内容の詳細", key="form_change_notes")
        return {
            "current_email": current_email,
            "target_email": target_email,
            "confirm_email": confirm_email,
            "notes": notes,
        }

    current_email = st.text_input(
        "現在登録しているメールアドレス",
        key="form_stop_current",
    )
    notes = st.text_area("その他・ご連絡事項", key="form_stop_notes")
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


def render_input_stage() -> None:
    st.title(APP_TITLE)
    st.write(APP_DESCRIPTION)
    st.warning(LINE_WARNING)

    with st.form("member_intake_form"):
        procedure = st.radio(
            "ご希望のお手続きをお選びください",
            PROCEDURE_OPTIONS,
            horizontal=False,
            key="form_procedure",
        )

        st.subheader("共通項目")
        name = st.text_input("お名前", key="form_name")
        furigana = st.text_input("ふりがな", key="form_furigana")
        owner_teacher = st.text_input("浄化オーナーの先生", key="form_owner_teacher")
        flow_teacher = st.text_input("流れの先生", key="form_flow_teacher")

        st.subheader(procedure)
        procedure_fields = render_procedure_fields(procedure)

        agreement = st.checkbox(AGREEMENT_LABEL, key="form_agreement")
        submitted = st.form_submit_button(
            "確認画面へ進む", use_container_width=True
        )

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

    st.session_state["pending_payload"] = payload
    st.session_state["stage"] = STAGE_CONFIRM
    st.rerun()


def _build_confirm_rows(payload: dict[str, str]) -> list[tuple[str, str]]:
    procedure = payload["procedure"]
    rows: list[tuple[str, str]] = [
        ("お手続き", payload["procedure"]),
        ("お名前", payload["name"]),
        ("ふりがな", payload["furigana"]),
        ("浄化オーナーの先生", payload["owner_teacher"]),
        ("流れの先生", payload["flow_teacher"] or "（未入力）"),
    ]

    if procedure == "新規登録":
        rows.append(("新しく登録するメールアドレス", payload["target_email"]))
    elif procedure == "登録内容の変更":
        rows.append(("現在登録しているメールアドレス", payload["current_email"]))
        rows.append(("変更後のメールアドレス", payload["target_email"]))
    else:
        rows.append(("現在登録しているメールアドレス", payload["current_email"]))

    rows.append(("その他・ご連絡事項", payload["notes"] or "（なし）"))
    return rows


def render_confirm_stage() -> None:
    payload = st.session_state.get("pending_payload")
    if not payload:
        st.session_state["stage"] = STAGE_INPUT
        st.rerun()
        return

    st.title("ご入力内容の確認")
    st.write("以下の内容で送信します。よろしければ「この内容で送信する」を押してください。")

    for label, value in _build_confirm_rows(payload):
        col_label, col_value = st.columns([1, 2])
        with col_label:
            st.markdown(f"**{label}**")
        with col_value:
            st.write(value)

    st.divider()

    col_back, col_submit = st.columns(2)
    with col_back:
        back_clicked = st.button(
            "← 修正する", use_container_width=True, key="confirm_back"
        )
    with col_submit:
        send_clicked = st.button(
            "この内容で送信する",
            type="primary",
            use_container_width=True,
            key="confirm_send",
        )

    if back_clicked:
        st.session_state["stage"] = STAGE_INPUT
        st.rerun()
        return

    if not send_clicked:
        return

    try:
        repository = SheetsRepository.from_streamlit_secrets(st.secrets)
        receipt_id = repository.append_submission(payload)
    except SheetsConfigError as exc:
        st.error("保存先の設定がまだ完了していません。")
        st.info(str(exc))
        return
    except Exception as exc:  # pragma: no cover - runtime safeguard
        st.error("保存時にエラーが発生しました。")
        st.info(f"詳細: {exc}")
        return

    st.session_state["completed_receipt_id"] = receipt_id
    st.session_state["pending_payload"] = None
    st.session_state["stage"] = STAGE_COMPLETE
    st.rerun()


def render_complete_stage() -> None:
    st.title("受付が完了しました")
    st.success(COMPLETION_MESSAGE)

    receipt_id = st.session_state.get("completed_receipt_id")
    if receipt_id:
        st.write(f"受付番号: **{receipt_id}**")

    st.divider()

    if st.button("新しい受付を始める", key="complete_restart"):
        reset_form()
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📝",
        layout="centered",
    )

    init_session_state()

    stage = st.session_state["stage"]

    if stage == STAGE_CONFIRM:
        render_confirm_stage()
    elif stage == STAGE_COMPLETE:
        render_complete_stage()
    else:
        render_input_stage()


if __name__ == "__main__":
    main()
