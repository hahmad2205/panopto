import asyncio
from crawl4ai import AsyncWebCrawler
from supabase_client import supabase_client

class WebsiteCrawler:
    def __init__(self, website):
        self.url = website.get("website_url")
        self.company_profile_id = website.get("id")
        self.result = None

    async def _crawl(self):
        async with AsyncWebCrawler() as crawler:
            self.result = await crawler.arun(url=self.url)

    def crawl_page(self):
        content = ""
        asyncio.run(self._crawl())
        if self.result:
            content = self.result.markdown

        return content

    def store_company_website(self):
        websites = []
        try:
            asyncio.run(self._crawl())

            if self.result:
                website_data = {
                    "url": self.url,
                    "markdown": self.result.markdown,
                    "company_profile_id": self.company_profile_id,
                }

                response = supabase_client.table("sdr_agent_companywebsite").insert([website_data]).execute()
                websites = response.data

        except Exception as e:
            print("Error in WebsiteCrawler:", e)

        return websites
