import logging

import dotenv
import streamlit as st

from clients.apify.linkedin_comments_actor import LinkedinCommentsActor
from clients.apify.linkedin_post_actor import LinkedinPostActor
from clients.apify.website_crawl_actor import WebsiteCrawlActor
from clients.proxy_curl.linkedin_company_profile import LinkedinCompanyProfileClient
from clients.proxy_curl.linkedin_profile import LinkedinProfileClient
from clients.serp.google_news import GoogleNewsClient
from clients.serp.google_scholars import GoogleScholarsClient
from streamlit_styles import processing_spinner_style
from supabase_client import supabase_client

logger = logging.getLogger(__name__)
dotenv.load_dotenv()


class DataClient:
    def __init__(self):
        pass

    def store_processed_profile(self, pdf, markdown_text, email_to, linkedin_profile):
        storage_path = f"{linkedin_profile.get('public_identifier')}_{linkedin_profile.get('id')}_profile.pdf"

        supabase_client.storage.from_("processedprofiles").upload(
            file=pdf, path=storage_path, file_options={"content-type": "application/pdf"}
        )

        # Get public URL
        final_pdf = supabase_client.storage.from_("processedprofiles").get_public_url(storage_path)

        # Store profile data in Supabase
        profile_data = {
            "text": markdown_text,
            "email_to": email_to,
            "final_pdf": final_pdf,
            "linkedin_profile_id": linkedin_profile.get("id"),
        }

        supabase_client.table("sdr_agent_processedprofile").insert(profile_data).execute()

        return final_pdf, storage_path
