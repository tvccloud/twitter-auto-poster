import os
import time
import random
import logging
import sys
import tweepy
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Load Twitter credentials ---
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
    logging.error("Missing Twitter credentials. Exiting.")
    sys.exit(1)

# --- Create client ---
try:
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
        wait_on_rate_limit=True
    )
except Exception as e:
    logging.exception("Failed to create Twitter client: %s", e)
    sys.exit(1)

# get authenticated user id once (used to fetch recent tweets)
try:
    me = client.get_me()
    USER_ID = me.data["id"]
    logging.info("Authenticated as user id: %s", USER_ID)
except Exception:
    USER_ID = None
    logging.warning("Could not fetch authenticated user id; recent-tweet duplicate check will be limited.")

# --- Helpers ---
BLOCKED = {
    "politics","election","government","minister",
    "bjp","congress","parliament","president",
    "religion","god","hindu","islam","christian",
    "temple","mosque","church","israel","palestine"
}

CRYPTO_KEYWORDS = {"bitcoin", "btc", "crypto", "cryptocurrency", "ethereum", "eth", "blockchain", "defi", "nft", "nfts"}

def is_safe(text):
    t = (text or "").lower()
    if any(b in t for b in BLOCKED):
        return False
    return True

def is_crypto_topic(text):
    t = (text or "").lower()
    return any(k in t for k in CRYPTO_KEYWORDS)

def get_crypto_news(limit=10):
    url = "https://news.google.com/rss/search?q=Bitcoin OR cryptocurrency OR crypto OR Ethereum&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    topics = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        if title and is_safe(title) and is_crypto_topic(title):
            topics.append(title)
        if len(topics) >= limit:
            break
    # dedupe preserving order
    seen = set()
    unique = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique

def fetch_recent_texts(limit=50):
    """Return list of recently posted tweet texts (most recent first)."""
    if not USER_ID:
        return []
    try:
        resp = client.get_users_tweets(USER_ID, max_results=limit, tweet_fields=["text"])
        texts = []
        if resp and getattr(resp, "data", None):
            for item in resp.data:
                txt = item.get("text") if isinstance(item, dict) else getattr(item, "text", "")
                if txt:
                    texts.append(txt.strip())
        return texts
    except Exception as e:
        logging.warning("Could not fetch recent tweets: %s", e)
        return []

def make_unique_text(base_text, recent_texts):
    """If base_text matches a recent tweet, mutate it with safe variations until unique."""
    attempt = 0
    max_attempts = 6
    hashtags = ["#Bitcoin","#BTC","#Crypto","#ETH","#Blockchain"]
    commentary = [
        "Market watching closely.",
        "Big conversations happening.",
        "Volatility incoming?",
        "Traders paying attention.",
        "Momentum building."
    ]

    new_text = base_text
    while attempt < max_attempts:
        # compare trimmed identical strings
        if not any(new_text.strip() == r.strip() for r in recent_texts):
            return new_text
        # mutate: add commentary or hashtag (prefer readability)
        suffix = " " + random.choice(commentary) + " " + random.choice(hashtags)
        # if already long, replace last 30 chars
        if len(base_text) + len(suffix) > 270:
            new_text = (base_text[:230] + suffix)[:270]
        else:
            new_text = (base_text + suffix)[:270]
        attempt += 1
        # refresh recent_texts occasionally to pick up newly posted tweets in this run
        if attempt % 3 == 0:
            recent_texts = fetch_recent_texts(50)
    # fallback: append a small unique token (very last resort)
    return (base_text + " #" + str(int(time.time()) % 10000))[:270]

def generate_crypto_tweet(topic):
    templates = [
        "🚀 {topic}",
        "📈 {topic}",
        "🔥 {topic}",
        "⚡ {topic}",
        "👀 {topic}"
    ]
    commentary = [
        "Market watching closely.",
        "Big conversations happening.",
        "Volatility incoming?",
        "Traders paying attention.",
        "Momentum building."
    ]
    hashtags = ["#Bitcoin","#BTC","#Crypto","#Ethereum","#Blockchain"]

    tweet = random.choice(templates).format(topic=topic)
    tweet += " " + random.choice(commentary)
    tweet += " " + random.choice(hashtags)
    return tweet[:270]

def generate_crypto_thread(topic):
    hashtags = ["#Bitcoin","#BTC","#Crypto"]
    thread = [
        f"1/ {topic}",
        "2/ Here’s what’s happening in the market.",
        "3/ Traders and long-term holders are reacting.",
        "4/ Watch volatility in the next 24 hours.",
        f"5/ Stay updated daily. {random.choice(hashtags)}"
    ]
    return thread

# --- Posting helpers with duplicate-safety ---
def post_tweet_unique(text):
    recent = fetch_recent_texts(50)
    text_unique = make_unique_text(text, recent)
    try:
        resp = client.create_tweet(text=text_unique)
        tid = None
        if getattr(resp, "data", None):
            tid = resp.data.get("id")
        logging.info("Tweet posted. id: %s", tid)
        return tid
    except tweepy.errors.Forbidden as e:
        # handle duplicate error by forcing uniqueness fallback
        logging.warning("Forbidden while posting (likely duplicate). Applying forced uniqueness: %s", e)
        forced = (text + " #" + str(int(time.time()) % 10000))[:270]
        try:
            resp = client.create_tweet(text=forced)
            tid = resp.data.get("id") if getattr(resp, "data", None) else None
            logging.info("Tweet posted after forced uniqueness. id: %s", tid)
            return tid
        except Exception as ee:
            logging.exception("Failed to post tweet after forced uniqueness: %s", ee)
            return None
    except Exception as e:
        logging.exception("Failed to post tweet: %s", e)
        return None

# --- Main flow ---
def main():
    topics = get_crypto_news(limit=10)
    if not topics:
        logging.info("No crypto topics found. Exiting.")
        return

    selected = topics[:5]
    # choose longest for thread
    long_topic = max(selected, key=len)

    for topic in selected:
        if topic == long_topic:
            thread = generate_crypto_thread(topic)
            reply_to = None
            for part in thread:
                # ensure each part is unique relative to recent tweets
                part_text = make_unique_text(part, fetch_recent_texts(50))
                if reply_to is None:
                    resp = post_tweet_unique(part_text)
                else:
                    # post reply in thread
                    try:
                        resp = client.create_tweet(text=part_text, in_reply_to_tweet_id=reply_to)
                        resp_id = resp.data.get("id") if getattr(resp, "data", None) else None
                        resp = resp_id
                        logging.info("Thread part posted. id: %s", resp)
                    except tweepy.errors.Forbidden:
                        # fallback: try posting with uniqueness and link to previous
                        forced = (part_text + " #" + str(int(time.time()) % 10000))[:270]
                        try:
                            resp = client.create_tweet(text=forced, in_reply_to_tweet_id=reply_to)
                            resp = resp.data.get("id") if getattr(resp, "data", None) else None
                            logging.info("Thread part posted after fallback. id: %s", resp)
                        except Exception as e:
                            logging.exception("Failed thread post: %s", e)
                            resp = None
                    except Exception as e:
                        logging.exception("Failed thread post: %s", e)
                        resp = None

                # normalize reply_to for next iteration
                if isinstance(resp, dict):
                    reply_to = resp.get("id")
                else:
                    reply_to = resp
                time.sleep(random.randint(8, 15))
        else:
            tweet = generate_crypto_tweet(topic)
            post_tweet_unique(tweet)
            time.sleep(random.randint(10, 20))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("Unhandled exception: %s", e)
        sys.exit(1)
