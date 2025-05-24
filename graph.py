# from langgraph.graph import StateGraph, START, END
# from typing_extensions import TypedDict
# import streamlit as st
#
# from clients.ai_client.ai_client import AIClient
# from clients.apify.linkedin_comments_actor import LinkedinCommentsActor
# from clients.apify.linkedin_post_actor import LinkedinPostActor
# from clients.apify.website_crawl_actor import WebsiteCrawlActor
# from clients.proxy_curl.linkedin_company_profile import LinkedinCompanyProfileClient
# from clients.proxy_curl.linkedin_profile import LinkedinProfileClient
# from clients.serp.google_news import GoogleNewsClient
# from clients.serp.google_scholars import GoogleScholarsClient
#
#
# class State(TypedDict):
#     linkedin_url: str
#     linkedin_profile: dict
#     user_recent_company_linkedin_profile_urls: list
#     company_websites: list
#     email: str
#     result: str
#
# class SDRAgent:
#     async def _fetch_linkedin_profile(self, state: State):
#         try:
#             with st.spinner("Fetching LinkedIn profile..."):
#                 linkedin_profile_client = LinkedinProfileClient(state["linkedin_url"])
#                 state["linkedin_profile"] = linkedin_profile_client.store_linkedin_profile()  # Await if async
#                 print(state["linkedin_profile"])
#             st.markdown('<span style="color:black;">✅ LinkedIn profile fetched...</span>', unsafe_allow_html=True)
#         except Exception as e:
#             st.markdown('<span style="color:black;">❌ LinkedIn profile fetching failed...</span>', unsafe_allow_html=True)
#
#         state["user_recent_company_linkedin_profile_urls"] = linkedin_profile_client.get_recent_experience()
#
#         return state
#
#     async def _fetch_linkedin_company_profile(self, state: State):
#         linkedin_profile = state["linkedin_profile"]
#         try:
#             with st.spinner("Fetching linkedin company profile..."):
#                 linkedin_company_profile_client = LinkedinCompanyProfileClient(
#                     state["user_recent_company_linkedin_profile_urls"], linkedin_profile.get("id")
#                 )
#                 if state["user_recent_company_linkedin_profile_urls"]:
#                     linkedin_company_profile_client.store_company_linkedin_profiles()
#             st.markdown('<span style="color:black;">✅ Linkedin company profile fetched...</span>', unsafe_allow_html=True)
#         except Exception as e:
#             st.markdown('<span style="color:black;">❌ Linkedin company profile fetching failed...</span>', unsafe_allow_html=True)
#
#         state["company_websites"] = linkedin_company_profile_client.get_company_websites()
#
#         return state
#
#     async def _fetch_company_websites(self, state: State):
#         company_websites = state["company_websites"]
#         try:
#             if company_websites:
#                 with st.spinner("Fetching company websites..."):
#                     for company_website in company_websites:
#                         website_crawler = WebsiteCrawlActor(company_website)
#                         website_crawler.store_company_website()
#                 st.markdown('<span style="color:black;">✅ Company websites fetched...</span>', unsafe_allow_html=True)
#         except Exception as e:
#             st.markdown('<span style="color:black;">❌ Company websites fetching failed...</span>',
#                         unsafe_allow_html=True)
#
#         return company_websites
#
#     async def _fetch_google_news(self, state: State):
#         linkedin_profile = state["linkedin_profile"]
#         try:
#             with st.spinner("Fetching google news..."):
#                 google_news_client = GoogleNewsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
#                 google_news_client.store_persons_news()
#             st.markdown('<span style="color:black;">✅ Google news fetched...</span>', unsafe_allow_html=True)
#         except Exception as e:
#             st.markdown('<span style="color:black;">❌ Google news fetching failed...</span>',
#                         unsafe_allow_html=True)
#
#         return state
#
#     async def _fetch_google_publications(self, state: State):
#         linkedin_profile = state["linkedin_profile"]
#         try:
#             with st.spinner("Fetching google publications..."):
#                 google_scholar_client = GoogleScholarsClient(linkedin_profile.get("full_name"), linkedin_profile.get("id"))
#                 google_scholar_author_id = google_scholar_client.store_scholar_profile()
#                 if google_scholar_author_id:
#                     google_scholar_client.store_scholar_articles(google_scholar_author_id)
#             st.markdown('<span style="color:black;">✅ Google publications fetched...</span>', unsafe_allow_html=True)
#         except Exception as e:
#             st.markdown('<span style="color:black;">❌ Google publications fetching failed...</span>',
#                         unsafe_allow_html=True)
#
#         return state
#
#     async def _fetch_linkedin_posts(self, state: State):
#         linkedin_profile = state["linkedin_profile"]
#         if linkedin_profile:
#             try:
#                 with st.spinner("Fetching linkedin posts..."):
#                     linkedin_post_actor = LinkedinPostActor(state["linkedin_url"], linkedin_profile.get("id"))
#                     linkedin_post_actor.store_linkedin_posts()
#                 st.markdown('<span style="color:black;">✅ Linkedin posts fetched...</span>', unsafe_allow_html=True)
#             except Exception as e:
#                 st.markdown('<span style="color:black;">❌ Linkedin posts fetching failed...</span>',
#                             unsafe_allow_html=True)
#
#         return state
#
#     async def _fetch_linkedin_comments(self, state: State):
#         linkedin_profile = state["linkedin_profile"]
#
#         if linkedin_profile:
#             try:
#                 with st.spinner("Fetching linkedin comments..."):
#                     linkedin_comments_actor = LinkedinCommentsActor(state["linkedin_url"], linkedin_profile.get("id"))
#                     linkedin_comments_actor.store_linkedin_comments()
#                 st.markdown('<span style="color:black;">✅ Linkedin comments fetched...</span>', unsafe_allow_html=True)
#             except Exception as e:
#                 st.markdown('<span style="color:black;">❌ Linkedin comments fetching failed...</span>',
#                             unsafe_allow_html=True)
#
#         return state
#
#     def create_graph(self):
#         builder = StateGraph(State)
#
#         # Add node
#         builder.add_node("fetch_linkedin_profile", self._fetch_linkedin_profile)
#         builder.add_node("fetch_linkedin_company_profile", self._fetch_linkedin_company_profile)
#         builder.add_node("fetch_company_websites", self._fetch_company_websites)
#         builder.add_node("fetch_linkedin_posts", self._fetch_google_publications)
#         builder.add_node("fetch_linkedin_comments", self._fetch_linkedin_comments)
#         builder.add_node("fetch_google_news", self._fetch_google_news)
#         builder.add_node("fetch_google_publications", self._fetch_google_publications)
#
#         # Add edges
#         builder.add_edge(START, "fetch_linkedin_profile")
#
#         builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_company_profile")
#         builder.add_edge("fetch_linkedin_company_profile", "fetch_company_websites")
#
#         builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_posts")
#         builder.add_edge("fetch_linkedin_profile", "fetch_linkedin_comments")
#         builder.add_edge("fetch_linkedin_profile", "fetch_google_news")
#         builder.add_edge("fetch_linkedin_profile", "fetch_google_publications")
#
#
#         return builder.compile()
#
#
# sdr_agent = SDRAgent()
# graph_app = sdr_agent.create_graph()

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from my_chains import (
    fetch_linkedin_data, fetch_google_news, fetch_google_publications,
    fetch_linkedin_company_website, fetch_company_website, fetch_linkedin_posts, fetch_linkedin_comments,
    news_chain, publication_chain, opportunities_chain, about_company_chain,
    objection_handling_chain, engagement_highlights_chain, engagement_style_chain,
    suggested_outreaches_chain, trigger_events_chain, linkedin_data_chain,
    generate_talking_points, generate_citations, outreach_email_chain,
    create_pdf_and_send_email
)

# ------------------------
# Define State
# ------------------------

class GraphState(TypedDict):
    linkedin_data: dict
    google_news: list
    google_publications: list
    linkedin_posts: list
    linkedin_comments: list
    linkedin_company_website: str
    company_website: str
    results: dict
    talking_points: str
    citations: str
    outreach_email: str
    final_status: str

# ------------------------
# Build Graph
# ------------------------

builder = StateGraph(GraphState)

# Step 1: Fetch LinkedIn and Related Data
builder.add_node("fetch_linkedin_data", fetch_linkedin_data)
builder.add_node("fetch_google_news", fetch_google_news)
builder.add_node("fetch_google_publications", fetch_google_publications)
builder.add_node("fetch_linkedin_company_website", fetch_linkedin_company_website)
builder.add_node("fetch_company_website", fetch_company_website)
builder.add_node("fetch_linkedin_posts", fetch_linkedin_posts)
builder.add_node("fetch_linkedin_comments", fetch_linkedin_comments)

builder.set_entry_point("fetch_linkedin_data")

# Parallel after LinkedIn data
builder.add_edge("fetch_linkedin_data", "fetch_google_news")
builder.add_edge("fetch_linkedin_data", "fetch_google_publications")
builder.add_edge("fetch_linkedin_data", "fetch_linkedin_company_website")
builder.add_edge("fetch_linkedin_data", "fetch_linkedin_posts")
builder.add_edge("fetch_linkedin_data", "fetch_linkedin_comments")
builder.add_edge("fetch_linkedin_company_website", "fetch_company_website")

# Step 2: LLM Chains
builder.add_node("news_chain", news_chain)
builder.add_node("publication_chain", publication_chain)
builder.add_node("opportunities_chain", opportunities_chain)
builder.add_node("about_company_chain", about_company_chain)
builder.add_node("objection_handling_chain", objection_handling_chain)
builder.add_node("engagement_highlights_chain", engagement_highlights_chain)
builder.add_node("engagement_style_chain", engagement_style_chain)
builder.add_node("suggested_outreaches_chain", suggested_outreaches_chain)
builder.add_node("trigger_events_chain", trigger_events_chain)
builder.add_node("linkedin_data_chain", linkedin_data_chain)

# Connect all fetching → LLM chains (assume internal parallel execution)
llm_chains = [
    "news_chain", "publication_chain", "opportunities_chain", "about_company_chain",
    "objection_handling_chain", "engagement_highlights_chain", "engagement_style_chain",
    "suggested_outreaches_chain", "trigger_events_chain", "linkedin_data_chain"
]
for fetch_node in [
    "fetch_google_news", "fetch_google_publications", "fetch_linkedin_company_website",
    "fetch_company_website", "fetch_linkedin_posts", "fetch_linkedin_comments"
]:
    for chain in llm_chains:
        builder.add_edge(fetch_node, chain)

# Step 3: Combine Results
builder.add_node("generate_talking_points", generate_talking_points)
builder.add_node("generate_citations", generate_citations)
builder.add_node("outreach_email_chain", outreach_email_chain)

for chain in llm_chains:
    builder.add_edge(chain, "generate_talking_points")
    builder.add_edge(chain, "generate_citations")
    builder.add_edge(chain, "outreach_email_chain")

# Step 4: Final Output
builder.add_node("create_pdf_and_send_email", create_pdf_and_send_email)
builder.add_edge("generate_talking_points", "create_pdf_and_send_email")
builder.add_edge("generate_citations", "create_pdf_and_send_email")
builder.add_edge("outreach_email_chain", "create_pdf_and_send_email")

builder.set_finish_point("create_pdf_and_send_email")

# ------------------------
# Compile and Use
# ------------------------

graph = builder.compile()
