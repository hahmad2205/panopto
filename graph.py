from typing import Optional

import streamlit as st
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from clients.ai_client.ai_client import AIClient
from clients.apify.linkedin_comments_actor import LinkedinCommentsActor
from clients.apify.linkedin_post_actor import LinkedinPostActor
from clients.apify.website_crawl_actor import WebsiteCrawlActor
from clients.data_client.data_client import DataClient
from clients.email_client.email_client import EmailClient
from clients.proxy_curl.linkedin_company_profile import LinkedinCompanyProfileClient
from clients.proxy_curl.linkedin_profile import LinkedinProfileClient
from clients.serp.google_news import GoogleNewsClient
from clients.serp.google_scholars import GoogleScholarsClient
from utils import markdown_to_pdf


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

class SDRAgent:
    async def _fetch_linkedin_profile(self, state: State):
        profile = {}

        try:
            with st.spinner("Fetching LinkedIn profile..."):
                linkedin_profile_client = LinkedinProfileClient(state["linkedin_url"])
                profile = linkedin_profile_client.store_linkedin_profile()  # Await if async
            st.markdown('<span style="color:black;">✅ LinkedIn profile fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ LinkedIn profile fetching failed...</span>', unsafe_allow_html=True)

        user_recent_company_linkedin_profile_urls = linkedin_profile_client.get_recent_experience()

        return {
            "linkedin_profile": profile,
            "user_recent_company_linkedin_profile_urls": user_recent_company_linkedin_profile_urls
        }

    async def _fetch_linkedin_company_profile(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_company_profiles = []
        company_websites = []

        try:
            with st.spinner("Fetching linkedin company profile..."):
                linkedin_company_profile_client = LinkedinCompanyProfileClient(
                    state["user_recent_company_linkedin_profile_urls"], linkedin_profile.get("id")
                )
                if state["user_recent_company_linkedin_profile_urls"]:
                    linkedin_company_profiles = linkedin_company_profile_client.store_company_linkedin_profiles()
            st.markdown('<span style="color:black;">✅ Linkedin company profile fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ Linkedin company profile fetching failed...</span>', unsafe_allow_html=True)

        company_websites_url = linkedin_company_profile_client.get_company_websites()

        try:
            if company_websites:
                with st.spinner("Fetching company websites..."):
                    for company_website_url in company_websites_url:
                        website_crawler = WebsiteCrawlActor(company_website_url)
                        company_websites = website_crawler.store_company_website()
                st.markdown('<span style="color:black;">✅ Company websites fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ Company websites fetching failed...</span>',
                        unsafe_allow_html=True)

        return {
            "linkedin_company_profiles": linkedin_company_profiles,
            "company_websites_url": company_websites_url,
            "company_websites": company_websites
        }

    async def _fetch_google_news(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        google_news = []
        try:
            with st.spinner("Fetching google news..."):
                google_news_client = GoogleNewsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
                google_news = google_news_client.store_persons_news()
            st.markdown('<span style="color:black;">✅ Google news fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ Google news fetching failed...</span>',
                        unsafe_allow_html=True)

        return {
            "google_news": google_news
        }

    async def _fetch_google_publications(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        google_publications = []
        try:
            with st.spinner("Fetching google publications..."):
                google_scholar_client = GoogleScholarsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
                google_scholar_author_id = google_scholar_client.store_scholar_profile()
                if google_scholar_author_id:
                    google_publications = google_scholar_client.store_scholar_articles(google_scholar_author_id)
            st.markdown('<span style="color:black;">✅ Google publications fetched...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ Google publications fetching failed...</span>',
                        unsafe_allow_html=True)

        return {
            "google_publications": google_publications
        }

    async def _fetch_linkedin_posts(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_posts = []
        if linkedin_profile:
            try:
                with st.spinner("Fetching linkedin posts..."):
                    linkedin_post_actor = LinkedinPostActor(state["linkedin_url"], linkedin_profile.get("id"))
                    linkedin_posts = linkedin_post_actor.store_linkedin_posts()
                st.markdown('<span style="color:black;">✅ Linkedin posts fetched...</span>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<span style="color:black;">❌ Linkedin posts fetching failed...</span>',
                            unsafe_allow_html=True)

        return {
            "linkedin_posts": linkedin_posts
        }

    async def _fetch_linkedin_comments(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_comments = []

        if linkedin_profile:
            try:
                with st.spinner("Fetching linkedin comments..."):
                    linkedin_comments_actor = LinkedinCommentsActor(state["linkedin_url"], linkedin_profile.get("id"))
                    linkedin_comments = linkedin_comments_actor.store_linkedin_comments()
                st.markdown('<span style="color:black;">✅ Linkedin comments fetched...</span>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<span style="color:black;">❌ Linkedin comments fetching failed...</span>',
                            unsafe_allow_html=True)

        return {
            "linkedin_comments": linkedin_comments
        }

    async def _initialize_ai_client(self, state: State):
        linkedin_profile = state["linkedin_profile"]

        return {
            "ai_client": AIClient(linkedin_profile.get("id"))
        }

    async def _process_google_news(self, state: State):
        ai_client = state["ai_client"]

        return {
            "user_google_news": ai_client.process_with_spinner(
                "Analyzing google news",
                ai_client.process_google_news_content,
                ai_client.get_google_news_context
            ) + "\n\n"
        }

    async def _process_google_publications(self, state: State):
        ai_client = state["ai_client"]

        return {
            "user_publications": ai_client.process_with_spinner(
                "Analyzing google publications",
                ai_client.publications_chain,
                lambda: ai_client.get_context_from_sources([ai_client.publications])
            ) + "\n\n"
        }

    async def _process_opportunities(self, state: State):
        ai_client = state["ai_client"]

        return {
            "opportunities": ai_client.process_with_spinner(
                "Generating opportunities",
                ai_client.opportunities_chain,
                lambda: {
                    **ai_client.get_profile_context(),
                    **ai_client.get_company_context()
                }
            ) + "\n\n"
        }

    async def _process_talking_points(self, state: State):
        ai_client = state["ai_client"]

        return {
            "talking_points": ai_client.process_with_spinner(
                "Identifying talking points",
                lambda: ai_client.talking_point_chain(state["user_publications"], state["user_google_news"]),
                lambda: ai_client.get_context_from_sources(
                    [ai_client.linkedin_profile, ai_client.posts, ai_client.comments, ai_client.google_news, ai_client.publications]
                )
            ) + "\n\n"
        }

    async def _process_engagement_style(self, state: State):
        ai_client = state["ai_client"]

        return {
            "engagement_style": ai_client.process_with_spinner(
                "Determining engagement style",
                ai_client.engagement_style_chain,
                lambda: ai_client.get_context_from_sources(
                    [ai_client.posts, ai_client.comments]
                )
            ) + "\n\n"
        }

    async def _process_objection_handling(self, state: State):
        ai_client = state["ai_client"]

        return {
            "objection_handling": ai_client.process_with_spinner(
                "Preparing objection handling strategies",
                ai_client.objection_handling_chain,
                lambda: {
                    **ai_client.get_profile_context(),
                    **ai_client.get_company_context()
                }
            ) + "\n\n"
        }

    async def _process_trigger_events_and_timing(self, state: State):
        ai_client = state["ai_client"]

        return {
            "trigger_events_and_timing": ai_client.process_with_spinner(
                "Identifying trigger events and timing",
                ai_client.trigger_events_and_timing_chain,
                lambda: {
                    **ai_client.get_company_context(),
                    **ai_client.get_context_from_sources([ai_client.posts])
                }
            ) + "\n\n"
        }

    async def _process_engagement_highlights(self, state: State):
        ai_client = state["ai_client"]

        return {
            "engagement_highlights": ai_client.process_with_spinner(
                "Analyzing engagement highlights",
                ai_client.engagement_highlights_chain,
                lambda: ai_client.get_context_from_sources([ai_client.posts])
            ) + "\n\n"
        }

    async def _process_company_information(self, state: State):
        ai_client = state["ai_client"]

        return {
            "company_information": ai_client.process_with_spinner(
                "Analyzing company information",
                ai_client.company_about_chain,
                ai_client.get_company_context
            ) + "\n\n"
        }

    async def _process_linkedin_data(self, state: State):
        ai_client = state["ai_client"]

        return {
            "linkedin_data": ai_client.process_with_spinner(
                "Analyzing LinkedIn data",
                ai_client.linkedin_data_chain,
                lambda: {
                    **ai_client.get_profile_context(),
                    **{f"[{ai_client.citation_list.index(company) + 1}]": company for company in ai_client.companies}
                }
            ) + "\n\n"
        }

    async def _process_outreach_email(self, state: State):
        ai_client = state["ai_client"]
        llm_output = {
            "opportunities": state["opportunities"],
            "talking_points": state["talking_points"],
            "engagement_style": state["engagement_style"],
            "objection_handling": state["objection_handling"],
            "trigger_events_and_timing": state["trigger_events_and_timing"],
            "engagement_highlights": state["engagement_highlights"],
            "about_company": state["company_information"],
            "linkedin_data": state["linkedin_data"],
        }

        return {
            "outreach_email": ai_client.create_additional_outreach_email(llm_output)
        }

    async def _process_additional_outreaches(self, state: State):
        ai_client = state["ai_client"]

        return {
            "additional_outreaches": ai_client.process_with_spinner(
                "Adding additional outreaches",
                ai_client.suggested_additional_outreach_chain,
                ai_client.get_profile_context
            ) + "\n\n"
        }

    async def _process_citations(self, state: State):
        ai_client = state["ai_client"]

        return {
            "citations": ai_client.process_with_spinner(
                "Adding citations",
                lambda: ai_client.create_citations(state["linkedin_url"]),
                None
            ) + "\n\n"
        }

    async def _aggregate_ai_result(self, state: State):
        ai_client = state["ai_client"]
        state["profile_info_markdown"] = ai_client.create_profile_header_markdown(state["linkedin_url"])
        state["result"] = "## Sales Insights\n"

        ai_results = [
            state["opportunities"],
            state["talking_points"],
            state["engagement_style"],
            state["objection_handling"],
            state["trigger_events_and_timing"],
            state["engagement_highlights"],
            state["company_information"],
            state["linkedin_data"],
            state["user_publications"],
            state["user_google_news"],
            state["outreach_email"],
            state["additional_outreaches"],
            state["citations"],
        ]

        return {
            "result": "".join(result for result in ai_results)
        }

    async def _create_pdf(self, state: State):
        data_client = DataClient()
        pdf = ""
        final_pdf = ""
        storage_path = ""
        try:
            with st.spinner("Creating PDF..."):
                pdf = markdown_to_pdf(state["profile_info_markdown"], state["result"])
                final_pdf, storage_path = data_client.store_processed_profile(pdf, state["result"], state["email"], state["linkedin_profile"])

                st.markdown('<span style="color:black;">✅ PDF created...</span>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ PDF creation failed...</span>',
                        unsafe_allow_html=True)

        return {
            "pdf": pdf,
            "final_pdf": final_pdf,
            "storage_path": storage_path
        }

    async def send_email(self, state: State):
        try:
            with st.spinner("Sending email..."):
                email_client = EmailClient()
                email_kwargs = {
                    "linkedin_profile": state["linkedin_profile"],
                    "final_pdf": state["final_pdf"],
                    "email_to": state["email"],
                    "storage_path": state["storage_path"],
                    "pdf": state["pdf"],
                }
                email_client.send_email(**email_kwargs)

                st.markdown('<span style="color:black;">✅ Email sent...</span>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown('<span style="color:black;">❌ Sending email failed...</span>',
                        unsafe_allow_html=True)

        return state

    def create_graph(self):
        builder = StateGraph(State)

        # Add node
        builder.add_node("fetch_linkedin_profile", self._fetch_linkedin_profile)
        builder.add_node("fetch_linkedin_company_profile", self._fetch_linkedin_company_profile)
        builder.add_node("fetch_linkedin_posts", self._fetch_linkedin_posts)
        builder.add_node("fetch_linkedin_comments", self._fetch_linkedin_comments)
        builder.add_node("fetch_google_news", self._fetch_google_news)
        builder.add_node("fetch_google_publications", self._fetch_google_publications)

        builder.add_node("initialize_ai_client", self._initialize_ai_client)
        builder.add_node("process_google_news", self._process_google_news)
        builder.add_node("process_google_publications", self._process_google_publications)
        builder.add_node("process_opportunities", self._process_opportunities)
        builder.add_node("process_talking_points", self._process_talking_points)
        builder.add_node("process_engagement_style", self._process_engagement_style)
        builder.add_node("process_objection_handling", self._process_objection_handling)
        builder.add_node("process_engagement_highlights", self._process_engagement_highlights)
        builder.add_node("process_trigger_events_and_timing", self._process_trigger_events_and_timing)
        builder.add_node("process_company_information", self._process_company_information)
        builder.add_node("process_linkedin_data", self._process_linkedin_data)
        builder.add_node("process_outreach_email", self._process_outreach_email)
        builder.add_node("process_additional_outreaches", self._process_additional_outreaches)
        builder.add_node("process_citations", self._process_citations)
        builder.add_node("aggregate_ai_result", self._aggregate_ai_result)
        builder.add_node("create_pdf", self._create_pdf)
        builder.add_node("send_email", self.send_email)

        # Add edges
        builder.add_edge(START, "fetch_linkedin_profile")

        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_company_profile")

        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_posts")
        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_comments")
        builder.add_edge("fetch_linkedin_profile", "fetch_google_news")
        builder.add_edge("fetch_linkedin_profile", "fetch_google_publications")

        builder.add_edge("fetch_linkedin_company_profile", "initialize_ai_client")
        builder.add_edge("fetch_linkedin_posts", "initialize_ai_client")
        builder.add_edge("fetch_linkedin_comments", "initialize_ai_client")
        builder.add_edge("fetch_google_news", "initialize_ai_client")
        builder.add_edge("fetch_google_publications", "initialize_ai_client")

        builder.add_edge("initialize_ai_client", "process_google_news")
        builder.add_edge("initialize_ai_client", "process_google_publications")
        builder.add_edge("initialize_ai_client", "process_opportunities")
        builder.add_edge("initialize_ai_client", "process_engagement_style")
        builder.add_edge("initialize_ai_client", "process_objection_handling")
        builder.add_edge("initialize_ai_client", "process_trigger_events_and_timing")
        builder.add_edge("initialize_ai_client", "process_engagement_highlights")
        builder.add_edge("initialize_ai_client", "process_company_information")
        builder.add_edge("initialize_ai_client", "process_linkedin_data")
        builder.add_edge("initialize_ai_client", "process_additional_outreaches")
        builder.add_edge("initialize_ai_client", "process_citations")

        builder.add_edge("process_google_news", "process_talking_points")
        builder.add_edge("process_google_publications", "process_talking_points")
        builder.add_edge("process_opportunities", "process_talking_points")
        builder.add_edge("process_engagement_style", "process_talking_points")
        builder.add_edge("process_objection_handling", "process_talking_points")
        builder.add_edge("process_trigger_events_and_timing", "process_talking_points")
        builder.add_edge("process_engagement_highlights", "process_talking_points")
        builder.add_edge("process_company_information", "process_talking_points")
        builder.add_edge("process_linkedin_data", "process_talking_points")

        builder.add_edge("process_talking_points", "process_outreach_email")

        builder.add_edge("process_outreach_email", "aggregate_ai_result")
        builder.add_edge("aggregate_ai_result", "create_pdf")
        builder.add_edge("create_pdf", "send_email")
        builder.add_edge("send_email", END)

        return builder.compile()

    def invoke_graph(self, linkedin_url: str, email: str):
        graph = self.create_graph()

        initial_state = {
            "linkedin_url": linkedin_url,
            "email": email
        }

        import asyncio
        asyncio.run(graph.ainvoke(initial_state))
