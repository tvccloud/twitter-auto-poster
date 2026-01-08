import os
import time
import random
import logging
import sys
import tweepy
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load credentials
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
    logging.error("Missing Twitter credentials. Exiting.")
    sys.exit(1)

# Twitter client
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True
)

BLOCKED = {
    "politics","election","government","minister",
    "bjp","congress","parliament","president",
    "religion","god","hindu","islam","christian",
    "temple","mosque","church","israel","palestine"
}

def is_safe(text):
    return not any(word in text.lower() for word in BLOCKED)

def get_trending_topics(limit=5):
    feed = feedparser.parse("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    topics = []
    for entry in feed.entries:
        title = entry.get("title", "")
        if title and is_safe(title):
            topics.append(title)
        if len(topics) >= limit:
            break
    return topics

TEMPLATES = [
    "{topic}. This is gaining attention today.",
    "A lot of people are discussing: {topic}",
    "Trending now: {topic}",
    "Seeing increased buzz around {topic}.",
    "{topic} is getting a lot of attention recently."
]

def generate_tweet(topic):
    return random.choice(TEMPLATES).format(topic=topic)[:270]

def generate_thread(topic):
    # Simple deterministic multi-tweet thread
    return [
        f"1/ {topic}",
        "2/ Here’s a quick breakdown of why this is trending.",
        "3/ It’s gaining attention due to recent developments and growing public interest.",
        "4/ More updates expected soon. Stay tuned."
    ]

def main():
    topics = get_trending_topics(10)
    if not topics:
        logging.info("No safe topics found.")
        return

    # pick 5 topics
    selected = topics[:5]

    # find the topic with the longest text
    long_topic = max(selected, key=len)

    for topic in selected:
        if topic == long_topic:
            # Create and post the thread
            thread_tweets = generate_thread(topic)
            reply_to = None
            for t in thread_tweets:
                resp = client.create_tweet(text=t, reply_to_tweet_id=reply_to)
                reply_to = resp["data"]["id"]
                logging.info("Thread segment posted.")
                time.sleep(random.randint(8, 15))
        else:
            # Normal tweet
            tweet = generate_tweet(topic)
            client.create_tweet(text=tweet)
            logging.info("Single tweet posted.")
            time.sleep(random.randint(10, 20))

if __name__ == "__main__":
    main()
