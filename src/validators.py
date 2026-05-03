from __future__ import annotations

import re
import unicodedata


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# よくあるドメイン入力ミス → 正しいスペル
DOMAIN_TYPO_MAP = {
    "gmial.com": "gmail.com",
    "gmali.com": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cmo": "gmail.com",
    "gmal.com": "gmail.com",
    "hotmial.com": "hotmail.com",
    "hotmal.com": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "yahho.co.jp": "yahoo.co.jp",
    "yaho.co.jp": "yahoo.co.jp",
    "yahoo.con": "yahoo.com",
    "icloud.con": "icloud.com",
    "iclud.com": "icloud.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "ezewb.ne.jp": "ezweb.ne.jp",
    "docomo.ne.j": "docomo.ne.jp",
}


def normalize_email(value: str) -> str:
    """全角→半角、前後空白除去、小文字化。空文字はそのまま返す。"""
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(value)))


def suggest_email_correction(value: str) -> str | None:
    """よくあるドメインタイプミスを検出。修正案があれば返す。"""
    email = normalize_email(value)
    if "@" not in email:
        return None
    local, _, domain = email.rpartition("@")
    fixed = DOMAIN_TYPO_MAP.get(domain)
    if fixed:
        return f"{local}@{fixed}"
    return None


def _emails_match(a: str, b: str) -> bool:
    return normalize_email(a) == normalize_email(b)


def validate_submission(payload: dict[str, str], agreement_checked: bool) -> list[str]:
    errors: list[str] = []
    procedure = payload["procedure"]

    if not payload["name"]:
        errors.append("お名前をご入力ください。")
    if not payload["furigana"]:
        errors.append("ふりがなをご入力ください。")
    if not payload["owner_teacher"]:
        errors.append("浄化オーナーの先生をご入力ください。")
    if not agreement_checked:
        errors.append("確認事項にチェックを入れてください。")

    if procedure == "新規登録":
        if not payload["target_email"]:
            errors.append("新しく登録したいログイン用メールアドレスをご入力ください。")
        if not payload["confirm_email"]:
            errors.append("確認用メールアドレスをご入力ください。")
        if payload["target_email"] and not is_valid_email(payload["target_email"]):
            errors.append("メールアドレスの形式でご入力ください。")
        if payload["confirm_email"] and not is_valid_email(payload["confirm_email"]):
            errors.append("確認用メールアドレスの形式をご確認ください。")
        if (
            payload["target_email"]
            and payload["confirm_email"]
            and not _emails_match(payload["target_email"], payload["confirm_email"])
        ):
            errors.append("確認用メールアドレスが一致していません。")

    if procedure == "登録内容の変更":
        if not payload["current_email"]:
            errors.append("現在登録しているメールアドレスをご入力ください。")
        if not payload["target_email"]:
            errors.append("変更後に使うメールアドレスをご入力ください。")
        if not payload["confirm_email"]:
            errors.append("確認用メールアドレスをご入力ください。")
        if payload["current_email"] and not is_valid_email(payload["current_email"]):
            errors.append("現在登録メールアドレスの形式をご確認ください。")
        if payload["target_email"] and not is_valid_email(payload["target_email"]):
            errors.append("変更後メールアドレスの形式をご確認ください。")
        if payload["confirm_email"] and not is_valid_email(payload["confirm_email"]):
            errors.append("確認用メールアドレスの形式をご確認ください。")
        if (
            payload["target_email"]
            and payload["confirm_email"]
            and not _emails_match(payload["target_email"], payload["confirm_email"])
        ):
            errors.append("確認用メールアドレスが一致していません。")

    if procedure == "ご利用停止":
        if not payload["current_email"]:
            errors.append("現在登録しているメールアドレスをご入力ください。")
        if payload["current_email"] and not is_valid_email(payload["current_email"]):
            errors.append("現在登録メールアドレスの形式をご確認ください。")

    if procedure == "ログインに関するご相談":
        # メアドは任意。入力されている場合のみ形式チェック
        if payload["current_email"] and not is_valid_email(payload["current_email"]):
            errors.append("思い当たるメールアドレスの形式をご確認ください。")
        if not payload["notes"]:
            errors.append("お困りの状況をご入力ください。")

    return errors
