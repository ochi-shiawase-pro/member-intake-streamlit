from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from src.form_fields import LOGIN_TROUBLE_OPTIONS, PROCEDURE_OPTIONS
from src import ghost_client as ghost_client_mod
from src.ghost_client import GhostClient, GhostConfigError
from src.sheets_repository import SheetsConfigError, SheetsRepository
from src.ui_text import (
    AGREEMENT_LABEL,
    APP_DESCRIPTION,
    APP_TITLE,
    COMPLETION_MESSAGE,
    LINE_WARNING,
)
from src.validators import (
    normalize_email,
    suggest_email_correction,
    validate_submission,
)


EMAIL_HELP = "※大文字・小文字、全角・半角は区別されません（自動で揃えます）"


JST = ZoneInfo("Asia/Tokyo")

CUSTOM_STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;500;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea,
.stRadio, .stButton, .stCheckbox, .stForm, .stAlert, h1, h2, h3, h4, p, label {
    font-family: 'M PLUS Rounded 1c', 'Hiragino Maru Gothic ProN',
                 'Yu Gothic UI', sans-serif !important;
}
.stApp { background-color: #FFF9F0; }
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 720px !important;
}
h1, h2, h3 { color: #5C4A3D !important; letter-spacing: 0.02em; }
.stTextInput input, .stTextArea textarea {
    border-radius: 14px !important;
    padding: 0.7rem 0.95rem !important;
    border: 1.5px solid #F2D7D0 !important;
    background-color: #FFFFFF !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #E8A5A0 !important;
    box-shadow: 0 0 0 3px rgba(232, 165, 160, 0.22) !important;
}
.stButton button, .stFormSubmitButton button, div[data-testid="stFormSubmitButton"] button {
    border-radius: 999px !important;
    padding: 0.65rem 1.6rem !important;
    font-weight: 500 !important;
    border: 1.5px solid #E8A5A0 !important;
    background-color: #FFFFFF !important;
    color: #C76B65 !important;
    transition: all 0.2s ease;
}
.stButton button:hover, .stFormSubmitButton button:hover,
div[data-testid="stFormSubmitButton"] button:hover {
    background-color: #FBEDEB !important;
    border-color: #C76B65 !important;
}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: #E8A5A0 !important;
    color: #FFFFFF !important;
    border-color: #E8A5A0 !important;
}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
    background-color: #D88B85 !important;
    border-color: #D88B85 !important;
}
.stAlert { border-radius: 14px !important; }
hr { border-color: #F2D7D0 !important; }
div[data-testid="stForm"] {
    background-color: #FFFDF8;
    border: 1px solid #F5E4DE;
    border-radius: 18px;
    padding: 1.6rem 1.8rem !important;
}
</style>
"""

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
    "form_login_predicted_email",
    "form_login_trouble_types",
    "form_login_notes",
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
            help=EMAIL_HELP,
        )
        st.caption(EMAIL_HELP)
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
            help=EMAIL_HELP,
        )
        target_email = st.text_input(
            "変更後に使うメールアドレス",
            key="form_change_target",
            help=EMAIL_HELP,
        )
        st.caption(EMAIL_HELP)
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

    if procedure == "ご利用停止":
        current_email = st.text_input(
            "現在登録しているメールアドレス",
            key="form_stop_current",
            help=EMAIL_HELP,
        )
        st.caption(EMAIL_HELP)
        notes = st.text_area("その他・ご連絡事項", key="form_stop_notes")
        return {
            "current_email": current_email,
            "target_email": "",
            "confirm_email": "",
            "notes": notes,
        }

    # ログインに関するご相談
    st.info(
        "ログインでお困りの方のための受付です。"
        "分かる範囲でご記入ください。お名前から照合しますので、"
        "メールアドレスが分からなくても大丈夫です。"
    )
    trouble_types = st.multiselect(
        "お困りの状況（あてはまるものをすべて）",
        LOGIN_TROUBLE_OPTIONS,
        key="form_login_trouble_types",
    )
    predicted_email = st.text_input(
        "思い当たるログイン用メールアドレス（分かる範囲で / 任意）",
        key="form_login_predicted_email",
        help=EMAIL_HELP,
    )
    st.caption(EMAIL_HELP + "　※分からない場合は空欄で構いません")
    free_notes = st.text_area(
        "詳しい状況・ご連絡事項",
        key="form_login_notes",
        placeholder="例：先週まではログインできていました／メールが何度送っても届きません など",
    )
    combined_notes_parts: list[str] = []
    if trouble_types:
        combined_notes_parts.append("【お困りの状況】" + " / ".join(trouble_types))
    if free_notes.strip():
        combined_notes_parts.append("【詳細】" + free_notes.strip())
    return {
        "current_email": predicted_email,
        "target_email": "",
        "confirm_email": "",
        "notes": "\n".join(combined_notes_parts),
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
    current_email_n = normalize_email(current_email)
    target_email_n = normalize_email(target_email)
    confirm_email_n = normalize_email(confirm_email)

    if procedure in ("新規登録", "登録内容の変更"):
        ghost_target_email = target_email_n
    else:
        ghost_target_email = current_email_n

    return {
        "procedure": procedure,
        "name": name.strip(),
        "furigana": furigana.strip(),
        "owner_teacher": owner_teacher.strip(),
        "flow_teacher": flow_teacher.strip(),
        "current_email": current_email_n,
        "target_email": target_email_n,
        "confirm_email": confirm_email_n,
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
    elif procedure == "ご利用停止":
        rows.append(("現在登録しているメールアドレス", payload["current_email"]))
    else:  # ログインに関するご相談
        rows.append((
            "思い当たるメールアドレス",
            payload["current_email"] or "（分からない）",
        ))

    rows.append(("ご連絡事項・状況", payload["notes"] or "（なし）"))
    return rows


def _show_email_typo_warnings(payload: dict[str, str]) -> None:
    """よくあるドメインタイポを検出して、確認画面でやさしく注意喚起する。"""
    candidates = [
        ("メールアドレス", payload["target_email"]),
        ("現在のメールアドレス", payload["current_email"]),
    ]
    for label, value in candidates:
        if not value:
            continue
        suggestion = suggest_email_correction(value)
        if suggestion:
            st.warning(
                f"{label}「{value}」は、もしかして "
                f"**「{suggestion}」** のお間違いではありませんか？\n"
                "このまま送信もできますが、念のためご確認ください。"
            )


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

    _show_email_typo_warnings(payload)

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
        # 受付完了と同時に、可能なら Ghost へも反映する（新規/変更のみ）。
        try:
            ghost = GhostClient.from_streamlit_secrets(st.secrets)
        except GhostConfigError:
            ghost = None

        if ghost is not None:
            procedure = payload["procedure"]
            if procedure in ("新規登録", "登録内容の変更"):
                repository.update_ghost_result(receipt_id, ghost_status="処理中")
                try:
                    skip_error = False
                    if procedure == "新規登録":
                        email = payload["target_email"]
                        try:
                            ghost.create_member(
                                email=email,
                                name=payload["name"],
                                labels=["member-intake"],
                            )
                        except Exception as exc:
                            # 既にメンバーが存在する場合は、そのまま完了扱いにする
                            status = getattr(exc, "status", None)
                            if status == 422:
                                existing = ghost.find_member_by_email(email)
                                if existing:
                                    repository.update_ghost_result(
                                        receipt_id,
                                        ghost_status="完了",
                                        remarks="既存メンバーのため追加はスキップしました。",
                                    )
                                    skip_error = True
                                else:
                                    raise
                            else:
                                raise
                    else:
                        current_email = payload["current_email"]
                        target_email = payload["target_email"]
                        member = ghost.find_member_by_email(current_email)
                        if not member:
                            raise RuntimeError("Ghost側に「現在登録メールアドレス」が見つかりませんでした。")
                        ghost.update_member(
                            member_id=str(member.get("id")),
                            email=target_email,
                            name=payload["name"] or None,
                        )
                    if not skip_error:
                        repository.update_ghost_result(receipt_id, ghost_status="完了", remarks="")
                except Exception as exc:  # pragma: no cover - runtime safeguard
                    repository.update_ghost_result(
                        receipt_id,
                        ghost_status="エラー",
                        remarks=str(exc)[:400],
                    )
        else:
            # Ghost連携が未設定の場合も、受付側で分かるように備考へ残す
            # （Ghost反映ステータス自体は初期値「未」のまま）
            repository.update_ghost_result(
                receipt_id,
                ghost_status=payload["ghost_status"],
                ghost_processed_at="",
                remarks="Ghost連携未設定（Secretsに ghost_admin_api_url / ghost_admin_api_key がありません）",
            )
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

    st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

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
