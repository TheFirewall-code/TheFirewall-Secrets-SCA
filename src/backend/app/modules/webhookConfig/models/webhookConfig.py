from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from app.core.db import Base
import enum
from app.modules.vc.models.vc import VcTypes


class AllowedScanType(str, enum.Enum):
    loose = "Loose"
    aggressive = "Aggressive"

class EnumArray(TypeDecorator):
    impl = ARRAY(String)

    def __init__(self, enum_type: enum.Enum, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_type = enum_type

    def process_bind_param(self, value, dialect):
        if value is not None:
            return [
                e.value if isinstance(
                    e, self.enum_type) else e for e in value]
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return [self.enum_type(v) for v in value]
        return None


class BlockEnum(str, enum.Enum):
    block = "block"
    decline = "decline"


class WebhookConfig(Base):
    __tablename__ = 'webhook_configs'

    id = Column(Integer, primary_key=True, index=True)
    vc_id = Column(Integer, ForeignKey('vcs.id'), nullable=False, index=True)
    vc_type = Column(Enum(VcTypes), nullable=False)

    scan_type = Column(Enum(AllowedScanType))

    block_message = Column(String, nullable=True)
    unblock_message = Column(String, nullable=True)

    git_actions = Column(ARRAY(String))
    target_repos = Column(ARRAY(String))
    
    secret = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    
    # True is YES, False is NO
    block_pr_on_sec_found = Column(Boolean, default=True)
    block_pr_on_vul_found = Column(Boolean, default=False)
    jira_alerts_enabled = Column(Boolean, default=True)
    slack_alerts_enabled = Column(Boolean, default=True)

    # Relationships
    vc = relationship('VC', back_populates='webhook_configs')