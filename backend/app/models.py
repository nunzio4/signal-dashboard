from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


# ── LLM structured output schema ──

class ThesisSignalExtraction(BaseModel):
    thesis_id: str
    is_relevant: bool
    direction: Optional[Literal["supporting", "weakening"]] = None
    strength: Optional[int] = Field(default=None, ge=0, le=10)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_quote: Optional[str] = None
    reasoning: Optional[str] = None

    @model_validator(mode="after")
    def fill_defaults_for_irrelevant(self):
        """When not relevant, fill safe defaults so downstream code doesn't break."""
        if not self.is_relevant:
            if self.direction is None:
                self.direction = "supporting"
            if self.strength is None or self.strength == 0:
                self.strength = 1
            if self.confidence is None:
                self.confidence = 0.0
            if self.evidence_quote is None:
                self.evidence_quote = ""
            if self.reasoning is None:
                self.reasoning = ""
        else:
            # Relevant signals must have values — apply defaults if LLM omitted them
            if self.direction is None:
                self.direction = "supporting"
            if self.strength is None or self.strength == 0:
                self.strength = 1
            if self.confidence is None:
                self.confidence = 0.5
            if self.evidence_quote is None:
                self.evidence_quote = ""
            if self.reasoning is None:
                self.reasoning = ""
            # Truncate strings if LLM exceeded expected lengths
            self.evidence_quote = self.evidence_quote[:500]
            self.reasoning = self.reasoning[:500]
        return self


class ArticleAnalysisResult(BaseModel):
    signals: list[ThesisSignalExtraction]
    summary: Optional[str] = None

    @model_validator(mode="after")
    def truncate_summary(self):
        if self.summary and len(self.summary) > 500:
            self.summary = self.summary[:500]
        if self.summary is None:
            self.summary = ""
        return self


# ── API request models ──

class ManualSignalCreate(BaseModel):
    thesis_id: str
    direction: Literal["supporting", "weakening"]
    strength: int = Field(ge=1, le=10)
    evidence_quote: str
    reasoning: str
    source_title: str | None = None
    source_url: str | None = None
    signal_date: str | None = None


class SourceCreate(BaseModel):
    name: str
    source_type: Literal["rss", "newsapi", "manual"]
    url: str | None = None
    config: str | None = None
    enabled: bool = True


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    config: str | None = None
    enabled: bool | None = None


# ── API response models ──

class ThesisResponse(BaseModel):
    id: str
    name: str
    description: str
    keywords: list[str]


class SignalResponse(BaseModel):
    id: int
    thesis_id: str
    direction: str
    strength: int
    confidence: float
    evidence_quote: str
    reasoning: str
    source_title: str | None
    source_url: str | None
    signal_date: str
    is_manual: bool
    signal_type: str = "news"
    created_at: str | None = None


class TrendPoint(BaseModel):
    date: str
    score: float
    count: int


class ThesisDashboardData(BaseModel):
    thesis_id: str
    thesis_name: str
    thesis_description: str
    current_score: float
    previous_score: float | None
    score_trend: str  # 'rising', 'falling', 'stable'
    trend_data: list[TrendPoint]
    recent_signals: list[SignalResponse]
    news_signals_7d: int
    news_signals_24h: int
    data_signals_7d: int
    data_signals_24h: int


class DashboardResponse(BaseModel):
    theses: list[ThesisDashboardData]
    last_ingestion: str | None
    last_data_fetch: str | None
    next_ingestion: str | None
    next_data_fetch: str | None
    total_articles: int
    total_news_signals: int
    total_data_signals: int
    news_signals_24h: int
    data_signals_24h: int
    articles_24h: int
    total_data_points: int
    data_points_24h: int


class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    url: str | None
    config: str | None
    enabled: bool
    last_fetched_at: str | None
    created_at: str


class ArticleResponse(BaseModel):
    id: int
    source_id: int | None
    title: str
    url: str | None
    author: str | None
    published_at: str | None
    ingested_at: str
    analysis_status: str


class IngestionStatusResponse(BaseModel):
    last_run: str | None
    articles_total: int
    articles_pending: int
    articles_analyzed: int
    sources_enabled: int
