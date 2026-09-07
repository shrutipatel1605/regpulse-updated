"""SQLAlchemy ORM models for RegPulse."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can discover them
from app.models.admin import AdminAuditLog, AnalyticsEvent, PromptVersion  # noqa: E402, F401
from app.models.circular import CircularDocument, DocumentChunk  # noqa: E402, F401
from app.models.debate import DebateReply, DebateThread  # noqa: E402, F401
from app.models.kg import KGEntity, KGRelationship  # noqa: E402, F401
from app.models.learning import Learning  # noqa: E402, F401
from app.models.news import NewsItem  # noqa: E402, F401
from app.models.question import ActionItem, Question, SavedInterpretation  # noqa: E402, F401
from app.models.scraper import ScraperRun  # noqa: E402, F401
from app.models.snippet import PublicSnippet  # noqa: E402, F401
from app.models.subscription import SubscriptionEvent  # noqa: E402, F401
from app.models.user import PendingDomainReview, Session, User  # noqa: E402, F401
