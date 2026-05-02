import tweepy
import config


def _client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=config.TWITTER_API_KEY,
        consumer_secret=config.TWITTER_API_SECRET,
        access_token=config.TWITTER_ACCESS_TOKEN,
        access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET,
    )


def post_morning_analysis(text: str) -> str:
    """Post morning analysis tweet. Returns tweet URL."""
    response = _client().create_tweet(text=text)
    tweet_id = response.data["id"]
    return f"https://x.com/i/web/status/{tweet_id}"


def post_with_image(text: str, image_path: str) -> str:
    """Post tweet with image. Returns tweet URL."""
    auth = tweepy.OAuth1UserHandler(
        config.TWITTER_API_KEY,
        config.TWITTER_API_SECRET,
        config.TWITTER_ACCESS_TOKEN,
        config.TWITTER_ACCESS_TOKEN_SECRET,
    )
    api_v1 = tweepy.API(auth)
    media = api_v1.media_upload(filename=image_path)

    response = _client().create_tweet(
        text=text,
        media_ids=[media.media_id],
    )
    tweet_id = response.data["id"]
    return f"https://x.com/i/web/status/{tweet_id}"
