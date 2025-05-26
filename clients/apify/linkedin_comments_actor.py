from apify_client import ApifyClient
from decouple import config

from supabase_client import supabase_client


class LinkedinCommentsActor:
    """
    A utility class to fetch and store LinkedIn comments using the Apify platform.

    This class uses the Apify API to run a specified actor that scrapes LinkedIn comments for a given profile URL.
    It parses the fetched comments and stores them in the Supabase database.
    """

    def __init__(self, linkedin_url, linkedin_profile_id):
        self.client = ApifyClient(config("APIFY_API_KEY"))
        self.linkedin_profile_id = linkedin_profile_id
        self.run_input = {"username": linkedin_url, "page_number": 1, "limit": 10}

    def _parse_linkedin_comments(self, linkedin_comments_iter):
        parsed_linkedin_comments = []

        for linkedin_comment in linkedin_comments_iter:
            comment = {
                "commenter_name": linkedin_comment.get("commenter", {}).get("name"),
                "commenter_subtitle": linkedin_comment.get("commenter", {}).get("subtitle"),
                "comment_created_at_formatted": linkedin_comment.get("created_at", {}).get("formatted"),
                "comment_created_at_relative": linkedin_comment.get("created_at", {}).get("relative"),
                "comment_text": linkedin_comment.get("comment_text"),
                "comment_link": linkedin_comment.get("comment_link"),
                "is_pinned": linkedin_comment.get("is_pinned", False),
                "post": linkedin_comment.get("post", {}),
                "comment_stats": linkedin_comment.get("comment_stats", {}),
                "source_profile": linkedin_comment.get("source_profile"),
                "linkedin_profile_id": self.linkedin_profile_id,
            }
            parsed_linkedin_comments.append(comment)

        return parsed_linkedin_comments

    def store_linkedin_comments(self):
        run = self.client.actor(config("LINKEDIN_COMMENTS_ACTOR_ID")).call(run_input=self.run_input)
        linkedin_comments_iter = self.client.dataset(run["defaultDatasetId"]).iterate_items()
        parsed_linkedin_comments = self._parse_linkedin_comments(linkedin_comments_iter)
        response = []

        if parsed_linkedin_comments:
            response = supabase_client.table("sdr_agent_linkedincomment").insert(parsed_linkedin_comments).execute()

        return response.data if response else None
