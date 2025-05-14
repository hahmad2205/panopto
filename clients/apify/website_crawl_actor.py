from apify_client import ApifyClient
from decouple import config

from supabase_client import supabase_client


class WebsiteCrawlActor:
    """
    A utility class to crawl company websites using the Apify platform and store the extracted content in Supabase.
    """

    def __init__(self, website):
        self.client = ApifyClient(config("APIFY_API_KEY"))
        self.website_id = website["id"]
        self.run_input = {
            "startUrls": [{"url": website["website_url"]}],
            "maxCrawlPages": 1,
            "maxCrawlDepth": 0,
        }

    def store_company_website(self):
        try:
            run = self.client.actor(config("WEBSITE_CRAWLER_ACTOR_ID")).call(run_input=self.run_input)
            iterator = self.client.dataset(run["defaultDatasetId"]).iterate_items()

            company_websites = []
            for item in iterator:
                company_websites.append(
                    {
                        "url": item["url"],
                        "text": item["text"],
                        "markdown": item["markdown"],
                        "company_profile_id": self.website_id,
                    }
                )

            if company_websites:
                response = supabase_client.table("sdr_agent_companywebsite").insert(company_websites).execute()
                return response.data

        except Exception as e:
            print("Error in WebsiteCrawlActor:", e)

        return []
