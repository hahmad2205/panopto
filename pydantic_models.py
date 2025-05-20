from typing import Union

from pydantic import BaseModel


class ScholarProfile(BaseModel):
    author_id: Union[str, None]


class AvailableNews(BaseModel):
    news_available: bool


class GoogleNewsConfig(BaseModel):
    title: str
    link: str


class GoogleNews(BaseModel):
    news: list[GoogleNewsConfig]
