import logging

import dotenv
import streamlit as st

from clients.apify.linkedin_comments_actor import LinkedinCommentsActor
from clients.apify.linkedin_post_actor import LinkedinPostActor
from clients.apify.website_crawl_actor import WebsiteCrawlActor
from clients.gnews_client.gnews_client import GNewsClient
from clients.proxy_curl.linkedin_company_profile import LinkedinCompanyProfileClient
from clients.proxy_curl.linkedin_profile import LinkedinProfileClient
from clients.serp.google_scholars import GoogleScholarsClient
from streamlit_styles import processing_spinner_style
from supabase_client import supabase_client

logger = logging.getLogger(__name__)
dotenv.load_dotenv()


class DataClient:
    def __init__(self):
        pass

    def fetch_user_data(self, linkedin_url):
        processing_spinner_style()

        try:
            with st.spinner("Fetching linkedin profile..."):
                linkedin_profile_client = LinkedinProfileClient(linkedin_url)
                linkedin_profile = linkedin_profile_client.store_linkedin_profile()
            st.markdown('<span style="color:black;">✅ Linkedin profile fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(
                f"""
            <div class="status-message status-error">
                {str(e)}
            </div>
            """,
                unsafe_allow_html=True,
            )
            return

        user_recent_company_linkedin_profile_urls = linkedin_profile_client.get_recent_experience()

        if not user_recent_company_linkedin_profile_urls:
            logger.warning(f"No recent company experience found for {linkedin_url}")

        with st.spinner("Fetching linkedin company profile..."):
            linkedin_company_profile_client = LinkedinCompanyProfileClient(
                user_recent_company_linkedin_profile_urls, linkedin_profile.get("id")
            )
            if user_recent_company_linkedin_profile_urls:
                linkedin_company_profile_client.store_company_linkedin_profiles()
        st.markdown('<span style="color:black;">✅ Linkedin company profile fetched...</span>', unsafe_allow_html=True)

        company_websites = linkedin_company_profile_client.get_company_websites()

        if company_websites:
            with st.spinner("Fetching company websites..."):
                for company_website in company_websites:
                    website_crawler = WebsiteCrawlActor(company_website)
                    website_crawler.store_company_website()
            st.markdown('<span style="color:black;">✅ Company websites fetched...</span>', unsafe_allow_html=True)

        with st.spinner("Fetching google news..."):
            google_news_client = GNewsClient(linkedin_profile.get("id"))
            google_news_client.get_person_news(linkedin_profile.get("full_name"))
        st.markdown('<span style="color:black;">✅ Google news fetched...</span>', unsafe_allow_html=True)

        with st.spinner("Fetching google publications..."):
            google_scholar_client = GoogleScholarsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
            google_scholar_author_id = google_scholar_client.store_scholar_profile()
            if google_scholar_author_id:
                google_scholar_client.store_scholar_articles(google_scholar_author_id)
        st.markdown('<span style="color:black;">✅ Google publications fetched...</span>', unsafe_allow_html=True)

        if linkedin_profile:
            with st.spinner("Fetching linkedin posts..."):
                linkedin_post_actor = LinkedinPostActor(linkedin_url, linkedin_profile.get("id"))
                linkedin_post_actor.store_linkedin_posts()
            st.markdown('<span style="color:black;">✅ Linkedin posts fetched...</span>', unsafe_allow_html=True)

            with st.spinner("Fetching linkedin comments..."):
                linkedin_comments_actor = LinkedinCommentsActor(linkedin_url, linkedin_profile.get("id"))
                linkedin_comments_actor.store_linkedin_comments()
            st.markdown('<span style="color:black;">✅ Linkedin comments fetched...</span>', unsafe_allow_html=True)

        self.linkedin_profile = linkedin_profile

        return linkedin_profile

    def store_processed_profile(self, pdf, markdown_text, email_to):
        self.linkedin_profile = (
            supabase_client.table("sdr_agent_linkedinprofile")
            .select(
                "*"
            )
            .eq("id", 169)
            .single()
            .execute()
        ).data

        storage_path = f"{self.linkedin_profile.get('public_identifier')}_{self.linkedin_profile.get('id')}_profile.pdf"

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
            "linkedin_profile_id": self.linkedin_profile.get("id"),
        }

        supabase_client.table("sdr_agent_processedprofile").insert(profile_data).execute()

        return final_pdf, storage_path
