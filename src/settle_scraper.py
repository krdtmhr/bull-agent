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
MAIL_WAIT_SEC = 45  # 認証メール到着を待つ最大秒数


def _get_emoji_names_from_gmail() -> tuple[str, str]:
    """Gmailから楽天証券の2FA認証メールを読み、絵柄名を返す。"""
    import datetime as dt
    gmail_user = config.GMAIL_2FA_USER
    gmail_pass = config.GMAIL_2FA_PASSWORD
    print(f"  IMAP接続先: {gmail_user}")

    deadline = time.time() + MAIL_WAIT_SEC
    today_str = dt.date.today().strftime("%d-%b-%Y")
    while time.time() < deadline:
        try:
            conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            conn.login(gmail_user, gmail_pass)
            conn.select("INBOX")
            _, ids = conn.search(None, f'(FROM "service@rakuten-sec.co.jp" SINCE {today_str})')
            print(f"  メール検索結果件数: {len(ids[0].split()) if ids[0] else 0}")
            if ids[0]:
                msg_list = ids[0].split()
                # 最新から順に2FA認証メール（絵文字コード入り）を探す
                for i, msg_id in enumerate(reversed(msg_list)):
                    _, data = conn.fetch(msg_id, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    body_plain = ""
                    body_html = ""
                    parts_info = []
                    for part in msg.walk():
                        ct = part.get_content_type()
                        charset = part.get_content_charset() or "iso-2022-jp"
                        parts_info.append(ct)
                        raw = part.get_payload(decode=True)
                        if raw is None:
                            continue
                        if ct == "text/plain" and not body_plain:
                            try:
                                body_plain = raw.decode(charset, errors="replace")
                            except Exception:
                                body_plain = raw.decode("utf-8", errors="replace")
                        elif ct == "text/html" and not body_html:
                            try:
                                body_html = raw.decode(charset, errors="replace")
                            except Exception:
                                body_html = raw.decode("utf-8", errors="replace")
                    body = body_plain or body_html
                    if i == 0:
                        print(f"  [DBG] MIME: {parts_info}")
                        print(f"  [DBG] body先頭100文字: {repr(body[:100])}")
                    m1 = re.search(r'絵文字[１1]の内容[\s　]*(\S+)', body)
                    m2 = re.search(r'絵文字[２2]の内容[\s　]*(\S+)', body)
                    if m1 and m2:
                        print(f"  2FA認証メール発見: {m1.group(1)} / {m2.group(1)}")
                        conn.logout()
                        return m1.group(1), m2.group(1)
                    print(f"  メールID {msg_id}: 絵文字コードなし（スキップ）")
            conn.logout()
        except Exception as e:
            print(f"  メール確認エラー: {e}")
        time.sleep(5)
    raise TimeoutError(f"{MAIL_WAIT_SEC}秒待っても認証メールが届きませんでした")


def _build_emoji_map_from_page(page) -> dict:
    """
    altFlg=1 + eventType=init でページ再送信し、emojiAltClick の onclick 属性から
    {絵柄名: index文字列} のマッピングを構築する。
    成功時は dict（空の可能性あり）、失敗時は {} を返す。
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    try:
        page.evaluate("document.querySelector('[name=altFlg]').value = '1'")
        page.evaluate("document.querySelector('[name=eventType]').value = 'init'")
        page.evaluate("SotpLoginForm.submit()")
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        print(f"  altFlg=1再送信失敗: {e}")
        return {}

    page.screenshot(path="screenshots/rakuten_2fa_alt.png")
    print(f"  altFlg=1ページURL: {page.url}")

    # emojiAltClick('emoji_N', 'N', '...gif', '絵柄名') からマッピングを抽出
    emoji_map = page.evaluate(r"""
        () => {
            const buttons = document.querySelectorAll('button[id^="emoji_"]');
            const map = {};
            buttons.forEach(btn => {
                const oc = btn.getAttribute('onclick') || '';
                const m = oc.match(/emojiAltClick\([^,]+,\s*'(\d+)',[^,]+,\s*'([^']+)'\)/);
                if (m) map[m[2]] = m[1];
            });
            return map;
        }
    """)
    print(f"  絵文字マッピング(altFlg=1): {emoji_map}")
    return emoji_map


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

    page.locator('input[type="password"]').first.fill(password)
    page.screenshot(path="screenshots/rakuten_login_filled.png")
    print("  フィールド入力後 スクショ保存")

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

    # ② ログイン後リダイレクト待ち
    try:
        page.wait_for_url("**/member.rakuten-sec.co.jp/**", timeout=15000)
    except PWTimeout:
        print(f"  ログイン後URL（遷移なし）: {page.url}")
        return True

    # ③ 2FAページか確認
    page.screenshot(path="screenshots/rakuten_2fa.png")
    print(f"  2FAページURL: {page.url}")

    if page.locator('button[id^="emoji_"]').count() == 0:
        print("  2FAなし、ダッシュボードへ遷移済み")
        return True

    print("  2FAページ検出: 絵柄選択が必要")

    # HTMLソース保存（デバッグ用）
    with open("screenshots/rakuten_2fa_source.html", "w", encoding="utf-8") as f:
        f.write(page.content())

    # ④ altFlg=1 で再送信して絵柄名→インデックスのマッピングを取得
    emoji_map = _build_emoji_map_from_page(page)

    # ⑤ 新しい認証メールから絵柄名を取得（altFlg=1再送後のメール）
    emoji1, emoji2 = _get_emoji_names_from_gmail()
    print(f"  認証絵柄: {emoji1} → {emoji2}")

    # ⑥ 絵柄をクリック
    if emoji_map:
        for emoji in (emoji1, emoji2):
            idx = emoji_map.get(emoji)
            if idx is None:
                available = list(emoji_map.keys())
                raise ValueError(
                    f"絵柄「{emoji}」がマッピングに見つかりません。利用可能: {available}"
                )
            page.click(f'#emoji_{idx}', timeout=3000)
            print(f"  絵柄「{emoji}」クリック完了 (index={idx})")
    else:
        # フォールバック: emojiAltClickが使えない場合、HTMLソースを保存して失敗
        with open("screenshots/rakuten_2fa_alt_source.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        raise ValueError(
            "altFlg=1でのマッピング取得失敗。"
            "rakuten_2fa_alt_source.html を確認してください。"
        )

    # ⑦ 認証ボタンをクリック
    page.locator('input[value="認証する"]').click(timeout=5000)
    page.wait_for_load_state("networkidle", timeout=15000)

    page.screenshot(path="screenshots/rakuten_2fa_after.png")
    print(f"  2FA認証後URL: {page.url}")
    return True


def _get_fund_settlement(page) -> int | None:
    """投信取引履歴から直近の解約受取金額を取得する。"""
    page.screenshot(path="screenshots/rakuten_after_login.png")
    print(f"  ログイン後URL: {page.url}")

    for link_text in ("取引履歴", "投資信託", "投信", "保有商品"):
        try:
            page.get_by_text(link_text, exact=False).first.click(timeout=5000)
            page.wait_for_load_state("networkidle", timeout=10000)
            break
        except Exception:
            continue
    page.wait_for_load_state("networkidle", timeout=15000)

    os.makedirs("screenshots", exist_ok=True)
    page.screenshot(path="screenshots/rakuten_history.png")
    print("  デバッグ用スクショ保存: screenshots/rakuten_history.png")

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
