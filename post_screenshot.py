"""
スクリーンショットをマスク処理してTwitterに投稿するスクリプト。

使い方:
  python post_screenshot.py                    # ファイル選択ダイアログ
  python post_screenshot.py <画像パス>          # ファイル指定
  python post_screenshot.py <画像パス> <キャプション>
"""
import json
import os
import sys

from PIL import Image, ImageDraw
from dotenv import load_dotenv

load_dotenv()

MASK_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "mask_config.json")


def load_mask_config() -> dict:
    if os.path.exists(MASK_CONFIG_PATH):
        with open(MASK_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"regions": [], "default_caption": "🐂 ブルみん×ベアドン 取引記録\n#日経4倍ブル #投資記録"}


def apply_masks(img: Image.Image, regions: list) -> Image.Image:
    """指定領域を黒く塗りつぶす。座標は画像サイズに対する割合（0.0〜1.0）。"""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for r in regions:
        x1, y1, x2, y2 = int(r["x1"] * w), int(r["y1"] * h), int(r["x2"] * w), int(r["y2"] * h)
        draw.rectangle([x1, y1, x2, y2], fill="black")
        print(f"  マスク適用: {r.get('name', '')} ({x1},{y1})-({x2},{y2})")
    return img


def post_to_twitter(image_path: str, caption: str) -> str:
    import tweepy

    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError("Twitter APIキーが設定されていません。.envファイルを確認してください。")

    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)
    media = api_v1.media_upload(filename=image_path)

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    response = client.create_tweet(text=caption, media_ids=[media.media_id])
    return f"https://x.com/i/web/status/{response.data['id']}"


def pick_file() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="スクリーンショットを選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        root.destroy()
        return path
    except Exception:
        print("ファイルパスを引数で指定してください: python post_screenshot.py <path>")
        sys.exit(1)


def main():
    screenshot_path = sys.argv[1] if len(sys.argv) > 1 else pick_file()
    if not screenshot_path:
        print("キャンセルしました。")
        return

    if not os.path.exists(screenshot_path):
        print(f"ファイルが見つかりません: {screenshot_path}")
        sys.exit(1)

    config = load_mask_config()

    # マスク処理
    print(f"\n画像を読み込み中: {screenshot_path}")
    img = Image.open(screenshot_path).convert("RGB")
    print(f"サイズ: {img.size[0]}x{img.size[1]}")

    img = apply_masks(img, config.get("regions", []))

    base, ext = os.path.splitext(screenshot_path)
    masked_path = base + "_masked" + (ext or ".png")
    img.save(masked_path)
    print(f"マスク済み画像を保存: {masked_path}")

    # キャプション
    if len(sys.argv) > 2:
        caption = sys.argv[2]
    else:
        default = config.get("default_caption", "🐂 ブルみん×ベアドン 取引記録\n#日経4倍ブル #投資記録")
        print(f"\nデフォルトキャプション:\n{default}")
        print("\nそのまま使う場合はEnter、変更する場合は入力してください:")
        user_input = input().strip()
        caption = user_input if user_input else default

    # 確認
    print(f"\n--- 投稿内容 ---")
    print(f"画像: {masked_path}")
    print(f"キャプション:\n{caption}")
    print(f"---------------")
    print("\nTwitterに投稿しますか？ (y/n): ", end="")
    if input().strip().lower() != "y":
        print("キャンセルしました。")
        return

    print("投稿中...")
    url = post_to_twitter(masked_path, caption)
    print(f"\n投稿完了！\n{url}")


if __name__ == "__main__":
    main()
