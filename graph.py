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
    def _fetch_linkedin_profile(self, state: State):
        profile = {}

        try:
            linkedin_profile_client = LinkedinProfileClient(state["linkedin_url"])
            profile = linkedin_profile_client.store_linkedin_profile()
        except Exception as e:
            print(e)

        user_recent_company_linkedin_profile_urls = linkedin_profile_client.get_recent_experience()

        return {
            "linkedin_profile": profile,
            "user_recent_company_linkedin_profile_urls": user_recent_company_linkedin_profile_urls
        }

    def _fetch_linkedin_company_profile(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_company_profiles = []
        company_websites = []

        try:
            linkedin_company_profile_client = LinkedinCompanyProfileClient(
                state["user_recent_company_linkedin_profile_urls"], linkedin_profile.get("id")
            )
            if state["user_recent_company_linkedin_profile_urls"]:
                linkedin_company_profiles = linkedin_company_profile_client.store_company_linkedin_profiles()
        except Exception as e:
            print(e)

        company_websites_url = linkedin_company_profile_client.get_company_websites()

        try:
            if company_websites:
                for company_website_url in company_websites_url:
                    website_crawler = WebsiteCrawlActor(company_website_url)
                    company_websites = website_crawler.store_company_website()
        except Exception as e:
            print(e)

        return {
            "linkedin_company_profiles": linkedin_company_profiles,
            "company_websites_url": company_websites_url,
            "company_websites": company_websites
        }

    def _fetch_google_news(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        google_news = []
        try:
            google_news_client = GoogleNewsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
            google_news = google_news_client.store_persons_news()
        except Exception as e:
            print(e)

        return {
            "google_news": google_news
        }

    def _fetch_google_publications(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        google_publications = []
        try:
            google_scholar_client = GoogleScholarsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
            google_scholar_author_id = google_scholar_client.store_scholar_profile()
            if google_scholar_author_id:
                google_publications = google_scholar_client.store_scholar_articles(google_scholar_author_id)
        except Exception as e:
            print(e)

        return {
            "google_publications": google_publications
        }

    def _fetch_linkedin_posts(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_posts = []
        if linkedin_profile:
            try:
                linkedin_post_actor = LinkedinPostActor(state["linkedin_url"], linkedin_profile.get("id"))
                linkedin_posts = linkedin_post_actor.store_linkedin_posts()
            except Exception as e:
                print(e)

        return {
            "linkedin_posts": linkedin_posts
        }

    def _fetch_linkedin_comments(self, state: State):
        linkedin_profile = state["linkedin_profile"]
        linkedin_comments = []

        if linkedin_profile:
            try:
                linkedin_comments_actor = LinkedinCommentsActor(state["linkedin_url"], linkedin_profile.get("id"))
                linkedin_comments = linkedin_comments_actor.store_linkedin_comments()
            except Exception as e:
                print(e)

        return {
            "linkedin_comments": linkedin_comments
        }

    def _initialize_ai_client(self, state: State):
        linkedin_profile = state["linkedin_profile"]

        return {
            "ai_client": AIClient(linkedin_profile.get("id"))
        }

    def _process_google_news(self, state: State):
        ai_client = state["ai_client"]

        return {
            "user_google_news": ai_client.process_with_spinner(
                "Analyzing google news",
                ai_client.process_google_news_content,
                ai_client.get_google_news_context
            ) + "\n\n"
        }

    def _process_google_publications(self, state: State):
        ai_client = state["ai_client"]

        return {
            "user_publications": ai_client.process_with_spinner(
                "Analyzing google publications",
                ai_client.publications_chain,
                lambda: ai_client.get_context_from_sources([ai_client.publications])
            ) + "\n\n"
        }

    def _process_opportunities(self, state: State):
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

    def _process_talking_points(self, state: State):
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

    def _process_engagement_style(self, state: State):
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

    def _process_objection_handling(self, state: State):
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

    def _process_trigger_events_and_timing(self, state: State):
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

    def _process_engagement_highlights(self, state: State):
        ai_client = state["ai_client"]

        return {
            "engagement_highlights": ai_client.process_with_spinner(
                "Analyzing engagement highlights",
                ai_client.engagement_highlights_chain,
                lambda: ai_client.get_context_from_sources([ai_client.posts])
            ) + "\n\n"
        }

    def _process_company_information(self, state: State):
        ai_client = state["ai_client"]

        return {
            "company_information": ai_client.process_with_spinner(
                "Analyzing company information",
                ai_client.company_about_chain,
                ai_client.get_company_context
            ) + "\n\n"
        }

    def _process_linkedin_data(self, state: State):
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

    def _process_outreach_email(self, state: State):
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

    def _process_additional_outreaches(self, state: State):
        ai_client = state["ai_client"]

        return {
            "additional_outreaches": ai_client.process_with_spinner(
                "Adding additional outreaches",
                ai_client.suggested_additional_outreach_chain,
                ai_client.get_profile_context
            ) + "\n\n"
        }

    def _process_citations(self, state: State):
        ai_client = state["ai_client"]

        return {
            "citations": ai_client.process_with_spinner(
                "Adding citations",
                lambda: ai_client.create_citations(state["linkedin_url"]),
                None
            ) + "\n\n"
        }

    def _aggregate_ai_result(self, state: State):
        ai_client = state["ai_client"]
        profile_info_markdown = ai_client.create_profile_header_markdown(state["linkedin_url"])

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
        results_combined = "".join(result for result in ai_results)

        return {
            "profile_info_markdown": profile_info_markdown,
            "result": "## Sales Insights\n" + results_combined
        }

    def _create_pdf(self, state: State):
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

    def _send_email(self, state: State):
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

    def _add_nodes_from_dict(self, builder, nodes: dict):
        for label, function in nodes.items():
            builder.add_node(label, function)

    def _add_edges_from_combinations(self, builder, start_keys, end_keys):
        for start in start_keys:
            for end in end_keys:
                builder.add_edge(start, end)

    def create_graph(self):
        builder = StateGraph(State)

        nodes = {
            "fetch_linkedin_profile": self._fetch_linkedin_profile,
            "fetch_linkedin_company_profile": self._fetch_linkedin_company_profile,
            "fetch_linkedin_posts": self._fetch_linkedin_posts,
            "fetch_linkedin_comments": self._fetch_linkedin_comments,
            "fetch_google_news": self._fetch_google_news,
            "fetch_google_publications": self._fetch_google_publications,
            "initialize_ai_client": self._initialize_ai_client,
            "process_google_news": self._process_google_news,
            "process_google_publications": self._process_google_publications,
            "process_opportunities": self._process_opportunities,
            "process_talking_points": self._process_talking_points,
            "process_engagement_style": self._process_engagement_style,
            "process_objection_handling": self._process_objection_handling,
            "process_engagement_highlights": self._process_engagement_highlights,
            "process_trigger_events_and_timing": self._process_trigger_events_and_timing,
            "process_company_information": self._process_company_information,
            "process_linkedin_data": self._process_linkedin_data,
            "process_outreach_email": self._process_outreach_email,
            "process_additional_outreaches": self._process_additional_outreaches,
            "process_citations": self._process_citations,
            "aggregate_ai_result": self._aggregate_ai_result,
            "create_pdf": self._create_pdf,
            "send_email": self._send_email,
        }

        # Add nodes from the dictionary
        self._add_nodes_from_dict(builder, nodes)

        # Add edges
        builder.add_edge(START, "fetch_linkedin_profile")
        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_company_profile")
        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_posts")
        builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_comments")
        builder.add_edge("fetch_linkedin_profile", "fetch_google_news")
        builder.add_edge("fetch_linkedin_profile", "fetch_google_publications")


        self._add_edges_from_combinations(
            builder,
            ["fetch_linkedin_profile"],
            [
                "fetch_linkedin_company_profile",
                "fetch_linkedin_posts",
                "fetch_linkedin_comments",
                "fetch_google_news",
                "fetch_google_publications"
            ]
        )

        self._add_edges_from_combinations(
            builder,
            [
                "fetch_linkedin_company_profile",
                "fetch_linkedin_posts",
                "fetch_linkedin_comments",
                "fetch_google_news",
                "fetch_google_publications"
            ],
            ["initialize_ai_client"]
        )

        self._add_edges_from_combinations(
            builder,
            ["initialize_ai_client"],
            [
                "process_google_news",
                "process_google_publications",
                "process_opportunities",
                "process_engagement_style",
                "process_objection_handling",
                "process_trigger_events_and_timing",
                "process_engagement_highlights",
                "process_company_information",
                "process_linkedin_data",
                "process_additional_outreaches",
                "process_citations"
            ]
        )
        self._add_edges_from_combinations(
            builder,
            [
                "process_google_news",
                "process_google_publications",
                "process_opportunities",
                "process_engagement_style",
                "process_objection_handling",
                "process_trigger_events_and_timing",
                "process_engagement_highlights",
                "process_company_information",
                "process_linkedin_data",
                "process_additional_outreaches",
                "process_citations"
            ],
            ["process_talking_points"]
        )

        builder.add_edge("process_talking_points", "process_outreach_email")
        builder.add_edge("process_outreach_email", "aggregate_ai_result")
        builder.add_edge("aggregate_ai_result", "create_pdf")
        builder.add_edge("create_pdf", "send_email")
        builder.add_edge("send_email", END)

        return builder.compile()

    def invoke_graph(self, linkedin_url: str, email: str):
        try:
            graph = self.create_graph()
            initial_state = {
                "linkedin_url": linkedin_url,
                "email": email,
            }
            graph.invoke(initial_state)

            return [200, f"Email sent to {email}"]
        except Exception as e:
            return [None, f"Processing failed: {str(e)}"]
