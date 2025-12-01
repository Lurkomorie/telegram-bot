"""
Pydantic schemas for conversation state and image generation
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class RelationshipState(BaseModel):
    """Relationship tracking state"""
    relationshipStage: str  # stranger|acquaintance|friend|crush|lover|partner|ex
    emotions: str  # 2-10 words describing current emotional state
    moodNotes: str  # Brief notes about environmental factors, fatigue, etc.


class SceneState(BaseModel):
    """Scene description state"""
    location: str  # MUST be specific: "cozy bedroom with fireplace" not "living room"
    description: str  # 1-2 sentences about current scene in present tense
    aiClothing: str  # MUST be specific: "red lace lingerie" not "casual outfit"
    userClothing: str  # User's clothing if known, 'unchanged', or 'unknown'


class MetaState(BaseModel):
    """Metadata about conversation"""
    terminateDialog: bool = False
    terminateReason: str = ""


class FullState(BaseModel):
    """Complete conversation state (mirrors reference implementation)"""
    rel: RelationshipState
    scene: SceneState
    meta: MetaState


class SDXLImagePlan(BaseModel):
    """SDXL image generation tag plan"""
    composition_tags: list[str]  # Shot type, camera angle, spatial positioning
    action_tags: list[str]  # Pose and physical actions
    clothing_tags: list[str]  # Clothing or nudity state
    atmosphere_tags: list[str]  # Mood, environment, lighting
    expression_tags: list[str]  # Facial expression and emotion
    metadata_tags: list[str]  # Intensity level, gender tags, style tags


# ========== SYSTEM MESSAGE SCHEMAS ==========

class SystemMessageButton(BaseModel):
    """Button configuration for system messages"""
    text: str
    url: Optional[str] = None
    callback_data: Optional[str] = None
    web_app: Optional[dict] = None  # {"url": "..."}


class SystemMessageCreate(BaseModel):
    """Input schema for creating system messages"""
    title: Optional[str] = None
    text: str
    media_type: Literal['none', 'photo', 'video', 'animation'] = 'none'
    media_url: Optional[str] = None
    buttons: Optional[List[SystemMessageButton]] = None
    target_type: Literal['all', 'user', 'users', 'group']
    target_user_ids: Optional[List[int]] = None
    target_group: Optional[str] = None
    send_immediately: bool = False
    scheduled_at: Optional[datetime] = None
    parse_mode: Literal['HTML', 'MarkdownV2'] = 'HTML'
    disable_web_page_preview: bool = False
    template_id: Optional[UUID] = None


class SystemMessageUpdate(BaseModel):
    """Input schema for updating system messages"""
    title: Optional[str] = None
    text: Optional[str] = None
    media_type: Optional[Literal['none', 'photo', 'video', 'animation']] = None
    media_url: Optional[str] = None
    buttons: Optional[List[SystemMessageButton]] = None
    target_type: Optional[Literal['all', 'user', 'users', 'group']] = None
    target_user_ids: Optional[List[int]] = None
    target_group: Optional[str] = None
    send_immediately: Optional[bool] = None
    scheduled_at: Optional[datetime] = None
    parse_mode: Optional[Literal['HTML', 'MarkdownV2']] = None
    disable_web_page_preview: Optional[bool] = None


class SystemMessageResponse(BaseModel):
    """Output schema for system messages"""
    id: UUID
    title: Optional[str]
    text: str
    media_type: str
    media_url: Optional[str]
    buttons: Optional[List[dict]]
    target_type: str
    target_user_ids: Optional[List[int]]
    target_group: Optional[str]
    status: str
    send_immediately: bool
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    created_by: Optional[str]
    ext: Optional[dict]
    template_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SystemMessageTemplateCreate(BaseModel):
    """Input schema for creating templates"""
    name: str
    title: Optional[str] = None
    text: str
    media_type: Literal['none', 'photo', 'video', 'animation'] = 'none'
    media_url: Optional[str] = None
    buttons: Optional[List[SystemMessageButton]] = None


class SystemMessageTemplateUpdate(BaseModel):
    """Input schema for updating templates"""
    name: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    media_type: Optional[Literal['none', 'photo', 'video', 'animation']] = None
    media_url: Optional[str] = None
    buttons: Optional[List[SystemMessageButton]] = None
    is_active: Optional[bool] = None


class SystemMessageTemplateResponse(BaseModel):
    """Output schema for templates"""
    id: UUID
    name: str
    title: Optional[str]
    text: str
    media_type: str
    media_url: Optional[str]
    buttons: Optional[List[dict]]
    created_by: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeliveryStatusResponse(BaseModel):
    """Delivery tracking schema"""
    id: UUID
    system_message_id: UUID
    user_id: int
    status: str
    error: Optional[str]
    retry_count: int
    max_retries: int
    sent_at: Optional[datetime]
    message_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeliveryStatsResponse(BaseModel):
    """Delivery statistics schema"""
    total: int
    sent: int
    failed: int
    blocked: int
    pending: int
    success_rate: float
