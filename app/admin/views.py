"""
Admin panel model views with bulk delete support
"""
from sqladmin import ModelView, action
from wtforms import TextAreaField
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy import delete
from uuid import UUID
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
    can_export = True
    save_as = True
    page_size = 50
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Users",
        confirmation_message="Are you sure you want to delete ALL users? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all user records"""
        async with self.session_maker() as session:
            await session.execute(delete(User))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


class PersonaAdmin(ModelView, model=Persona):
    """Admin view for Persona model"""
    name = "Persona"
    name_plural = "Personas"
    icon = "fa-solid fa-robot"
    
    # List page
    column_list = [
        Persona.id,
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
    form_excluded_columns = [Persona.chats, Persona.history_starts]
    form_overrides = {
        "prompt": TextAreaField,
        "description": TextAreaField,
        "intro": TextAreaField,
    }
    form_ajax_refs = {
        "owner": {
            "fields": ("username", "first_name"),
            "order_by": "id",
        }
    }
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    save_as = True
    page_size = 50
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Personas",
        confirmation_message="Are you sure you want to delete ALL personas? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all persona records"""
        async with self.session_maker() as session:
            await session.execute(delete(Persona))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


class PersonaHistoryStartAdmin(ModelView, model=PersonaHistoryStart):
    """Admin view for PersonaHistoryStart model"""
    name = "Persona Greeting"
    name_plural = "Persona Greetings"
    icon = "fa-solid fa-comment"
    
    # List page
    column_list = [
        PersonaHistoryStart.id,
        PersonaHistoryStart.persona_id,
        PersonaHistoryStart.text,
        PersonaHistoryStart.image_url,
        PersonaHistoryStart.created_at
    ]
    column_searchable_list = [PersonaHistoryStart.text]
    column_sortable_list = [PersonaHistoryStart.persona_id, PersonaHistoryStart.created_at]
    column_default_sort = [(PersonaHistoryStart.created_at, True)]
    column_filters = [PersonaHistoryStart.persona_id]
    
    # Details/Form - Show persona as a relationship field
    form_overrides = {
        "text": TextAreaField,
    }
    form_ajax_refs = {
        "persona": {
            "fields": ("name", "key"),
            "order_by": "name",
        }
    }
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    save_as = True
    page_size = 50
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Greetings",
        confirmation_message="Are you sure you want to delete ALL persona greetings? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all greeting records"""
        async with self.session_maker() as session:
            await session.execute(delete(PersonaHistoryStart))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


class ChatAdmin(ModelView, model=Chat):
    """Admin view for Chat model"""
    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"
    
    # List page
    column_list = [
        Chat.id,
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
    form_excluded_columns = [Chat.messages]
    column_details_exclude_list = [Chat.state_snapshot, Chat.settings]
    form_ajax_refs = {
        "user": {
            "fields": ("username", "first_name"),
            "order_by": "id",
        },
        "persona": {
            "fields": ("name", "key"),
            "order_by": "name",
        }
    }
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    save_as = True
    page_size = 50
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Chats",
        confirmation_message="Are you sure you want to delete ALL chats? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all chat records"""
        async with self.session_maker() as session:
            await session.execute(delete(Chat))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


class MessageAdmin(ModelView, model=Message):
    """Admin view for Message model"""
    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-message"
    
    # List page
    column_list = [
        Message.id,
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
    column_details_exclude_list = [Message.media, Message.state_snapshot]
    form_overrides = {
        "text": TextAreaField,
    }
    form_ajax_refs = {
        "chat": {
            "fields": ("tg_chat_id",),
            "order_by": "created_at",
        }
    }
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    save_as = True
    page_size = 100
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Messages",
        confirmation_message="Are you sure you want to delete ALL messages? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all message records"""
        async with self.session_maker() as session:
            await session.execute(delete(Message))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


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
    form_overrides = {
        "prompt": TextAreaField,
        "negative_prompt": TextAreaField,
    }
    form_ajax_refs = {
        "user": {
            "fields": ("username", "first_name"),
            "order_by": "id",
        },
        "persona": {
            "fields": ("name", "key"),
            "order_by": "name",
        },
        "chat": {
            "fields": ("tg_chat_id",),
            "order_by": "created_at",
        }
    }
    
    # Display settings
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    save_as = True
    page_size = 50
    
    @action(
        name="delete_all",
        label="⚠️ Delete All Image Jobs",
        confirmation_message="Are you sure you want to delete ALL image jobs? This cannot be undone!",
        add_in_list=True,
        add_in_detail=False,
    )
    async def delete_all(self, request: Request):
        """Delete all image job records"""
        async with self.session_maker() as session:
            await session.execute(delete(ImageJob))
            await session.commit()
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))
