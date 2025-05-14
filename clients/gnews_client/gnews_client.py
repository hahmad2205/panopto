from gnews import GNews

from supabase_client import supabase_client


class GNewsClient:
    def __init__(self, linkedin_profile_id):
        self.linkedin_profile_id = linkedin_profile_id

    def _parse_news(self, news):
        parsed_news = []
        for index, item in enumerate(news):
            parsed_news.append(
                {
                    "title": item.get("title"),
                    "date": item.get("published_date"),
                    "source_name": item.get("publisher"),
                    "link": item.get("url"),
                    "position": index,
                    "description": item.get("description"),
                    "linkedin_profile_id": self.linkedin_profile_id,
                }
            )
        return parsed_news[:20]

    def get_person_news(self, person_name):
        """
        Fetch news about a specific person from Google News.

        Args:
            person_name (str): The name of the person to search for.
        Returns:
            list: A list of news articles.
        """
        gnews = GNews()

        news_results = gnews.get_news(person_name)
        parsed_news = self._parse_news(news_results)

        if parsed_news:
            supabase_client.table("sdr_agent_googlenews").insert(parsed_news).execute()
