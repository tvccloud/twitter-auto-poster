import os
import time
import random
import logging
import sys
import tweepy
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load Twitter credentials
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
    logging.error("Missing Twitter credentials. Exiting.")
    sys.exit(1)

client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True
)

# Get crypto news only
def get_crypto_news(limit=10):
    feed = feedparser.parse(
        "https://news.google.com/rss/search?q=Bitcoin OR cryptocurrency OR crypto OR Ethereum&hl=en-IN&gl=IN&ceid=IN:en"
    )
    topics = []
    for entry in feed.entries:
        title = entry.get("title", "")
        if title:
            topics.append(title)

        if len(topics) >= limit:
            break

    return topics


def generate_crypto_tweet(topic):
    templates = [
        "🚀 {topic} — Crypto Twitter is buzzing.",
        "📈 {topic}. What’s your take?",
        "🔥 Trending in crypto: {topic}",
        "👀 Big update: {topic}",
        "⚡ Crypto alert: {topic}"
    ]

    base = random.choice(templates).format(topic=topic)

    # Add small uniqueness to avoid duplicate error
    unique_tag = f" #{int(time.time()) % 10000}"

    return (base + unique_tag)[:270]


def generate_crypto_thread(topic):
    unique_tag = f" #{int(time.time()) % 10000}"

    return [
        f"1/ {topic}{unique_tag}",
        "2/ Here’s why this matters in the crypto space.",
        "3/ Traders and long-term holders are watching closely.",
        "4/ The next 24 hours could be interesting.",
        "5/ Follow for daily Bitcoin & crypto updates."
    ]


def main():
    topics = get_crypto_news(10)

    if not topics:
        logging.info("No crypto topics found.")
        return

    selected = topics[:5]

    # Longest topic becomes thread
    long_topic = max(selected, key=len)

    for topic in selected:
        if topic == long_topic:
            thread = generate_crypto_thread(topic)
            reply_to = None
            for tweet in thread:
if reply_to is None:
    response = client.create_tweet(text=tweet)
else:
    response = client.create_tweet(
        text=tweet,
        in_reply_to_tweet_id=reply_to
    )
    reply_to = response["data"]["id"]
                logging.info("Thread part posted.")
                time.sleep(random.randint(8, 15))
        else:
            tweet = generate_crypto_tweet(topic)
            client.create_tweet(text=tweet)
            logging.info("Tweet posted.")
            time.sleep(random.randint(10, 20))


if __name__ == "__main__":
    main()
