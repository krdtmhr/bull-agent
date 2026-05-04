"""
楽天証券にログインして投信の直近約定金額を取得する。
2FA: メール認証（絵柄選択）をGmailから自動解析。
最大2回試行（3回でロック）。
"""
import imaplib
import email
import re
import time
import os

import config

MAX_ATTEMPTS = 2
MAIL_WAIT_SEC = 30  # 認証メール到着を待つ最大秒数


def _get_emoji_names_from_gmail() -> tuple[str, str]:
    """Gmailから楽天証券の2FA認証メールを読み、絵柄名を返す。"""
    deadline = time.time() + MAIL_WAIT_SEC
    while time.time() < deadline:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(config.EMAIL_FROM, config.EMAIL_PASSWORD)
            mail.select("INBOX")
            _, ids = mail.search(None, '(FROM "rakuten-sec.co.jp" UNSEEN)')
            if ids[0]:
                msg_id = ids[0].split()[-1]
                _, data = mail.fetch(msg_id, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
                mail.logout()
                m1 = re.search(r'絵文字[１1]の内容[\s　]*(\S+)', body)
                m2 = re.search(r'絵文字[２2]の内容[\s　]*(\S+)', body)
                if m1 and m2:
                    return m1.group(1), m2.group(1)
        except Exception as e:
            print(f"メール確認エラー: {e}")
        time.sleep(5)
    raise TimeoutError(f"{MAIL_WAIT_SEC}秒待っても認証メールが届きませんでした")


def _do_login(page, login_id: str, password: str) -> bool:
    """ログイン＋2FA実行。成功したらTrue。"""
    from playwright.sync_api import TimeoutError as PWTimeout

    # ① ID・パスワードでログイン
    page.goto("https://www.rakuten-sec.co.jp/ITS/V_ACT_Login.html", timeout=20000)
    page.wait_for_load_state("networkidle", timeout=15000)
    os.makedirs("screenshots", exist_ok=True)
    page.screenshot(path="screenshots/rakuten_login.png")
    print("  ログインページ スクショ保存")

    # ログインID: 検索バー(rsearchInput)を除いた最初のテキストフィールド
    filled = False
    for id_sel in (
        'input[type="text"]:not([id="rsearchInput"])',
        'input[type="text"]:not([class*="search"])',
        'form input[type="text"]',
    ):
        try:
            page.locator(id_sel).first.fill(login_id, timeout=5000)
            filled = True
            print(f"  ログインIDフィールド入力成功: {id_sel}")
            break
        except Exception:
            continue
    if not filled:
        raise RuntimeError("ログインIDフィールドが見つかりませんでした")
    # パスワード: type="password" のフィールド
    page.locator('input[type="password"]').first.fill(password)
    # 入力後スクショ（フィールドに値が入ったか確認用）
    page.screenshot(path="screenshots/rakuten_login_filled.png")
    print("  フィールド入力後 スクショ保存")

    # ログインボタンをクリック
    for btn_sel in (
        'button#login-btn',
        'button[type="submit"]',
        'button:has-text("ログイン")',
    ):
        try:
            page.click(btn_sel, timeout=5000)
            break
        except Exception:
            continue

    # ② 2FAページ待ち
    try:
        page.wait_for_url("**/login_add**", timeout=15000)
    except PWTimeout:
        # 2FAなしで直接ログインできた場合
        return True

    # ③ 2FAページのスクショ保存（デバッグ用）
    page.screenshot(path="screenshots/rakuten_2fa.png")
    print("  2FAページ スクショ保存")

    # 認証メールから絵柄名を取得
    emoji1, emoji2 = _get_emoji_names_from_gmail()
    print(f"  認証絵柄: {emoji1} → {emoji2}")

    # ④ 絵柄をクリック（alt属性で探す）
    for emoji in (emoji1, emoji2):
        clicked = False
        for selector in (
            f'img[alt="{emoji}"]',
            f'[title="{emoji}"]',
            f'[aria-label="{emoji}"]',
            f'[data-name="{emoji}"]',
        ):
            try:
                page.click(selector, timeout=3000)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            raise ValueError(f"絵柄「{emoji}」がページ上で見つかりませんでした")

    # ⑤ 認証ボタンをクリック
    page.click('input[type="submit"], button:has-text("認証する")', timeout=5000)
    page.wait_for_load_state("networkidle", timeout=15000)
    return True


def _get_fund_settlement(page) -> int | None:
    """投信取引履歴から直近の解約受取金額を取得する。"""
    from playwright.sync_api import TimeoutError as PWTimeout

    # ログイン後トップページのスクショ
    page.screenshot(path="screenshots/rakuten_after_login.png")
    print(f"  ログイン後URL: {page.url}")

    # 投信取引履歴リンクをクリックして辿る
    for link_text in ("取引履歴", "投資信託", "投信", "保有商品"):
        try:
            page.get_by_text(link_text, exact=False).first.click(timeout=5000)
            page.wait_for_load_state("networkidle", timeout=10000)
            break
        except Exception:
            continue
    page.wait_for_load_state("networkidle", timeout=15000)

    # デバッグ用スクリーンショット保存
    os.makedirs("screenshots", exist_ok=True)
    page.screenshot(path="screenshots/rakuten_history.png")
    print("  デバッグ用スクショ保存: screenshots/rakuten_history.png")

    # ページ上のテキストから解約受取金額を探す
    # 「解約」「受取」「金額」などのキーワード周辺の数字を取得
    content = page.content()
    patterns = [
        r'受取金額[^\d]*([0-9,]+)',
        r'解約金額[^\d]*([0-9,]+)',
        r'約定金額[^\d]*([0-9,]+)',
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            amount = int(m.group(1).replace(",", ""))
            print(f"  約定金額検出: ¥{amount:,}")
            return amount

    print("  ページ内容から金額を取得できませんでした。スクショを確認してください。")
    return None


def fetch_settlement_amount() -> int | None:
    """
    楽天証券にログインして直近の投信解約受取金額を返す。
    失敗時は None を返す（口座ロック防止のため最大2回）。
    """
    from playwright.sync_api import sync_playwright

    login_id = os.environ.get("RAKUTEN_LOGIN_ID", "")
    password = os.environ.get("RAKUTEN_PASSWORD", "")

    if not login_id or not password:
        print("RAKUTEN_LOGIN_ID / RAKUTEN_PASSWORD が未設定のためスキップ")
        return None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"楽天ログイン試行 {attempt}/{MAX_ATTEMPTS}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                _do_login(page, login_id, password)
                amount = _get_fund_settlement(page)
                browser.close()
                if amount:
                    return amount
        except Exception as e:
            print(f"  試行 {attempt} 失敗: {e}")
            if attempt == MAX_ATTEMPTS:
                print("  最大試行回数に達しました。口座ロック防止のため中止します。")
    return None
