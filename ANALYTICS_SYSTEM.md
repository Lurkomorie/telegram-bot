# Telegram Bot Analytics System

## Overview

Complete analytics system for tracking all user interactions with the Telegram bot. Includes event tracking, Cloudflare image storage, and a React dashboard for viewing statistics and user timelines.

## Features

- **Comprehensive Event Tracking**: Tracks every user interaction including messages, commands, image generations, persona selections, and more
- **Non-Blocking Architecture**: All analytics operations run in the background using `asyncio.create_task()` to ensure they never slow down the bot
- **Cloudflare Image Storage**: Automatically uploads generated images to Cloudflare CDN for permanent archival (analytics only)
- **React Analytics Dashboard**: Beautiful, minimalistic dashboard built with React and Tailwind CSS
- **Real-time Statistics**: View total users, messages, images, active users, and popular personas
- **User Timeline View**: See complete interaction history for any user with visual message bubbles

## Architecture

### Database Layer

- **Table**: `tg_analytics_events`
- **Fields**:
  - `client_id`: Telegram user ID
  - `event_name`: Type of event (user_message, ai_message, image_generated, etc.)
  - `persona_id`, `persona_name`: Associated persona information
  - `message`: Message content (for text events)
  - `prompt`, `negative_prompt`: Image generation prompts
  - `image_url`: Cloudflare CDN URL (for images)
  - `meta`: Additional metadata (JSONB)
  - `created_at`: Timestamp

### Services

#### 1. Analytics Service (`app/core/analytics_service_tg.py`)

Main service for tracking events. All tracking functions are non-blocking:

- `track_start_command()` - /start command
- `track_user_message()` - User sends message
- `track_ai_message()` - AI responds
- `track_image_generated()` - Image created (with Cloudflare upload)
- `track_image_refresh()` - User refreshes image
- `track_persona_selected()` - Persona chosen
- `track_story_selected()` - Story chosen
- `track_chat_cleared()` - /clear command
- `track_chat_continued()` - Continue conversation
- `track_premium_action()` - Premium-related events

#### 2. Cloudflare Upload Service (`app/core/cloudflare_upload.py`)

Handles image uploads to Cloudflare CDN:

- Supports both URL and binary data uploads
- Automatic retry logic with exponential backoff
- File size validation
- Returns permanent CDN URLs

### Analytics API (`app/api/analytics.py`)

RESTful API endpoints:

- `GET /api/analytics/stats` - Overall statistics
- `GET /api/analytics/users` - All users with event counts
- `GET /api/analytics/users/{client_id}/events` - User event timeline

### React Dashboard (`/analytics-dashboard`)

Built with:

- **React 18** - UI framework
- **Vite 5** - Build tool (Node 18 compatible)
- **Tailwind CSS** - Styling
- **React Router** - Client-side routing

**Pages:**

1. **Statistics** - Dashboard with key metrics and popular personas
2. **Users** - Table of all users with activity information
3. **User Timeline** - Detailed event timeline for individual users

## Integration Points

### Bot Handlers

Analytics tracking integrated into:

- `app/bot/handlers/start.py` - /start command, persona/story selection, continue chat
- `app/bot/handlers/chat.py` - User messages, /clear command
- `app/bot/handlers/image.py` - Image refresh requests
- `app/core/multi_brain_pipeline.py` - AI message tracking
- `app/main.py` - Image generation completion tracking

### Non-Blocking Guarantee

All tracking calls use:

```python
asyncio.create_task(track_event_tg(...))
```

This ensures analytics never blocks the main bot operations.

## Deployment

### 1. Database Migration

Run the migration to create the analytics table:

```bash
alembic upgrade head
```

### 2. Environment Variables

Add to your `.env`:

```env
CLOUDFLARE_API_TOKEN=your_token_here
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_ACCOUNT_HASH=your_account_hash_here
```

### 3. Build Analytics Dashboard

```bash
cd analytics-dashboard
npm install
npm run build
```

### 4. Restart Application

The analytics system will automatically:

- Start tracking events on all bot interactions
- Upload images to Cloudflare in the background
- Serve the dashboard at `/analytics`

## Accessing the Dashboard

Once deployed, access the analytics dashboard at:

```
https://your-app-url.com/analytics
```

The dashboard includes:

- **Statistics page** - Overview with metrics and popular personas
- **Users page** - List of all users with activity stats
- **User Timeline** - Click any user to see their complete interaction history

## Visual Design

### Timeline Layout

- **User messages**: Right side, blue bubbles
- **AI messages**: Left side, gray bubbles, with persona name
- **Images**: Left side with full image display
- **Commands**: Center, as gray badges (/start, /clear, etc.)
- **Events**: Center, as gray badges (persona selected, story selected, etc.)

### Color Scheme

- Minimalistic design with clean white backgrounds
- Blue accents for interactive elements
- Gray tones for secondary information
- Colored stat cards for key metrics

## Performance Considerations

1. **Non-Blocking Operations**: All analytics run in background tasks
2. **Database Indexing**: Optimized indexes on `client_id`, `event_name`, and `created_at`
3. **Batch Operations**: Uses efficient bulk queries for statistics
4. **Error Isolation**: Analytics failures never crash the main bot
5. **Cloudflare CDN**: Fast image delivery through global CDN

## Event Types Tracked

- `start_command` - User runs /start
- `user_message` - User sends text message
- `ai_message` - AI responds with text
- `image_generated` - Image created and delivered
- `image_refresh` - User refreshes an image
- `persona_selected` - User selects a persona
- `story_selected` - User selects a story
- `chat_cleared` - User runs /clear
- `chat_continued` - User continues existing chat
- `premium_action` - Premium-related actions
- `command` - Generic command execution

## Monitoring

Check analytics system health:

1. Look for `[ANALYTICS]` logs in application output
2. Verify Cloudflare uploads with `[CLOUDFLARE]` logs
3. Check API endpoints are accessible at `/api/analytics/stats`
4. Access dashboard at `/analytics` to verify UI is working

## Troubleshooting

### Analytics not appearing in dashboard

- Check database migration ran successfully
- Verify environment variables are set
- Check application logs for `[ANALYTICS]` errors

### Images not showing in timeline

- Verify Cloudflare credentials are correct
- Check `[CLOUDFLARE]` logs for upload errors
- Ensure images are being generated successfully

### Dashboard not loading

- Verify `analytics-dashboard/dist` exists
- Check build was successful with `npm run build`
- Look for mount message in app startup logs

## Future Enhancements

Potential additions:

- Export data to CSV
- Date range filtering
- Real-time updates via WebSocket
- Advanced charts and graphs
- User segmentation
- Retention analysis
- A/B testing support

## Technical Stack

**Backend:**

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic (migrations)
- aiohttp (Cloudflare uploads)

**Frontend:**

- React 18
- Vite 5
- Tailwind CSS 3
- React Router 6

**Infrastructure:**

- Cloudflare Images CDN
- Non-blocking async architecture
