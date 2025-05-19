import logging

import streamlit as st

from clients.ai_client.ai_client import AIClient
from clients.data_client.data_client import DataClient
from clients.email_client.email_client import EmailClient
from supabase_client import supabase_client
from utils import markdown_to_pdf

logger = logging.getLogger(__name__)


def process_user_details(linkedin_url, email_to):
    try:
        data_client = DataClient()
        # linkedin_profile = data_client.fetch_user_data(linkedin_url)
        linkedin_profile = (
            supabase_client.table("sdr_agent_linkedinprofile")
            .select(
                "*"
            )
            .eq("id", 234)
            .single()
            .execute()
        ).data

        if linkedin_profile:
            ai_client = AIClient(linkedin_profile.get("id"))
            profile_with_markdown, markdown_text = ai_client.run_client(linkedin_url)

            try:
                with st.spinner("Creating PDF..."):
                    pdf = markdown_to_pdf(profile_with_markdown, markdown_text)
                    final_pdf, storage_path = data_client.store_processed_profile(pdf, markdown_text, email_to)

                    st.markdown('<span style="color:black;">✅ PDF created...</span>',
                                unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<span style="color:black;">❌ PDF creation failed...</span>',
                            unsafe_allow_html=True)

            try:
                with st.spinner("Sending email..."):
                    email_client = EmailClient()
                    email_kwargs = {
                        "linkedin_profile": linkedin_profile,
                        "final_pdf": final_pdf,
                        "email_to": email_to,
                        "storage_path": storage_path,
                        "pdf": pdf,
                    }
                    email_client.send_email(**email_kwargs)

                    st.markdown('<span style="color:black;">✅ Email sent...</span>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<span style="color:black;">❌ Sending email failed...</span>',
                        unsafe_allow_html=True)

            return [200, f"Email sent to {email_to}"]
        else:
            return [None, f"Linkedin profile not found"]

    except Exception as e:
        logger.error(f"Error occurred while fetching user details for {linkedin_url}: {str(e)}")
        raise
