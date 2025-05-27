from typing import TypedDict, Optional

from clients.ai_client.ai_client import AIClient


class State(TypedDict):
    linkedin_url: str
    linkedin_profile: dict
    user_recent_company_linkedin_profile_urls: list
    company_websites_url: list
    linkedin_company_profiles: list
    company_websites: list
    google_news: list
    google_publications: list
    linkedin_posts: list
    linkedin_comments: list
    knowledge_base: dict
    ai_client: Optional[AIClient]
    user_google_news: str
    user_publications: str
    opportunities: str
    talking_points: str
    engagement_style: str
    objection_handling: str
    trigger_events_and_timing: str
    engagement_highlights: str
    company_information: str
    linkedin_data: str
    outreach_email: str
    additional_outreaches: str
    citations: str
    email: str
    result: str
    profile_info_markdown: str
    pdf: str
    final_pdf: str
    storage_path: str
