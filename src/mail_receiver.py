"""
メール受信モジュール
ユーザーが送った約定スクショメールを受け取り、画像を保存する

送信フォーマット:
  件名: BUY   （買い。口数・金額はシステムが自動計算）
  件名: SELL  （売り。口数はSTEP1で通知した推奨口数をシステムが使用）
  件名: HOLD  （様子見・取引なし）
  添付: 約定画面のスクリーンショット（PNG/JPG）
"""
import imaplib
import email
import email.header
import os
from datetime import date, datetime
from typing import Optional

import config

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SCREENSHOT_DIR = "screenshots"


def _decode_subject(subject_raw: str) -> str:
    parts = email.header.decode_header(subject_raw)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def parse_subject(subject: str) -> str:
    """
    件名から action を解析する。
    BUY  → "BUY"
    SELL → "SELL"
    HOLD → "HOLD"
    口数・金額はシステム側で計算するため、件名には action のみ。
    """
    upper = subject.strip().upper()
    for kw in ("BUY", "SELL", "HOLD"):
        if kw in upper:
            return kw
    return "HOLD"


def fetch_trade_screenshot(target_date: Optional[date] = None) -> Optional[dict]:
    """
    当日のスクショメールを受信BOXから探し、画像ファイルに保存する。

    Returns:
        {
            "action": "BUY" | "SELL" | "HOLD",
            "value": int,          # BUY→金額、SELL→口数、HOLD→0
            "screenshot": str,     # 保存した画像ファイルのパス（添付なければNone）
            "subject": str,
            "received_at": str,
        }
        見つからなければ None
    """
    if target_date is None:
        target_date = date.today()

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(config.EMAIL_FROM, config.EMAIL_PASSWORD)
    mail.select("INBOX")

    date_str = target_date.strftime("%d-%b-%Y")
    # 当日以降、件名に BUY / SELL / HOLD を含むメール
    _, msg_ids = mail.search(None, f'(SINCE "{date_str}")')

    found = None
    for msg_id in reversed(msg_ids[0].split()):
        _, data = mail.fetch(msg_id, "(RFC822)")
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        subject_raw = msg.get("Subject", "")
        subject = _decode_subject(subject_raw).strip().upper()

        # BUY / SELL / HOLD を含む件名のみ対象
        if not any(kw in subject for kw in ("BUY", "SELL", "HOLD")):
            continue

        action = parse_subject(subject)
        received_at = msg.get("Date", "")

        # 添付画像を探す
        screenshot_path = None
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype.startswith("image/"):
                ext = "png" if "png" in ctype else "jpg"
                filename = f"{target_date.isoformat()}_{action}.{ext}"
                screenshot_path = os.path.join(SCREENSHOT_DIR, filename)
                with open(screenshot_path, "wb") as f:
                    f.write(part.get_payload(decode=True))
                break

        found = {
            "action": action,
            "screenshot": screenshot_path,
            "subject": subject,
            "received_at": received_at,
        }
        break  # 最新1件だけ取得

    mail.logout()
    return found
