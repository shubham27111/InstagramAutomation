import os
import feedparser  # To parse RSS feeds
import requests  # To make HTTP requests for fetching URLs and posting to Instagram
from bs4 import BeautifulSoup  # To scrape and parse HTML for metadata like images
from dotenv import load_dotenv  # To load environment variables from a .env file
import openai  # To interact with OpenAI's GPT API
import json  # For working with JSON data
from datetime import datetime  # To handle timestamps for tracking when articles were last checked

# Load environment variables from the .env file
load_dotenv()

# Retrieve sensitive information like API keys from the environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # API key for OpenAI
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")  # Access token for Instagram API
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")  # Instagram account ID for posting

# Set the OpenAI API key to authenticate requests to OpenAI's GPT model
openai.api_key = OPENAI_API_KEY

# Initialize the last checked time to UTC for the first run (it will be updated after each article check)
LAST_CHECKED = datetime.utcnow()


def get_latest_articles(feed_url, last_checked):
    """
    Fetch the latest articles from the provided RSS feed URL.
    This function parses the RSS feed and filters articles that have been published since the last check.
    """
    feed = feedparser.parse(feed_url)  # Parse the RSS feed from the URL

    # Prepare a list to store news items
    news_items = []

    # Loop through each entry (article) in the RSS feed
    for entry in feed.entries:
        # Extract necessary details like title, link, published date, summary, and author
        news_item = {
            "title": entry.title,  # Article title
            "link": entry.link,  # URL of the article
            "published": entry.published,  # Date the article was published
            "summary": entry.summary,  # Summary of the article
            "author": entry.get("author", "Unknown"),  # Author's name (if available)
        }
        # Append the extracted news item to the list
        news_items.append(news_item)

    # Return the list of news items
    return news_items


def generate_caption(article_title, article_summary, article_url):
    """
    Generate an engaging Instagram caption using OpenAI API.
    The caption should summarize the article and include the link to it.
    """
    # Prepare a prompt for the GPT model to generate a caption
    prompt = f"Write an engaging 2-3 sentence Instagram caption for the article titled '{article_title}'. \
    The caption should briefly summarize the article and end with this link: {article_url}."

    # Call the OpenAI API to generate a response using the given prompt
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use the GPT-3.5 model for generating text
        messages=[{"role": "user", "content": prompt}]  # Pass the prompt to the model
    )
    
    # Return the generated caption from the response
    return response['choices'][0]['message']['content']


def fetch_thumbnail(article_url):
    """
    Fetch the thumbnail image URL from the article's Open Graph metadata.
    Open Graph meta tags are commonly used to define thumbnail images for articles.
    """
    # Make an HTTP GET request to fetch the article's HTML content
    response = requests.get(article_url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Try to find the Open Graph meta tag for the image
    thumbnail_url = soup.find("meta", property="og:image")
    
    # If the thumbnail exists, return its URL, else return None
    return thumbnail_url['content'] if thumbnail_url else None


def post_to_instagram(image_url, caption):
    """
    Publish an Instagram post using the Instagram Graph API.
    The post includes an image and a caption.
    """
    # Step 1: Upload media (image) to Instagram
    media_url = f"https://graph.facebook.com/v15.0/{IG_ACCOUNT_ID}/media"  # URL for media upload API
    media_payload = {
        "image_url": image_url,  # URL of the image to be uploaded
        "caption": caption,  # Caption for the Instagram post
        "access_token": IG_ACCESS_TOKEN  # Instagram access token for authentication
    }
    
    # Make a POST request to upload the media
    media_response = requests.post(media_url, data=media_payload)
    
    # Extract media ID from the response, which is required to publish the post
    media_id = media_response.json().get("id")
    
    # If no media ID is returned, print the error and return
    if not media_id:
        print("Error uploading media:", media_response.json())
        return

    # Step 2: Publish the media (image) to Instagram
    publish_url = f"https://graph.facebook.com/v15.0/{IG_ACCOUNT_ID}/media_publish"  # URL for media publishing API
    publish_payload = {
        "creation_id": media_id,  # ID of the media to be published
        "access_token": IG_ACCESS_TOKEN  # Instagram access token for authentication
    }
    
    # Make a POST request to publish the media
    publish_response = requests.post(publish_url, data=publish_payload)
    
    # If the status code is 200, the post is published successfully
    if publish_response.status_code == 200:
        print("Post published successfully!")
    else:
        print("Error publishing post:", publish_response.json())


def main():
    """
    Main function to handle the automation workflow for fetching articles, generating captions,
    and posting to Instagram.
    """
    global LAST_CHECKED  # Access the global variable for the last checked timestamp

    # RSS feed URL of the website (example: BBC News)
    feed_url = "http://feeds.bbci.co.uk/news/rss.xml"

    # Step 1: Get new articles from the RSS feed
    new_articles = get_latest_articles(feed_url, LAST_CHECKED)

    # Loop through each new article
    for article in new_articles:
        # Step 2: Generate a caption for the article using OpenAI's GPT model
        caption = generate_caption(article['title'], article['summary'], article['link'])

        # Step 3: Fetch the thumbnail image URL for the article
        image_url = fetch_thumbnail(article['link'])
        
        # If no thumbnail is found, print a message and continue to the next article
        if not image_url:
            print(f"No thumbnail found for article: {article['title']}")
            continue

        # Step 4: Post the image and caption to Instagram
        post_to_instagram(image_url, caption)

        # Only process one article per execution (break after first post)
        break

    # Update the LAST_CHECKED timestamp after processing the articles
    LAST_CHECKED = datetime.utcnow()


# Run the main function when the script is executed
if __name__ == "__main__":
    main()
