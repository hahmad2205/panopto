import json

from datetime import date
from decimal import Decimal
from json import JSONEncoder

from apify_client import ApifyClient
from decouple import config

from supabase_client import supabase_client
from utils import parse_datetime


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            encoded_obj = str(obj)
        elif isinstance(obj, date):
            encoded_obj = obj.isoformat()
        else:
            encoded_obj = super().default(obj)

        return encoded_obj


class LinkedinPostActor:
    """
    A utility class to fetch and store LinkedIn posts using the Apify platform.

    This class interacts with the Apify API to execute a designated actor that scrapes LinkedIn posts
    for a given profile. The results are parsed and saved to Supabase.
    """

    def __init__(self, linkedin_url, linkedin_profile_id):
        self.client = ApifyClient(config("APIFY_API_KEY"))
        self.linkedin_profile_id = linkedin_profile_id
        self.run_input = {"username": linkedin_url, "page_number": 1, "limit": 10}

    def _parse_linkedin_posts(self, linkedin_posts_iter):
        posts = []

        for linkedin_post in linkedin_posts_iter:
            post = json.loads(
                json.dumps(
                    {
                        "urn": linkedin_post.get("urn"),
                        "author_first_name": linkedin_post.get("author", {}).get("first_name"),
                        "author_last_name": linkedin_post.get("author", {}).get("last_name"),
                        "author_username": linkedin_post.get("author", {}).get("username"),
                        "posted_at_relative": linkedin_post.get("posted_at", {}).get("relative"),
                        "posted_at_date": parse_datetime(linkedin_post.get("posted_at", {}).get("date")),
                        "posted_at_timestamp": linkedin_post.get("posted_at", {}).get("timestamp"),
                        "url": linkedin_post.get("url"),
                        "text": linkedin_post.get("text"),
                        "stats": linkedin_post.get("stats", {}),
                        "media": linkedin_post.get("media", {}).get("images", []),
                        "linkedin_profile_id": self.linkedin_profile_id,
                    },
                    cls=CustomJSONEncoder,
                )
            )
            posts.append(post)

        return posts

    def store_linkedin_posts(self):
        run = self.client.actor(config("LINKEDIN_POST_ACTOR_ID")).call(run_input=self.run_input)
        linkedin_posts_iter = self.client.dataset(run["defaultDatasetId"]).iterate_items()
        parsed_linkedin_posts = self._parse_linkedin_posts(linkedin_posts_iter)

        if parsed_linkedin_posts:
            response = supabase_client.table("sdr_agent_linkedinpost").insert(parsed_linkedin_posts).execute()
            return response.data

        return []
