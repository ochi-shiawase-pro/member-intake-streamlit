from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(value.strip()))


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
        if payload["target_email"] and payload["confirm_email"] and payload["target_email"] != payload["confirm_email"]:
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
        if payload["target_email"] and payload["confirm_email"] and payload["target_email"] != payload["confirm_email"]:
            errors.append("確認用メールアドレスが一致していません。")

    if procedure == "ご利用停止":
        if not payload["current_email"]:
            errors.append("現在登録しているメールアドレスをご入力ください。")
        if payload["current_email"] and not is_valid_email(payload["current_email"]):
            errors.append("現在登録メールアドレスの形式をご確認ください。")

    return errors
