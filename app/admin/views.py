"""
Admin panel model views for Starlette-Admin
"""
from starlette_admin.contrib.sqla import ModelView
from app.db.models import User, Persona, PersonaHistoryStart, Chat, Message, ImageJob


class UserAdmin(ModelView):
    """Admin view for User model"""
    exclude_fields_from_list = [User.settings]
    exclude_fields_from_create = [User.created_at, User.updated_at, User.chats, User.personas, User.settings]
    exclude_fields_from_edit = [User.created_at, User.updated_at, User.chats, User.personas]
    exclude_fields_from_detail = [User.settings]
    
    searchable_fields = [User.username, User.first_name]
    sortable_fields = [User.id, User.username, User.created_at]
    
    page_size = 50
    page_size_options = [25, 50, 100]


class PersonaAdmin(ModelView):
    """Admin view for Persona model"""
    exclude_fields_from_create = [Persona.created_at, Persona.chats, Persona.history_starts]
    exclude_fields_from_edit = [Persona.created_at, Persona.chats, Persona.history_starts]
    
    searchable_fields = [Persona.name, Persona.key, Persona.description]
    sortable_fields = [Persona.name, Persona.key, Persona.visibility, Persona.created_at]
    
    page_size = 50
    page_size_options = [25, 50, 100]


class PersonaHistoryStartAdmin(ModelView):
    """Admin view for PersonaHistoryStart model"""
    exclude_fields_from_create = [PersonaHistoryStart.created_at]
    exclude_fields_from_edit = [PersonaHistoryStart.created_at]
    
    searchable_fields = [PersonaHistoryStart.text]
    
    page_size = 50
    page_size_options = [25, 50, 100]


class ChatAdmin(ModelView):
    """Admin view for Chat model"""
    exclude_fields_from_list = [Chat.state_snapshot, Chat.settings]
    exclude_fields_from_create = [Chat.created_at, Chat.updated_at, Chat.messages, Chat.state_snapshot, Chat.settings]
    exclude_fields_from_edit = [Chat.created_at, Chat.updated_at, Chat.messages]
    exclude_fields_from_detail = [Chat.state_snapshot, Chat.settings]
    
    searchable_fields = [Chat.tg_chat_id]
    
    page_size = 50
    page_size_options = [25, 50, 100]


class MessageAdmin(ModelView):
    """Admin view for Message model"""
    exclude_fields_from_list = [Message.media, Message.state_snapshot]
    exclude_fields_from_create = [Message.created_at, Message.state_snapshot]
    exclude_fields_from_edit = [Message.created_at, Message.state_snapshot]
    exclude_fields_from_detail = [Message.media, Message.state_snapshot]
    
    searchable_fields = [Message.text]
    
    page_size = 100
    page_size_options = [50, 100, 200]


class ImageJobAdmin(ModelView):
    """Admin view for ImageJob model"""
    exclude_fields_from_list = [ImageJob.ext]
    exclude_fields_from_create = [ImageJob.created_at, ImageJob.finished_at, ImageJob.ext]
    exclude_fields_from_edit = [ImageJob.created_at, ImageJob.finished_at]
    exclude_fields_from_detail = [ImageJob.ext]
    
    searchable_fields = [ImageJob.prompt]
    
    page_size = 50
    page_size_options = [25, 50, 100]
