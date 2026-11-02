"""ORM 模型统一出口：导入本包即可让 Base.metadata 收集全部 14 张表。"""
from app.models.activity import Activity
from app.models.activity_signup import ActivitySignup
from app.models.ai_message import AiMessage
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.club import Club
from app.models.club_application import ClubApplication
from app.models.club_member import ClubMember
from app.models.content import Content
from app.models.intent import TradeIntent
from app.models.item import Item
from app.models.notification import Notification
from app.models.report import Report
from app.models.user import User

__all__ = [
    "Activity",
    "ActivitySignup",
    "AiMessage",
    "AuditLog",
    "Category",
    "Club",
    "ClubApplication",
    "ClubMember",
    "Content",
    "Item",
    "Notification",
    "Report",
    "TradeIntent",
    "User",
]
