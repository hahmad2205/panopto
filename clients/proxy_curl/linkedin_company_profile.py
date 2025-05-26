from decouple import config

from supabase_client import supabase_client
from utils import call_api


class LinkedinCompanyProfileClient:
    def __init__(self, company_linkedin_urls, linkedin_profile_id):
        self.headers = {"Authorization": f"Bearer {config('PROXY_CURL_API_KEY')}"}
        self.company_base_url = config("PROXY_CURL_LINKEDIN_COMPANY_PROFILE_URL")
        self.school_base_url = config("PROXY_CURL_LINKEDIN_SCHOOL_PROFILE_URL")

        self.company_linkedin_urls = company_linkedin_urls
        self.linkedin_profile_id = linkedin_profile_id
        self.saved_profiles = []

    def _parse_company_profile_data(self, company_linkedin_data):
        parsed_company_profile_data = {
            "linkedin_internal_id": company_linkedin_data.get("linkedin_internal_id"),
            "description": company_linkedin_data.get("description"),
            "website": company_linkedin_data.get("website"),
            "industry": company_linkedin_data.get("industry"),
            "company_size_on_linkedin": company_linkedin_data.get("company_size_on_linkedin"),
            "search_id": company_linkedin_data.get("search_id"),
            "company_type": company_linkedin_data.get("company_type"),
            "founded_year": company_linkedin_data.get("founded_year"),
            "follower_count": company_linkedin_data.get("follower_count"),
            "name": company_linkedin_data.get("name"),
            "tagline": company_linkedin_data.get("tagline"),
            "profile_pic_url": company_linkedin_data.get("profile_pic_url"),
            "background_cover_image_url": company_linkedin_data.get("background_cover_image_url"),
            "universal_name_id": company_linkedin_data.get("universal_name_id"),
            "specialties": company_linkedin_data.get("specialities", []),
            "locations": company_linkedin_data.get("locations", []),
            "updates": company_linkedin_data.get("updates", []),
            "head_quarter": company_linkedin_data.get("hq", {}),
            "linkedin_profile_id": self.linkedin_profile_id,
        }

        if company_linkedin_data.get("company_size"):
            min_size, max_size = company_linkedin_data.get("company_size", [None, None])
            parsed_company_profile_data["min_company_size"] = min_size
            parsed_company_profile_data["max_company_size"] = max_size

        return parsed_company_profile_data

    def store_company_linkedin_profiles(self):
        company_records = []

        for url in self.company_linkedin_urls:
            try:
                base_url = self.school_base_url if url.startswith("https://www.linkedin.com/school/") else self.company_base_url
                full_url = f"{base_url}{url}"
                raw_data = call_api("get", full_url, self.headers)

                parsed_data = self._parse_company_profile_data(raw_data)
                company_records.append(parsed_data)
            except Exception as e:
                print(f"Failed to process {url}: {str(e)}")

        if company_records:
            response = supabase_client.table("sdr_agent_companylinkedinprofile").insert(company_records).execute()
            self.saved_profiles = response.data
            return self.saved_profiles

    def get_company_websites(self):
        return [
            {"id": saved_profile["id"], "website_url": saved_profile["website"]}
            for saved_profile in self.saved_profiles
            if saved_profile.get("website")
        ]
