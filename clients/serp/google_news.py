from decouple import config

from supabase_client import supabase_client
from utils import call_api


class GoogleNewsClient:
    def __init__(self, search_term, linkedin_profile_id):
        self.base_url = f"{config('SERP_URL')}"
        self.linkedin_profile_id = linkedin_profile_id
        self.params = {
            "engine": "google_news",
            "q": search_term,
            "api_key": config("SERP_API_KEY"),
        }

    def _parse_news(self, news):
        parsed_news = []
        for item in news.get("news_results", []):
            parsed_news.append(
                {
                    "title": item.get("title"),
                    "date": item.get("date"),
                    "source_name": item.get("source", {}).get("name"),
                    "position": item.get("position"),
                    "link": item.get("link"),
                    "thumbnail": item.get("thumbnail"),
                    "thumbnail_small": item.get("thumbnail_small"),
                    "source_icon": item.get("source", {}).get("icon"),
                    "linkedin_profile_id": self.linkedin_profile_id,
                }
            )
        return parsed_news[:20]

    def store_persons_news(self):
        google_news = call_api("get", self.base_url, {}, params=self.params)
        parsed_news = self._parse_news(google_news)

        if parsed_news:
            supabase_client.table("sdr_agent_googlenews").insert(parsed_news).execute()
