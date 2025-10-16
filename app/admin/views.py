"""
Admin panel model views
"""
from sqladmin import ModelView
from app.db.models import User, Persona, PersonaHistoryStart, Chat, Message, ImageJob


class UserAdmin(ModelView, model=User):
    """Admin view for User model"""
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    
    # List page
    column_list = [User.id, User.username, User.first_name, User.locale, User.created_at]
    column_searchable_list = [User.username, User.first_name]
    column_sortable_list = [User.id, User.username, User.created_at]
    column_default_sort = [(User.created_at, True)]
    
    # Details/Form
    column_details_exclude_list = [User.settings]
    form_excluded_columns = [User.chats, User.personas]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 50


class PersonaAdmin(ModelView, model=Persona):
    """Admin view for Persona model"""
    name = "Persona"
    name_plural = "Personas"
    icon = "fa-solid fa-robot"
    
    # List page
    column_list = [
        Persona.name, 
        Persona.key, 
        Persona.visibility, 
        Persona.owner_user_id,
        Persona.created_at
    ]
    column_searchable_list = [Persona.name, Persona.key, Persona.description]
    column_sortable_list = [Persona.name, Persona.key, Persona.visibility, Persona.created_at]
    column_default_sort = [(Persona.created_at, True)]
    column_filters = [Persona.visibility, Persona.owner_user_id]
    
    # Details/Form
    form_excluded_columns = [Persona.chats, Persona.history_starts, Persona.owner]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 50


class PersonaHistoryStartAdmin(ModelView, model=PersonaHistoryStart):
    """Admin view for PersonaHistoryStart model"""
    name = "Persona Greeting"
    name_plural = "Persona Greetings"
    icon = "fa-solid fa-comment"
    
    # List page
    column_list = [
        PersonaHistoryStart.persona_id,
        PersonaHistoryStart.text,
        PersonaHistoryStart.image_url,
        PersonaHistoryStart.created_at
    ]
    column_searchable_list = [PersonaHistoryStart.text]
    column_sortable_list = [PersonaHistoryStart.persona_id, PersonaHistoryStart.created_at]
    column_default_sort = [(PersonaHistoryStart.created_at, True)]
    column_filters = [PersonaHistoryStart.persona_id]
    
    # Details/Form
    form_excluded_columns = [PersonaHistoryStart.persona]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 50


class ChatAdmin(ModelView, model=Chat):
    """Admin view for Chat model"""
    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"
    
    # List page
    column_list = [
        Chat.tg_chat_id,
        Chat.user_id,
        Chat.persona_id,
        Chat.mode,
        Chat.created_at,
        Chat.updated_at
    ]
    column_searchable_list = [Chat.tg_chat_id]
    column_sortable_list = [
        Chat.tg_chat_id, 
        Chat.user_id, 
        Chat.created_at,
        Chat.updated_at,
        Chat.last_user_message_at
    ]
    column_default_sort = [(Chat.updated_at, True)]
    column_filters = [Chat.mode, Chat.user_id, Chat.persona_id]
    
    # Details/Form
    form_excluded_columns = [Chat.messages, Chat.user, Chat.persona]
    column_details_exclude_list = [Chat.state_snapshot, Chat.settings]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 50


class MessageAdmin(ModelView, model=Message):
    """Admin view for Message model"""
    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-message"
    
    # List page
    column_list = [
        Message.chat_id,
        Message.role,
        Message.text,
        Message.is_processed,
        Message.created_at
    ]
    column_searchable_list = [Message.text]
    column_sortable_list = [Message.chat_id, Message.role, Message.created_at]
    column_default_sort = [(Message.created_at, True)]
    column_filters = [Message.role, Message.is_processed, Message.chat_id]
    
    # Details/Form
    form_excluded_columns = [Message.chat]
    column_details_exclude_list = [Message.media, Message.state_snapshot]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 100


class ImageJobAdmin(ModelView, model=ImageJob):
    """Admin view for ImageJob model"""
    name = "Image Job"
    name_plural = "Image Jobs"
    icon = "fa-solid fa-image"
    
    # List page
    column_list = [
        ImageJob.id,
        ImageJob.user_id,
        ImageJob.persona_id,
        ImageJob.status,
        ImageJob.created_at,
        ImageJob.finished_at
    ]
    column_searchable_list = [ImageJob.prompt]
    column_sortable_list = [
        ImageJob.status,
        ImageJob.user_id,
        ImageJob.created_at,
        ImageJob.finished_at
    ]
    column_default_sort = [(ImageJob.created_at, True)]
    column_filters = [ImageJob.status, ImageJob.user_id, ImageJob.persona_id]
    
    # Details/Form
    column_details_exclude_list = [ImageJob.ext]
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 50

