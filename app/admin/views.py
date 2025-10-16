"""
Admin panel model views for Starlette-Admin
"""
from starlette_admin.contrib.sqla import ModelView
from app.db.models import User, Persona, PersonaHistoryStart, Chat, Message, ImageJob


class UserAdmin(ModelView):
    """Admin view for User model"""
    identity = "user"
    name = "User"
    label = "Users"
    icon = "fa fa-user"
    
    # List page
    fields = [
        User.id,
        User.username,
        User.first_name,
        User.locale,
        User.created_at,
        User.updated_at,
    ]
    
    searchable_fields = [User.username, User.first_name]
    sortable_fields = [User.id, User.username, User.created_at]
    
    # Exclude from forms
    exclude_fields_from_create = [User.created_at, User.updated_at, User.chats, User.personas]
    exclude_fields_from_edit = [User.created_at, User.updated_at, User.chats, User.personas]
    exclude_fields_from_detail = [User.settings]
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100]


class PersonaAdmin(ModelView):
    """Admin view for Persona model"""
    identity = "persona"
    name = "Persona"
    label = "Personas"
    icon = "fa fa-robot"
    
    # List page
    fields = [
        Persona.id,
        Persona.name,
        Persona.key,
        Persona.visibility,
        Persona.owner_user_id,
        Persona.created_at,
    ]
    
    searchable_fields = [Persona.name, Persona.key, Persona.description]
    sortable_fields = [Persona.name, Persona.key, Persona.visibility, Persona.created_at]
    
    # Exclude relationships from forms
    exclude_fields_from_create = [Persona.created_at, Persona.chats, Persona.history_starts]
    exclude_fields_from_edit = [Persona.created_at, Persona.chats, Persona.history_starts]
    exclude_fields_from_detail = []
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100]


class PersonaHistoryStartAdmin(ModelView):
    """Admin view for PersonaHistoryStart model"""
    identity = "persona_greeting"
    name = "Persona Greeting"
    label = "Persona Greetings"
    icon = "fa fa-comment"
    
    # List page
    fields = [
        PersonaHistoryStart.id,
        PersonaHistoryStart.persona,  # Show relationship
        PersonaHistoryStart.text,
        PersonaHistoryStart.image_url,
        PersonaHistoryStart.created_at,
    ]
    
    fields_default_sort = [(PersonaHistoryStart.created_at, True)]
    searchable_fields = [PersonaHistoryStart.text]
    
    # Exclude from forms
    exclude_fields_from_create = [PersonaHistoryStart.created_at]
    exclude_fields_from_edit = [PersonaHistoryStart.created_at]
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100]


class ChatAdmin(ModelView):
    """Admin view for Chat model"""
    identity = "chat"
    name = "Chat"
    label = "Chats"
    icon = "fa fa-comments"
    
    # List page
    fields = [
        Chat.id,
        Chat.tg_chat_id,
        Chat.user,  # Show relationship
        Chat.persona,  # Show relationship
        Chat.mode,
        Chat.created_at,
        Chat.updated_at,
    ]
    
    fields_default_sort = [(Chat.updated_at, True)]
    searchable_fields = [Chat.tg_chat_id]
    
    # Exclude from forms
    exclude_fields_from_create = [Chat.created_at, Chat.updated_at, Chat.messages]
    exclude_fields_from_edit = [Chat.created_at, Chat.updated_at, Chat.messages]
    exclude_fields_from_detail = [Chat.state_snapshot, Chat.settings]
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100]


class MessageAdmin(ModelView):
    """Admin view for Message model"""
    identity = "message"
    name = "Message"
    label = "Messages"
    icon = "fa fa-message"
    
    # List page
    fields = [
        Message.id,
        Message.chat,  # Show relationship
        Message.role,
        Message.text,
        Message.is_processed,
        Message.created_at,
    ]
    
    fields_default_sort = [(Message.created_at, True)]
    searchable_fields = [Message.text]
    
    # Exclude from forms
    exclude_fields_from_create = [Message.created_at]
    exclude_fields_from_edit = [Message.created_at]
    exclude_fields_from_detail = [Message.media, Message.state_snapshot]
    
    # Pagination
    page_size = 100
    page_size_options = [50, 100, 200]


class ImageJobAdmin(ModelView):
    """Admin view for ImageJob model"""
    identity = "image_job"
    name = "Image Job"
    label = "Image Jobs"
    icon = "fa fa-image"
    
    # List page
    fields = [
        ImageJob.id,
        ImageJob.user_id,
        ImageJob.persona,  # Show relationship
        ImageJob.status,
        ImageJob.created_at,
        ImageJob.finished_at,
    ]
    
    fields_default_sort = [(ImageJob.created_at, True)]
    searchable_fields = [ImageJob.prompt]
    
    # Exclude from forms
    exclude_fields_from_create = [ImageJob.created_at, ImageJob.finished_at]
    exclude_fields_from_edit = [ImageJob.created_at, ImageJob.finished_at]
    exclude_fields_from_detail = [ImageJob.ext]
    
    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100]
