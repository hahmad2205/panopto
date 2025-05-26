from decouple import config

from clients.ai_client.ai_client import AIClient
from supabase_client import supabase_client
from utils import call_api


class GoogleScholarsClient:
    def __init__(self, search_term, linkedin_profile_id):
        self.base_url = f"{config('SERP_URL')}"
        self.linkedin_profile_id = linkedin_profile_id
        self.google_scholar_params = {
            "engine": "google_scholar_profiles",
            "mauthors": search_term,
            "api_key": config("SERP_API_KEY"),
        }
        self.scholar_profile = None

    def _remove_redundant_profile_data(self, profiles):
        updated_profiles = []
        for profile in profiles.get("profiles", []):
            profile.pop("serpapi_link", None)
            updated_profiles.append(profile)
        return updated_profiles

    def store_scholar_profile(self):
        scholar_profiles = call_api("get", self.base_url, {}, params=self.google_scholar_params)
        parsed_profiles = self._remove_redundant_profile_data(scholar_profiles)

        ai_client = AIClient(self.linkedin_profile_id)
        author = ai_client.publication_author_chain(parsed_profiles)
        author_id = author.author_id

        if author_id:
            author_profile = next((profile for profile in parsed_profiles if profile["author_id"] == author_id), None)

            if author_profile:
                author_profile["linkedin_profile_id"] = self.linkedin_profile_id
                response = supabase_client.table("sdr_agent_googlescholarprofile").insert(author_profile).execute()
                if response.data:
                    self.scholar_profile = response.data[0]
                else:
                    raise Exception("Failed to insert scholar profile.")

        return author_id

    def _parse_scholar_articles_data(self, articles):
        parsed_articles = []
        scholar_id = self.scholar_profile["id"] if self.scholar_profile else None

        for article in articles.get("articles", []):
            parsed_articles.append(
                {
                    "citation_id": article.get("citation_id"),
                    "publication": article.get("publication"),
                    "title": article.get("title"),
                    "authors": article.get("authors"),
                    "link": article.get("link"),
                    "cited_by": article.get("cited_by", {}).get("value", 0),
                    "scholar_id": scholar_id,
                }
            )

        return parsed_articles

    def store_scholar_articles(self, author_id):
        google_articles_params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": config("SERP_API_KEY"),
        }
        scholar_articles = call_api("get", self.base_url, {}, params=google_articles_params)
        parsed_articles = self._parse_scholar_articles_data(scholar_articles)
        response = []
        if parsed_articles:
            response = supabase_client.table("sdr_agent_googlepublication").insert(parsed_articles).execute()

        return response.data if response else None
