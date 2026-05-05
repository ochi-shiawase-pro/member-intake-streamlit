# 情報配信ログイン登録・変更受付

Streamlit で動かす受付サイトのたたき台です。

## できること

- 新規登録
- 登録内容の変更
- ご利用停止

の 3 種類の受付を行い、Google Workspace のスプレッドシート `億万長者リスト` の `受付一覧` シートへ保存します。

Ghost への反映はこの段階では手動です。
（※任意で、Secrets に Ghost Admin API を設定すると「新規登録」「登録内容の変更」は送信と同時に自動反映できます。）

## ファイル構成

```text
member_intake_streamlit/
  app.py
  requirements.txt
  README.md
  .streamlit/
    secrets.toml.example
  src/
    form_fields.py
    sheets_repository.py
    ui_text.py
    validators.py
```

## 次にやること

### 1. スプレッドシート側

- `億万長者リスト` を開く
- `受付一覧` シートを作る
- 1 行目に見出しを入れる

### 2. サービスアカウント共有

- 今使っているサービスアカウントのメールアドレスを確認する
- `億万長者リスト` をそのサービスアカウントに `編集者` 共有する

### 3. Streamlit Secrets

`.streamlit/secrets.toml.example` を見ながら、Streamlit Cloud の Secrets に設定する

必要な値:

- `type`
- `project_id`
- `private_key_id`
- `private_key`
- `client_email`
- `client_id`
- `client_x509_cert_url`
- `spreadsheet_name`
- `worksheet_name`

任意（Ghost へ自動反映したい場合）:

- `ghost_admin_api_url`
- `ghost_admin_api_key`
- `ghost_admin_api_version`（未指定なら `v5.0`）

## ローカル実行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## LINE で案内するときの注意

LINE 内ブラウザでは次の画面に進めないことがあるため、案内文に以下を入れるのがおすすめです。

```text
入力ページが開いたら、Safari または Google Chrome で開き直してご利用ください。
LINE内ブラウザでは正しく動作しないことがあります。
```
