"""Google Sheets API連携モジュール。トレードログ・キャラ記憶・投稿ログの保存・取得を担当。"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv(
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "17y0Ds1AjtslH7EqZqTDhLzJV6WPXFKo5TKdBl-VW6XY",
)

TRADE_LOG_SHEET = "BULLトレードログ"
CHAR_MEMORY_SHEET = "キャラ記憶"
POST_LOG_SHEET = "投稿ログ"

TRADE_LOG_HEADERS = [
    "date", "day", "signal", "action", "price", "quantity",
    "realized_pnl", "unrealized_pnl", "total_value", "cash",
    "position_size", "vix", "nikkei", "cme_direction", "sp500_direction",
    "confidence", "screenshot_url", "memo", "created_at",
]

CHAR_MEMORY_HEADERS = [
    "date", "day", "event_type", "summary",
    "bullmin_emotion", "bullmin_intensity",
    "beardon_emotion", "beardon_intensity",
    "running_joke", "lesson", "future_reference", "created_at",
]

POST_LOG_HEADERS = [
    "date", "day", "title", "x_post", "short_dialogue", "note_body",
    "youtube_script", "next_hook",
    "posted_x", "posted_note", "posted_youtube",
    "x_url", "note_url", "youtube_url", "created_at",
]


def get_sheets_client():
    """Google Sheets API クライアントを返す。"""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        cred_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "credentials",
            "google_service_account.json",
        )
        if not os.path.exists(cred_path):
            raise FileNotFoundError(
                f"サービスアカウントJSONが見つかりません: {cred_path}\n"
                "環境変数 GOOGLE_SERVICE_ACCOUNT_JSON を設定するか、"
                "credentials/google_service_account.json を配置してください。"
            )
        creds = Credentials.from_service_account_file(cred_path, scopes=scopes)

    return gspread.authorize(creds)


def _get_or_create_sheet(spreadsheet, title: str, headers: list):
    """シートが存在しなければ作成し、ヘッダー行がなければ補完する。"""
    try:
        ws = spreadsheet.worksheet(title)
    except Exception:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.update("A1", [headers])
        return ws

    # 既存シートのヘッダー行を確認・補完
    first_row = ws.row_values(1)
    if not any(first_row):
        # 完全に空 → ヘッダーを挿入
        ws.insert_row(headers, index=1)
    elif first_row != headers:
        # ヘッダーが違う or 一部空 → 上書き
        ws.update("A1", [headers])

    return ws


def ensure_sheet_structure(spreadsheet_id: str | None = None) -> None:
    """必要な3シートとヘッダーを作成・確認する。"""
    sid = spreadsheet_id or SPREADSHEET_ID
    client = get_sheets_client()
    ss = client.open_by_key(sid)
    _get_or_create_sheet(ss, TRADE_LOG_SHEET, TRADE_LOG_HEADERS)
    _get_or_create_sheet(ss, CHAR_MEMORY_SHEET, CHAR_MEMORY_HEADERS)
    _get_or_create_sheet(ss, POST_LOG_SHEET, POST_LOG_HEADERS)


def _row_from_dict(headers: list, row: dict) -> list:
    return [str(row.get(h, "")) for h in headers]


def append_trade_log(row: dict) -> None:
    """BULLトレードログに1行追加する。APIエラー時は既存処理を止めない。"""
    try:
        row.setdefault("created_at", datetime.now().isoformat())
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, TRADE_LOG_SHEET, TRADE_LOG_HEADERS)
        ws.append_row(_row_from_dict(TRADE_LOG_HEADERS, row))
        logger.info("トレードログ保存完了")
    except Exception as e:
        print(f"[Sheets] トレードログ保存失敗（スキップ）: {e}")
        logger.error(f"トレードログ保存失敗（スキップ）: {e}")


def append_character_memory(row: dict) -> None:
    """キャラ記憶に1行追加する。APIエラー時は既存処理を止めない。"""
    try:
        row.setdefault("created_at", datetime.now().isoformat())
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, CHAR_MEMORY_SHEET, CHAR_MEMORY_HEADERS)
        ws.append_row(_row_from_dict(CHAR_MEMORY_HEADERS, row))
        logger.info("キャラ記憶保存完了")
    except Exception as e:
        print(f"[Sheets] キャラ記憶保存失敗（スキップ）: {e}")
        logger.error(f"キャラ記憶保存失敗（スキップ）: {e}")


def append_post_log(row: dict) -> None:
    """投稿ログに1行追加する。APIエラー時は既存処理を止めない。"""
    try:
        row.setdefault("created_at", datetime.now().isoformat())
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, POST_LOG_SHEET, POST_LOG_HEADERS)
        ws.append_row(_row_from_dict(POST_LOG_HEADERS, row))
        logger.info("投稿ログ保存完了")
    except Exception as e:
        print(f"[Sheets] 投稿ログ保存失敗（スキップ）: {e}")
        logger.error(f"投稿ログ保存失敗（スキップ）: {e}")


def _sheet_to_dicts(ws, limit: int) -> list:
    """シートの末尾 limit 行を辞書リストとして返す。ヘッダー重複に強い実装。"""
    all_values = ws.get_all_values()
    if not all_values:
        return []
    headers = all_values[0]
    data_rows = all_values[1:]
    if not data_rows:
        return []
    result = []
    for row in data_rows:
        # headers と row の長さを揃える
        row_padded = row + [""] * (len(headers) - len(row))
        d = {h: row_padded[i] for i, h in enumerate(headers) if h}
        result.append(d)
    return result[-limit:] if len(result) > limit else result


def fetch_recent_trade_logs(limit: int = 30) -> list:
    """直近のトレードログを取得する。失敗時は空リストを返す。"""
    try:
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, TRADE_LOG_SHEET, TRADE_LOG_HEADERS)
        return _sheet_to_dicts(ws, limit)
    except Exception as e:
        print(f"[Sheets] トレードログ取得失敗（スキップ）: {e}")
        logger.error(f"トレードログ取得失敗（スキップ）: {e}")
        return []


def fetch_recent_character_memory(limit: int = 20) -> list:
    """直近のキャラ記憶を取得する。失敗時は空リストを返す。"""
    try:
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, CHAR_MEMORY_SHEET, CHAR_MEMORY_HEADERS)
        return _sheet_to_dicts(ws, limit)
    except Exception as e:
        print(f"[Sheets] キャラ記憶取得失敗（スキップ）: {e}")
        logger.error(f"キャラ記憶取得失敗（スキップ）: {e}")
        return []


def fetch_recent_post_logs(limit: int = 10) -> list:
    """直近の投稿ログを取得する。失敗時は空リストを返す。"""
    try:
        client = get_sheets_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        ws = _get_or_create_sheet(ss, POST_LOG_SHEET, POST_LOG_HEADERS)
        return _sheet_to_dicts(ws, limit)
    except Exception as e:
        print(f"[Sheets] 投稿ログ取得失敗（スキップ）: {e}")
        logger.error(f"投稿ログ取得失敗（スキップ）: {e}")
        return []
