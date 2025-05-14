from decouple import config

from supabase_client import supabase_client
from utils import call_api


class LinkedinProfileClient:
    def __init__(self, linkedin_profile_url):
        self.headers = {"Authorization": f"Bearer {config('PROXY_CURL_API_KEY')}"}
        self.url = f"{config('PROXY_CURL_LINKEDIN_PROFILE_URL')}{linkedin_profile_url}"
        self.linkedin_profile = None

    def remove_redundant_profile_data(self, profile_data):
        keys_to_remove = [
            "languages_and_proficiencies",
            "accomplishment_organisations",
            "accomplishment_publications",
            "accomplishment_honors_awards",
            "accomplishment_patents",
            "accomplishment_courses",
            "accomplishment_test_scores",
            "activities",
            "similarly_named_profiles",
            "articles",
            "groups",
            "inferred_salary",
            "extra",
            "interests",
            "personal_emails",
            "personal_numbers",
        ]
        for key in keys_to_remove:
            profile_data.pop(key, None)

        return profile_data

    def store_linkedin_profile(self):
        profile_data = call_api("get", self.url, self.headers)

        if profile_data.get("code") and profile_data.get("code") != 200:
            raise Exception("❌ Failed to fetch LinkedIn profile. Please check the URL.")

        formatted_profile_data = self.remove_redundant_profile_data(profile_data)

        response = supabase_client.table("sdr_agent_linkedinprofile").insert(formatted_profile_data).execute()

        if response.data:
            self.linkedin_profile = response.data[0]
        else:
            raise Exception("Failed to insert LinkedIn profile.")

        return self.linkedin_profile

    def get_recent_experience(self):
        if not self.linkedin_profile:
            raise ValueError("LinkedIn profile data not available. Call store_linkedin_profile first.")

        experiences = self.linkedin_profile.get("experiences", [])
        return set(list(
            exp.get("company_linkedin_profile_url")
            for exp in experiences
            if not exp.get("ends_at") and exp.get("company_linkedin_profile_url")
        )[:2])
