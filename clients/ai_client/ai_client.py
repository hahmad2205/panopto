import dotenv
import streamlit as st
from decouple import config
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langsmith import Client as LangSmithClient

from clients.apify.website_crawl_actor import WebsiteCrawlActor
from pydantic_models import ScholarProfile, GoogleNews, AvailableNews
from streamlit_styles import processing_spinner_style
from supabase_client import supabase_client

dotenv.load_dotenv()


class AIClient:
    """
    This class analyzes prospect's data to generate a comprehensive Sales Development Representative (SDR) report.
    The report includes insights on the prospect's background, company information, engagement style, potential
    opportunities, and suggested outreach strategies.
    """

    def __init__(self, linkedin_profile_id):
        self.langsmith_client = LangSmithClient(api_key=config("LANGSMITH_API_KEY"))
        self.model = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model="google/gemini-2.5-flash-preview-04-17",
            api_key=config("OPEN_ROUTER_API_KEY"),
            temperature=0
        )
        self.news_availability = False

        self._initialize_sdr_data(linkedin_profile_id)

    def _initialize_sdr_data(self, linkedin_profile_id):
        profile = (
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

        if not profile:
            print("Failed to fetch LinkedIn profile:", profile.error)
            self.linkedin_profile = None
            self.companies = self.posts = self.comments = self.google_news = self.publications = self.companies_websites = []
            return

        self.linkedin_profile = profile
        self.companies = profile.get("sdr_agent_companylinkedinprofile", [])
        self.posts = profile.get("sdr_agent_linkedinpost", [])
        self.comments = profile.get("sdr_agent_linkedincomment", [])
        self.google_news = profile.get("sdr_agent_googlenews", [])
        self.scholar_profile = profile.get("sdr_agent_googlescholarprofile")
        self.publications = self.scholar_profile.get("sdr_agent_googlepublication", []) if self.scholar_profile else []

        self.companies_websites = [company.get("sdr_agent_companywebsite", []) for company in self.companies]

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

    def _linkedin_data_chain(self):
        input_data = {
            "summary": self.linkedin_profile.get("summary"),
            "headline": self.linkedin_profile.get("headline"),
            "experiences": self.linkedin_profile.get("experiences"),
            "education": self.linkedin_profile.get("education"),
            "certifications": self.linkedin_profile.get("certifications"),
            "industry": self.linkedin_profile.get("industry"),
            "company_description": [company.get("description") for company in self.companies],
            "skills": self.linkedin_profile.get("skills"),
            "recommendations": self.linkedin_profile.get("recommendations"),
        }
        return self._run_chain("linkedin_data_chain_prompt", input_data).content

    def _company_about_chain(self):
        return self._run_chain(
            "about_company_chain_prompt",
            {
                "linkedin_companies_profiles": self.companies,
                "linkedin_companies_websites": self.companies_websites,
            },
        ).content

    def _engagement_style_chain(self):
        return self._run_chain(
            "engagement_style_chain_prompt",
            {
                "linkedin_posts_caption": [post.get("text") for post in self.posts if not post.get("post_type") == "repost"],
                "linkedin_comments": [comment.get("comment_text") for comment in self.comments],
            },
        ).content

    def _suggested_additional_outreach_chain(self):
        return self._run_chain(
            "suggested_additional_outreach_chain_prompt",
            {
                "people_also_viewed": self.linkedin_profile.get("people_also_viewed"),
                "linkedin_headline": self.linkedin_profile.get("headline"),
                "linkedin_summary": self.linkedin_profile.get("summary"),
            },
        ).content

    def _talking_point_chain(self):
        return self._run_chain(
            "talking_point_chain_prompt",
            {
                "linkedin_experiences": self.linkedin_profile.get("experiences"),
                "linkedin_education": self.linkedin_profile.get("education"),
                "linkedin_posts": self.posts,
                "linkedin_comments": self.comments,
                "publications": self.user_publications,
                "news": self.user_google_news,
                "connect": self.knowledge_base.get("connect"),
                "ai_summary": self.knowledge_base.get("ai_summary"),
                "knowledge_insights": self.knowledge_base.get("knowledge_insights")
            },
        ).content

    def _opportunities_chain(self):
        return self._run_chain(
            "opportunities_chain_prompt",
            {
                "linkedin_companies_profiles": self.companies,
                "linkedin_companies_websites": self.companies_websites,
                "linkedin_headline": self.linkedin_profile.get("headline"),
                "sell_for_enterprise": self.knowledge_base.get("sell_for_enterprise"),
                "sell_for_education": self.knowledge_base.get("sell_for_education")
            },
        ).content

    def _engagement_highlights_chain(self):
        return self._run_chain(
            "engagement_highlights_chain_prompt",
            {
                "linkedin_posts": self.posts,
            },
        ).content

    def _trigger_events_and_timing_chain(self):
        return self._run_chain(
            "trigger_events_and_timing_chain_prompt",
            {
                "linkedin_posts": self.posts,
                "linkedin_companies": self.companies,
                "linkedin_companies_websites": self.companies_websites,
            },
        ).content

    def _objection_handling_chain(self):
        return self._run_chain(
            "objection_handling_prompt",
            {
                "linkedin_profile": self.linkedin_profile,
                "linkedin_companies": self.companies,
                "linkedin_companies_websites": self.companies_websites,
                "objection_handling": self.knowledge_base.get("objection_handling_context"),
                "competitors_insights": self.knowledge_base.get("insights_vs_competitors")
            },
        ).content

    def _outreach_email_chain(self, outreach_email_input):
        return self._run_chain(
            "outreach_email_chain_prompt",
            outreach_email_input
        ).content

    def _publications_chain(self):
        return self._run_chain(
            "publications_chain_prompt",
            {
                "publications": self.publications,
            }
        ).content

    def publication_author_chain(self, google_scholar_profiles):
        return self._run_chain(
            "google_scholar_profile_chain_prompt",
            {
                "google_scholar_profiles": google_scholar_profiles,
                "linkedin_profile": self.linkedin_profile,
            },
            PydanticOutputParser(pydantic_object=ScholarProfile)
        )

    def _google_news_content_chain(self):
        return self._run_chain(
            "news_chain_prompt",
            {
                "linkedin_profile": self.linkedin_profile,
                "google_news": self.google_news
            },
            PydanticOutputParser(pydantic_object=GoogleNews)
        )

    def _google_news_chain(self, news):
        return self._run_chain(
            "markdown_news_chain_prompt",
            {
                "linkedin_profile": self.linkedin_profile,
                "google_news": news
            }
        ).content

    def _check_google_news_availability_chain(self, news):
        return self._run_chain(
            "news_available_chain_prompt",
            {
                "news": news
            },
            PydanticOutputParser(pydantic_object=AvailableNews)
        )

    def _add_citations_chain(self, content, context):
        return self._run_chain(
            "add_citations_chain_prompt",
            {
                "content": content,
                "context": context
            }
        ).content

    def _process_google_news_content(self):
        """
        This method fetches top 3 Google News articles, crawls their content,
        generate structured news output and updates news availability.
        """

        google_news_content = self._google_news_content_chain()
        google_news_with_article_content = []

        top_news = google_news_content.news[:3] if hasattr(google_news_content, 'news') and isinstance(
            google_news_content.news, list) else []

        for news in top_news:
            article_crawler = WebsiteCrawlActor({"website_url": news.link})
            google_news_with_article_content.append({
                "title": news.title,
                "content": article_crawler.crawl_page()
            })

        google_news = self._google_news_chain(google_news_with_article_content)
        self.news_availability = self._check_google_news_availability_chain(google_news)

        return google_news

    def _create_citations(self, linkedin_url):
        citations = "## References\n"

        for index, citation_content in enumerate(self.citation_list, start=1):
            if citation_content == self.linkedin_profile:
                name = citation_content.get("full_name", "LinkedIn Profile")
                citations += f"{index}. [LinkedIn Profile - {name}]({linkedin_url})\n"

            elif citation_content in self.companies:
                name = citation_content.get("name", "Company Profile")
                url = f"https://www.linkedin.com/company/{citation_content.get('universal_name_id')}"
                citations += f"{index}. [LinkedIn Company Profile - {name}]({url})\n"

            elif citation_content in self.companies_websites:
                company_id = citation_content.get("company_profile_id")
                company_info = supabase_client.table("sdr_agent_companylinkedinprofile").select("name").eq("id",
                                                                                                           company_id).single().execute()
                name = company_info.data.get("name", "Company Website")
                url = citation_content.get("url", "#")
                citations += f"{index}. [Company Website - {name}]({url})\n"

            elif citation_content == self.posts:
                name = self.linkedin_profile.get("full_name", "Posts")
                url = f"{linkedin_url}{'' if linkedin_url.endswith('/') else '/'}recent-activity/all/"
                citations += f"{index}. [LinkedIn Posts - {name}]({url})\n"

            elif citation_content == self.comments:
                name = self.linkedin_profile.get("full_name", "Comments")
                url = f"{linkedin_url}{'' if linkedin_url.endswith('/') else '/'}recent-activity/comments/"
                citations += f"{index}. [LinkedIn Comments - {name}]({url})\n"

            elif citation_content == self.publications or citation_content == self.scholar_profile:
                name = self.scholar_profile.get("name", "Google Scholar")
                author_id = self.scholar_profile.get("author_id", "")
                url = f"https://scholar.google.com/citations?user={author_id}&hl=en&oi=ao"
                citations += f"{index}. [Google Publications - {name}]({url})\n"

            elif citation_content == self.google_news and self.news_availability.news_available:
                name = self.linkedin_profile.get("full_name", "Google News")
                query = name.replace(" ", "+")
                url = f"https://www.google.com/search?q={query}&tbm=nws"
                citations += f"{index}. [Google News - {name}]({url})\n"

        return citations

    def _create_profile_header_markdown(self, linkedin_url):
        current_experience_lines = "\n".join(
            f"{current_experience.get('title').title() if current_experience.get('title') else None} | {current_experience.get('company').strip() if current_experience.get('company').strip() else None}  "
            for current_experience in self.linkedin_profile.get("experiences")
            if not current_experience.get("ends_at")
        )

        profile_info_markdown = (
            f"# {self.linkedin_profile.get('full_name').title()}\n"
            f"{current_experience_lines}  \n"
            f"{self.linkedin_profile.get('city')}, {self.linkedin_profile.get('state')}, {self.linkedin_profile.get('country')}  \n"
            f"[LinkedIn]({linkedin_url})  \n"
        )
        return profile_info_markdown

    def _process_with_spinner(self, label, chain_function, citation_context_function=None):
        # try:
        with st.spinner(f"{label}..."):
            output = chain_function()
            if citation_context_function:
                context = citation_context_function()
                output = self._add_citations_chain(output, context)
            st.markdown(f'<span style="color:black;">✅ {label}...</span>',
                        unsafe_allow_html=True)
            return output
        # except Exception as e:
        #     st.markdown(f'<span style="color:black;">❌ {label} failed...</span>', unsafe_allow_html=True)
        #     return ""

    def _get_context_from_sources(self, sources):
        context = {}
        for source in sources:
            if source in self.citation_list:
                index = self.citation_list.index(source) + 1
                if source == self.posts:
                    data = [post.get("text") for post in source if post.get("text")]
                elif source == self.comments:
                    data = [comment.get("comment_text") for comment in source if comment.get("comment_text")]
                else:
                    data = source
                if data:
                    context[f"[{index}]"] = data
        return context

    def _get_company_context(self):
        return {
            **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies},
            **{f"[{self.citation_list.index(site) + 1}]": site for site in self.companies_websites},
        }

    def _get_profile_context(self):
        return {f"[{self.citation_list.index(self.linkedin_profile) + 1}]": self.linkedin_profile}

    def _get_google_news_context(self):
        result = {}
        if self.news_availability.news_available:
            context = {}

            if self.google_news in self.citation_list and self.google_news:
                if not (isinstance(self.google_news, (list, dict)) and not self.google_news):
                    index = self.citation_list.index(self.google_news) + 1
                    context[f"[{index}]"] = self.google_news

            result = context

        return result

    def _create_additional_outreach_email(self, llm_output):
        outreach_email_input = {
            "opportunities": llm_output.get("opportunities"),
            "talking_point": llm_output.get("talking_point"),
            "engagement_highlights": llm_output.get("engagement_highlights"),
            "objection_handling": llm_output.get("objection_handling"),
            "trigger_events_and_timing": llm_output.get("trigger_events_and_timing"),
            "engagement_style": llm_output.get("engagement_style"),
            "about_company": llm_output.get("about_company"),
            "linkedin_data": llm_output.get("linkedin_data"),
            "sell_for_education": self.knowledge_base.get("sell_for_education"),
            "sell_for_enterprise": self.knowledge_base.get("sell_for_enterprise"),
            "knowledge_insights": self.knowledge_base.get("knowledge_insights"),
            "pitches": self.knowledge_base.get("pitches"),
            "access_ai": self.knowledge_base.get("ai_summary"),
        }
        return self._process_with_spinner(
            "Crafting personalized outreach email",
            lambda: self._outreach_email_chain(outreach_email_input),
            None
        ) + "\n\n"

    def run_client(self, linkedin_url):
        processing_spinner_style()
        result = "## Sales Insights\n"
        llm_output = {}
        profile_info_markdown = self._create_profile_header_markdown(linkedin_url)

        self.user_google_news = self._process_with_spinner(
            "Analyzing google news",
            self._process_google_news_content,
            self._get_google_news_context
        ) + "\n\n"
        self.user_publications = self._process_with_spinner(
            "Analyzing google publications",
            self._publications_chain,
            lambda: self._get_context_from_sources([self.publications])
        ) + "\n\n"

        steps = [
            (
                "Generating opportunities", "opportunities", self._opportunities_chain,
                lambda: {
                    **self._get_profile_context(),
                    **self._get_company_context()
                }
            ),
            (
                "Identifying talking points", "talking_point", self._talking_point_chain,
                lambda: self._get_context_from_sources(
                    [self.linkedin_profile, self.posts, self.comments, self.google_news, self.publications]
                )
            ),
            (
                "Determining engagement style", "engagement_style", self._engagement_style_chain,
                lambda: self._get_context_from_sources(
                    [self.posts, self.comments]
                )
            ),
            (
                "Preparing objection handling strategies", "objection_handling",  self._objection_handling_chain,
                lambda: {
                    **self._get_profile_context(),
                    **self._get_company_context()
                }
            ),
            (
                "Identifying trigger events and timing", "trigger_events_and_timing", self._trigger_events_and_timing_chain,
                lambda: {
                    **self._get_company_context(),
                    **self._get_context_from_sources([self.posts])
                }
            ),
            (
                "Analyzing engagement highlights", "engagement_highlights", self._engagement_highlights_chain,
                lambda: self._get_context_from_sources([self.posts])
            ),
            (
                "Analyzing company information", "about_company", self._company_about_chain, self._get_company_context
            ),
            (
                "Analyzing LinkedIn data", "linkedin_data", self._linkedin_data_chain,
                lambda: {
                    **self._get_profile_context(),
                    **{f"[{self.citation_list.index(company) + 1}]": company for company in self.companies}
                }
            ),
        ]

        for label, key, chain_function, context_function in steps:
            llm_output[key] = self._process_with_spinner(label, chain_function, context_function)
            result += llm_output[key] + "\n\n"

        result += self.user_publications + self.user_google_news

        result += self._create_additional_outreach_email(llm_output)

        result += self._process_with_spinner(
            "Adding additional outreaches",
            self._suggested_additional_outreach_chain,
            self._get_profile_context
        ) + "\n\n"

        result += self._process_with_spinner(
            "Adding citations",
            lambda: self._create_citations(linkedin_url),
            None
        ) + "\n\n"

        return profile_info_markdown, result
