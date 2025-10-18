"""
Pydantic schemas for conversation state and image generation
"""
from pydantic import BaseModel
from typing import Optional


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


