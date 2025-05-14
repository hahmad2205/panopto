from time import sleep
from typing import Union

import dotenv
import streamlit as st
from decouple import config
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import GoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langsmith import Client as LangSmithClient
from pydantic import BaseModel

from streamlit_styles import processing_spinner_style
from supabase_client import supabase_client

dotenv.load_dotenv()


class ScholarProfile(BaseModel):
    author_id: Union[str, None]


class AvailableNews(BaseModel):
    news_available: bool


class AIClient:
    def __init__(self, linkedin_profile_id):
        self.langsmith_client = LangSmithClient(api_key=config("LANGSMITH_API_KEY"))
        # self.model = ChatOpenAI(
        #     base_url="https://openrouter.ai/api/v1",
        #     model="google/gemini-2.5-flash-preview-04-17",
        #     api_key=config("OPEN_ROUTER_API_KEY"),
        #     temperature=0
        # )
        self.model = GoogleGenerativeAI(
            google_api_key=config("GEMINI_API_KEY"),
            model="gemini-2.5-flash-preview-04-17",
            temperature=0
        )

        self._initialize_data(linkedin_profile_id)

    def _initialize_data(self, linkedin_profile_id):
        profile_resp = (
            supabase_client.table("sdr_agent_linkedinprofile")
            .select(
                """
                *,
                sdr_agent_companylinkedinprofile(*, sdr_agent_companywebsite(*)),
                sdr_agent_linkedinpost(*, sdr_agent_linkedinpostreaction(*)),
                sdr_agent_linkedincomment(*),
                sdr_agent_googlenews(*),
                sdr_agent_googlescholarprofile(*, sdr_agent_googlepublication(*))
                """
            )
            .eq("id", linkedin_profile_id)
            .single()
            .execute()
        ).data

        if not profile_resp:
            print("Failed to fetch LinkedIn profile:", profile_resp.error)
            self.linkedin_profile = None
            self.companies = []
            self.posts = []
            self.comments = []
            self.google_news = []
            self.publications = []
            self.companies_websites = []
            return

        profile = profile_resp
        self.linkedin_profile = profile
        self.companies = profile.get("sdr_agent_companylinkedinprofile", [])
        self.posts = profile.get("sdr_agent_linkedinpost", [])
        self.comments = profile.get("sdr_agent_linkedincomment", [])
        self.google_news = profile.get("sdr_agent_googlenews", [])
        self.scholar_profile = profile.get("sdr_agent_googlescholarprofile")
        self.publications = self.scholar_profile.get("sdr_agent_googlepublication", []) if self.scholar_profile else []

        self.companies_websites = []
        for company in self.companies:
            self.companies_websites.extend(company.get("sdr_agent_companywebsite", []))

        remove_linkedin_profile_items = [
            "sdr_agent_companylinkedinprofile",
            "sdr_agent_linkedinpost",
            "sdr_agent_linkedincomment",
            "sdr_agent_googlenews",
            "sdr_agent_googlescholarprofile"
        ]

        for redundant_linkedin_profile_item in remove_linkedin_profile_items:
            self.linkedin_profile.pop(redundant_linkedin_profile_item, None)

        self.citation_list = [
            source for source in (
                    [self.linkedin_profile] +
                    self.companies +
                    self.companies_websites +
                    [self.posts, self.comments, self.publications, self.google_news]
            ) if source
        ]

        self.knowledge_base = (
            supabase_client.table("sdr_agent_knowledgebase")
            .select(
                "*"
            )
            .eq("id", config("KNOWLEDGE_BASE_ID"))
            .single()
            .execute()
        ).data

    def _run_chain(self, prompt_name, chain_input, parser=None):
        prompt = self.langsmith_client.pull_prompt(f"{prompt_name}:{config('LANGSMITH_PROMPT_TAG')}")
        chain = (prompt | self.model | parser) if parser else (prompt | self.model)
        response = chain.invoke(chain_input)

        return response

    def linkedin_data_chain(self):
        input_data = {
            "summary": self.linkedin_profile.get("summary"),
            "headline": self.linkedin_profile.get("headline"),
            "experiences": self.linkedin_profile.get("experiences"),
            "education": self.linkedin_profile.get("education"),
            "certifications": self.linkedin_profile.get("certifications"),
            "industry": self.linkedin_profile.get("industry"),
            "company_description": [c.get("description") for c in self.companies],
            "skills": self.linkedin_profile.get("skills"),
            "recommendations": self.linkedin_profile.get("recommendations"),
        }
        return self._run_chain("linkedin_data_chain_prompt", input_data)

    def about_company_chain(self):
        return self._run_chain(
            "about_company_chain_prompt",
            {
                "linkedin_companies_profiles": self.companies,
                "linkedin_companies_websites": self.companies_websites,
            },
        )

    def engagement_style_chain(self):
        return self._run_chain(
            "engagement_style_chain_prompt",
            {
                "linkedin_posts_caption": [post.get("text") for post in self.posts],
                "linkedin_comments": [c.get("comment_text") for c in self.comments],
            },
        )

    def suggested_additional_outreach(self):
        return self._run_chain(
            "suggested_additional_outreach_chain_prompt",
            {
                "people_also_viewed": self.linkedin_profile.get("people_also_viewed"),
                "linkedin_headline": self.linkedin_profile.get("headline"),
                "linkedin_summary": self.linkedin_profile.get("summary"),
            },
        )

    def talking_point_chain(self):
        return self._run_chain(
            "talking_point_chain_prompt",
            {
                "linkedin_experiences": self.linkedin_profile.get("experiences"),
                "linkedin_education": self.linkedin_profile.get("education"),
                "linkedin_posts": self.posts,
                "linkedin_comments": self.comments,
                "publications": self.publications,
                "news": self.google_news,
                "connect": self.knowledge_base.get("connect"),
                "ai_summary": self.knowledge_base.get("ai_summary"),
                "knowledge_insights": self.knowledge_base.get("knowledge_insights")
            },
        )

    def opportunities_chain(self):
        return self._run_chain(
            "opportunities_chain_prompt",
            {
                "linkedin_companies_profiles": self.companies,
                "linkedin_companies_websites": self.companies_websites,
                "linkedin_headline": self.linkedin_profile.get("headline"),
                "sell_for_enterprise": self.knowledge_base.get("sell_for_enterprise"),
                "sell_for_education": self.knowledge_base.get("sell_for_education")
            },
        )

    def engagement_highlights_chain(self):
        return self._run_chain(
            "engagement_highlights_chain_prompt",
            {
                "linkedin_posts": self.posts,
            },
        )

    def trigger_events_and_timing_chain(self):
        return self._run_chain(
            "trigger_events_and_timing_chain_prompt",
            {
                "linkedin_posts": self.posts,
                "linkedin_companies": self.companies,
                "linkedin_companies_websites": self.companies_websites,
            },
        )

    def objection_handling_chain(self):
        return self._run_chain(
            "objection_handling_prompt",
            {
                "linkedin_profile": self.linkedin_profile,
                "linkedin_companies": self.companies,
                "linkedin_companies_websites": self.companies_websites,
                "objection_handling": self.knowledge_base.get("objection_handling_context"),
                "competitors_insights": self.knowledge_base.get("insights_vs_competitors")
            },
        )

    def outreach_email_chain(self, outreach_email_input):
        return self._run_chain(
            "outreach_email_chain_prompt",
            outreach_email_input
        )

    def publications_chain(self):
        return self._run_chain(
            "publications_chain_prompt",
            {
                "publications": self.publications,
            }
        )

    def publication_author_chain(self, google_scholar_profiles):
        return self._run_chain(
            "google_scholar_profile_chain_prompt",
            {
                "google_scholar_profiles": google_scholar_profiles,
                "linkedin_profile": self.linkedin_profile,
            },
            PydanticOutputParser(pydantic_object=ScholarProfile)
        )

    def news_chain(self):
        return self._run_chain(
            "news_chain_prompt",
            {
                "linkedin_profile": self.linkedin_profile,
                "google_news": self.google_news
            }
        )

    def check_news_available(self, news):
        return self._run_chain(
            "news_available_chain_prompt",
            {
                "news": news
            },
            PydanticOutputParser(pydantic_object=AvailableNews)
        )

    def add_citations_chain(self, content, context):
        return self._run_chain(
            "add_citations_chain_prompt",
            {
                "content": content,
                "context": context
            }
        )

    def create_citations(self, linkedin_url):
        citations = "## References\n"

        for i, item in enumerate(self.citation_list, start=1):
            if item == self.linkedin_profile:
                name = item.get("full_name", "LinkedIn Profile")
                citations += f"{i}. [LinkedIn Profile --- {name}]({linkedin_url})\n"

            elif item in self.companies:
                name = item.get("name", "Company Profile")
                url = f"https://www.linkedin.com/company/{item.get('universal_name_id')}"
                citations += f"{i}. [LinkedIn Company Profile --- {name}]({url})\n"

            elif item in self.companies_websites:
                company_id = item.get("company_profile_id")
                company_info = supabase_client.table("sdr_agent_companylinkedinprofile").select("name").eq("id", company_id).single().execute()
                name = company_info.data.get("name", "Company Website")
                url = item.get("url", "#")
                citations += f"{i}. [Company Website --- {name}]({url})\n"

            elif item == self.posts:
                name = self.linkedin_profile.get("full_name", "Posts")
                url = f"{linkedin_url}{'' if linkedin_url.endswith('/') else '/'}recent-activity/all/"
                citations += f"{i}. [LinkedIn Posts --- {name}]({url})\n"

            elif item == self.comments:
                name = self.linkedin_profile.get("full_name", "Comments")
                url = f"{linkedin_url}{'' if linkedin_url.endswith('/') else '/'}recent-activity/comments/"
                citations += f"{i}. [LinkedIn Comments --- {name}]({url})\n"

            elif item == self.publications or item == self.scholar_profile:
                name = self.scholar_profile.get("name", "Google Scholar")
                author_id = self.scholar_profile.get("author_id", "")
                url = f"https://scholar.google.com/citations?user={author_id}&hl=en&oi=ao"
                citations += f"{i}. [Google Publications --- {name}]({url})\n"

            elif item == self.google_news and self.news_availabilty.news_available:
                name = self.linkedin_profile.get("full_name", "Google News")
                query = name.replace(" ", "+")
                url = f"https://www.google.com/search?q={query}&tbm=nws"
                citations += f"{i}. [Google News --- {name}]({url})\n"

        return citations

    def run_client(self, linkedin_url):
        # TODO: Split this function

        processing_spinner_style()

        current_experience_lines = "\n".join(
            f"**{current_experience.get('title').title() if current_experience.get('title') else None} | {current_experience.get('company').strip() if current_experience.get('company').strip() else None}**  "
            for current_experience in self.linkedin_profile.get("experiences")
            if not current_experience.get("ends_at")
        )

        profile_info_markdown = (
            f"# {self.linkedin_profile.get('full_name').title()}\n"
            f"{current_experience_lines}  \n"
            f"{self.linkedin_profile.get('city')}, {self.linkedin_profile.get('state')}, {self.linkedin_profile.get('country')}  \n"
            f"🔗 [LinkedIn]({linkedin_url})  \n"
        )

        # with st.spinner("Generating opportunities..."):
        #     opportunities = self.opportunities_chain()
        #     opportunities_with_citations = self.add_citations_chain(
        #         opportunities,
        #         context={
        #             f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile,
        #             **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies},
        #             **{f"[{self.citation_list.index(company_website) + 1}]": company_website for company_website in self.companies_websites}
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Opportunities generated...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Identifying talking points..."):
        #     sleep(60)
        #     talking_point = self.talking_point_chain()
        #     sources = []
        #
        #     potential_sources = [
        #         self.linkedin_profile,
        #         self.posts,
        #         self.comments,
        #         self.google_news,
        #         self.publications
        #     ]
        #
        #     for source in potential_sources:
        #         if source in self.citation_list:
        #             index = self.citation_list.index(source) + 1
        #
        #             if source == self.posts:
        #                 data = [post.get("text") for post in self.posts if post.get("text")]
        #             elif source == self.comments:
        #                 data = [comment.get("comment_text") for comment in self.comments if comment.get("comment_text")]
        #             else:
        #                 data = source
        #
        #             if data and not (isinstance(data, (list, dict)) and not data):
        #                 sources.append((data, index))
        #
        #     talking_point_with_citations = self.add_citations_chain(
        #         talking_point,
        #         context={
        #             f"[{index}]": data
        #             for data, index in sources
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Talking points identified...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Analyzing engagement highlights..."):
        #     sleep(60)
        #     engagement_highlights = self.engagement_highlights_chain()
        #
        #     context = {}
        #
        #     if self.posts in self.citation_list:
        #         posts_content = [{"text": post.get("text"), "stats": post.get("stats")} for post in self.posts if post.get("text")]
        #         if posts_content:
        #             index = self.citation_list.index(self.posts) + 1
        #             context[f"[{index}]"] = posts_content
        #
        #     engagement_highlights_with_citations = self.add_citations_chain(
        #         engagement_highlights,
        #         context=context
        #     )
        # st.markdown('<span style="color:black;">✅ Engagement highlights analyzed...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Preparing objection handling strategies..."):
        #     sleep(60)
        #     objection_handling = self.objection_handling_chain()
        #     objection_handling_with_citations = self.add_citations_chain(
        #         objection_handling,
        #         context={
        #             f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile,
        #             **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies},
        #             **{f"[{self.citation_list.index(company_website) + 1}]": company_website for company_website in self.companies_websites}
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Objection handling strategies prepared...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Identifying trigger events and timing..."):
        #     sleep(60)
        #     trigger_events_and_timing = self.trigger_events_and_timing_chain()
        #     context = {}
        #
        #     if self.posts in self.citation_list:
        #         posts_content = [post.get("text") for post in self.posts if post.get("text")]
        #         if posts_content:
        #             index = self.citation_list.index(self.posts) + 1
        #             context[f"[{index}]"] = posts_content
        #
        #     trigger_events_and_timing_with_citations = self.add_citations_chain(
        #         trigger_events_and_timing,
        #         context={
        #             **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies},
        #             **{f"[{self.citation_list.index(company_website) + 1}]": company_website for company_website in self.companies_websites},
        #             **context
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Trigger events and timing identified ...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Determining engagement style..."):
        #     sleep(60)
        #     engagement_style = self.engagement_style_chain()
        #
        #     context = {}
        #
        #     if self.posts in self.citation_list:
        #         posts_content = [post.get("text") for post in self.posts if post.get("text")]
        #         if posts_content:
        #             index = self.citation_list.index(self.posts) + 1
        #             context[f"[{index}]"] = posts_content
        #
        #     if self.comments in self.citation_list:
        #         comments_content = [comment.get("comment_text") for comment in self.comments if
        #                             comment.get("comment_text")]
        #         if comments_content:
        #             index = self.citation_list.index(self.comments) + 1
        #             context[f"[{index}]"] = comments_content
        #
        #     engagement_style_with_citations = self.add_citations_chain(
        #         engagement_style,
        #         context=context
        #     )
        # st.markdown('<span style="color:black;">✅ Engagement style determined...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Analyzing company information..."):
        #     sleep(60)
        #     about_company = self.about_company_chain()
        #     about_company_with_citations = self.add_citations_chain(
        #         about_company,
        #         context={
        #             **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies},
        #             **{f"[{self.citation_list.index(company_website) + 1}]": company_website for company_website in self.companies_websites}
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Company information Analyzed...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Analyzing LinkedIn data..."):
        #     sleep(60)
        #     linkedin_data = self.linkedin_data_chain()
        #     linkedin_data_with_citations = self.add_citations_chain(
        #         linkedin_data,
        #         context={
        #             f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile,
        #             **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies}
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Linkedin information analyzed...</span>', unsafe_allow_html=True)
        #
        # outreach_email_input = {
        #     "opportunities": opportunities,
        #     "talking_point": talking_point,
        #     "engagement_highlights": engagement_highlights,
        #     "objection_handling": objection_handling,
        #     "trigger_events_and_timing": trigger_events_and_timing,
        #     "engagement_style": engagement_style,
        #     "about_company": about_company,
        #     "linkedin_data": linkedin_data,
        #     "sell_for_education": self.knowledge_base.get("sell_for_education"),
        #     "sell_for_enterprise": self.knowledge_base.get("sell_for_enterprise"),
        #     "knowledge_insights": self.knowledge_base.get("knowledge_insights"),
        #     "pitches": self.knowledge_base.get("pitches"),
        #     "access_ai": self.knowledge_base.get("ai_summary"),
        # }
        #
        # with st.spinner("Crafting personalized outreach email..."):
        #     outreach_email = self.outreach_email_chain(outreach_email_input)
        # st.markdown('<span style="color:black;">✅ Personalized outreach email crafted...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Adding additional outreaches..."):
        #     sleep(60)
        #     additional_suggested_outreach = self.suggested_additional_outreach()
        #     additional_outreach_with_citations = self.add_citations_chain(
        #         additional_suggested_outreach,
        #         context={
        #             f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile
        #         }
        #     )
        # st.markdown('<span style="color:black;">✅ Additional outreaches added...</span>', unsafe_allow_html=True)
        #
        # with st.spinner("Analyzing google publications..."):
        #     sleep(60)
        #     google_publications = self.publications_chain()
        #
        #     context = {}
        #
        #     if self.publications in self.citation_list and self.publications:
        #         if not (isinstance(self.publications, (list, dict)) and not self.publications):
        #             index = self.citation_list.index(self.publications) + 1
        #             context[f"[{index}]"] = self.publications
        #
        #     google_publications_with_citations = self.add_citations_chain(
        #         google_publications,
        #         context=context
        #     )
        # st.markdown('<span style="color:black;">✅ Google Publications Analyzed...</span>', unsafe_allow_html=True)

        with st.spinner("Analyzing google news..."):
            google_news = self.news_chain()
            self.news_availabilty = self.check_news_available(google_news)
            google_news_with_citations = google_news

            if self.news_availabilty.news_available:
                context = {}
                if self.google_news in self.citation_list and self.google_news:
                    if not (isinstance(self.google_news, (list, dict)) and not self.google_news):
                        index = self.citation_list.index(self.google_news) + 1
                        context[f"[{index}]"] = self.google_news

                google_news_with_citations = self.add_citations_chain(
                    google_news,
                    context={
                        f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile,
                        **context
                    }
                )
        st.markdown('<span style="color:black;">✅ Google News Analyzed...</span>', unsafe_allow_html=True)

#         sales_insights_markdown_with_citations = f"""## Sales Insights
# {talking_point_with_citations}
# {opportunities_with_citations}
# {engagement_style_with_citations}
# """
#
#         citations = self.create_citations(linkedin_url)
#         return (
#             f"{profile_info_markdown}\n\n{sales_insights_markdown_with_citations}\n\n{objection_handling_with_citations}\n\n"
#             f"{trigger_events_and_timing_with_citations}\n\n{engagement_highlights_with_citations}\n\n{about_company_with_citations}\n\n"
#             f"{linkedin_data_with_citations}\n\n{google_publications_with_citations}\n\n{google_news_with_citations}\n\n"
#             f"{outreach_email}\n\n{additional_outreach_with_citations}\n\n{citations}"
#         )

        return (f"{profile_info_markdown}\n\n{google_news_with_citations}\n")