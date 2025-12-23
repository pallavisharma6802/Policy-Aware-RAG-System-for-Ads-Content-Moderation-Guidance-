from sqlalchemy import Column, String, Integer, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class PolicySource(str, enum.Enum):
    GOOGLE = "google"

class Region(str, enum.Enum):
    GLOBAL = "global"
    US = "us"
    EU = "eu"
    UK = "uk"

class ContentType(str, enum.Enum):
    AD_TEXT = "ad_text"
    IMAGE = "image"
    VIDEO = "video"
    LANDING_PAGE = "landing_page"
    GENERAL = "general"

class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    
    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(String(255), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    
    chunk_text = Column(Text, nullable=False)
    
    policy_source = Column(Enum(PolicySource), nullable=False, index=True)
    policy_section = Column(String(255), nullable=False, index=True)
    policy_section_level = Column(String(10), nullable=False)
    
    region = Column(Enum(Region), nullable=False, default=Region.GLOBAL, index=True)
    content_type = Column(Enum(ContentType), nullable=False, default=ContentType.GENERAL, index=True)
    
    effective_date = Column(DateTime, nullable=True)
    doc_url = Column(String(512), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<PolicyChunk(doc_id={self.doc_id}, section={self.policy_section}, level={self.policy_section_level})>"
