"""
Social Media Publishers for Watchdog Nepal
============================================
Handles publishing approved posts to Instagram, Facebook, and Twitter/X.
All API credentials are loaded from environment variables.
"""
import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_env(key, default=''):
    return os.environ.get(key, default)


# ── Instagram Publisher ──────────────────────────────────────────────
def publish_to_instagram(post):
    """
    Publishes an image or reel to Instagram via the Graph API.
    Requires: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_CREATOR_ACCOUNT_ID
    
    Returns:
        tuple: (success: bool, post_id_or_error: str)
    """
    access_token = _get_env('INSTAGRAM_ACCESS_TOKEN')
    account_id = _get_env('INSTAGRAM_CREATOR_ACCOUNT_ID')
    
    if not access_token or not account_id:
        return False, "Instagram credentials not configured."
    
    try:
        base_url = f"https://graph.facebook.com/v19.0/{account_id}"
        
        if post.is_image and post.branded_image:
            # Step 1: Create media container
            image_url = f"{settings.MEDIA_URL}{post.branded_image.name}"
            # Instagram needs a publicly accessible URL
            full_image_url = f"https://watchdognepal.com{image_url}"
            
            container_response = requests.post(
                f"{base_url}/media",
                data={
                    'image_url': full_image_url,
                    'caption': post.caption or post.title,
                    'access_token': access_token,
                }
            )
            container_data = container_response.json()
            
            if 'id' not in container_data:
                return False, f"Container creation failed: {container_data.get('error', {}).get('message', str(container_data))}"
            
            container_id = container_data['id']
            
        elif post.is_reel and post.video_file:
            full_video_url = f"https://watchdognepal.com{settings.MEDIA_URL}{post.video_file.name}"
            
            container_response = requests.post(
                f"{base_url}/media",
                data={
                    'media_type': 'REELS',
                    'video_url': full_video_url,
                    'caption': post.caption or post.title,
                    'access_token': access_token,
                }
            )
            container_data = container_response.json()
            
            if 'id' not in container_data:
                return False, f"Reel container failed: {container_data.get('error', {}).get('message', str(container_data))}"
            
            container_id = container_data['id']
        else:
            return False, "No publishable media found."
        
        # Step 2: Publish the container
        publish_response = requests.post(
            f"{base_url}/media_publish",
            data={
                'creation_id': container_id,
                'access_token': access_token,
            }
        )
        publish_data = publish_response.json()
        
        if 'id' in publish_data:
            return True, publish_data['id']
        else:
            return False, f"Publish failed: {publish_data.get('error', {}).get('message', str(publish_data))}"
            
    except Exception as e:
        logger.exception("Instagram publish error")
        return False, str(e)


# ── Facebook Publisher ───────────────────────────────────────────────
def publish_to_facebook(post):
    """
    Publishes a post to a Facebook Page.
    Requires: FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID
    
    Returns:
        tuple: (success: bool, post_id_or_error: str)
    """
    access_token = _get_env('FACEBOOK_PAGE_ACCESS_TOKEN')
    page_id = _get_env('FACEBOOK_PAGE_ID')
    
    if not access_token or not page_id:
        return False, "Facebook credentials not configured."
    
    try:
        base_url = f"https://graph.facebook.com/v19.0/{page_id}"
        
        if post.is_image and post.branded_image:
            with open(post.branded_image.path, 'rb') as img_file:
                response = requests.post(
                    f"{base_url}/photos",
                    data={
                        'caption': post.caption or post.title,
                        'access_token': access_token,
                    },
                    files={'source': img_file}
                )
        elif post.is_reel and post.video_file:
            with open(post.video_file.path, 'rb') as vid_file:
                response = requests.post(
                    f"{base_url}/videos",
                    data={
                        'description': post.caption or post.title,
                        'access_token': access_token,
                    },
                    files={'source': vid_file}
                )
        else:
            # Text-only post
            response = requests.post(
                f"{base_url}/feed",
                data={
                    'message': f"{post.title}\n\n{post.caption}",
                    'access_token': access_token,
                }
            )
        
        data = response.json()
        if 'id' in data or 'post_id' in data:
            return True, data.get('id') or data.get('post_id')
        else:
            return False, f"Facebook error: {data.get('error', {}).get('message', str(data))}"
    
    except Exception as e:
        logger.exception("Facebook publish error")
        return False, str(e)


# ── Twitter/X Publisher ──────────────────────────────────────────────
def publish_to_twitter(post):
    """
    Publishes a post to Twitter/X using Tweepy (OAuth 1.0a).
    Requires: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
    
    Returns:
        tuple: (success: bool, tweet_id_or_error: str)
    """
    api_key = _get_env('TWITTER_API_KEY')
    api_secret = _get_env('TWITTER_API_SECRET')
    access_token = _get_env('TWITTER_ACCESS_TOKEN')
    access_secret = _get_env('TWITTER_ACCESS_TOKEN_SECRET')
    
    if not all([api_key, api_secret, access_token, access_secret]):
        return False, "Twitter credentials not configured."
    
    try:
        import tweepy
        
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        
        # For media uploads, we need the v1.1 API
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        
        media_ids = []
        
        if post.is_image and post.branded_image:
            media = api.media_upload(post.branded_image.path)
            media_ids.append(media.media_id)
        elif post.is_reel and post.video_file:
            media = api.media_upload(
                post.video_file.path,
                media_category='tweet_video'
            )
            media_ids.append(media.media_id)
        
        # Create tweet
        tweet_text = post.caption or post.title
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        response = client.create_tweet(
            text=tweet_text,
            media_ids=media_ids if media_ids else None
        )
        
        if response.data:
            return True, str(response.data['id'])
        else:
            return False, "Tweet creation returned no data."
    
    except Exception as e:
        logger.exception("Twitter publish error")
        return False, str(e)


# ── Unified Publisher ────────────────────────────────────────────────
def publish_post(post):
    """
    Publishes a post to all configured platforms.
    
    Args:
        post: SocialPost instance with status='approved'
    
    Returns:
        tuple: (success: bool, error: str)
    """
    if not post.is_publishable:
        return False, "Post has no publishable media."
    
    errors = []
    
    # Instagram
    ig_success, ig_result = publish_to_instagram(post)
    if ig_success:
        post.instagram_post_id = ig_result
    else:
        errors.append(f"Instagram: {ig_result}")
    
    # Facebook
    fb_success, fb_result = publish_to_facebook(post)
    if fb_success:
        post.facebook_post_id = fb_result
    else:
        errors.append(f"Facebook: {fb_result}")
    
    # Twitter
    tw_success, tw_result = publish_to_twitter(post)
    if tw_success:
        post.twitter_post_id = tw_result
    else:
        errors.append(f"Twitter: {tw_result}")
    
    if errors:
        post.publish_errors = "\n".join(errors)
    
    # Mark as published if at least one platform succeeded
    if ig_success or fb_success or tw_success:
        post.mark_published()
        return True, ""
    else:
        post.save()
        return False, "; ".join(errors)
