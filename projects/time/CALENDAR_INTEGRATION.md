# Calendar Integration Implementation Guide

## Overview

This document provides comprehensive implementation guidance for integrating the Time project with external calendar services including Google Calendar, Microsoft Outlook, and Apple Calendar. The integration supports cross-platform compatibility (iOS, Android, Web), GDPR/CCPA compliance, and real-time collaboration features.

**Status**: Implementation guide - awaiting code development

## Supported Calendar Providers

- **Google Calendar** (via Google Calendar API v3)
- **Microsoft Outlook** (via Microsoft Graph API)
- **Apple Calendar** (via CalDAV protocol)
- **Generic CalDAV** (for self-hosted solutions)

## Architecture Overview

### Integration Flow

```
User Action (Task Created/Updated)
    ↓
Event Queue (Celery/Redis)
    ↓
Calendar Sync Service
    ↓
Provider-Specific Adapter (Google/Outlook/Apple)
    ↓
External Calendar API
    ↓
Webhook/Polling for Changes
    ↓
Sync Back to Time App
```

### Data Model

```python
# models/calendar_integration.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class CalendarConnection(Base):
    """User's calendar service connection"""
    __tablename__ = 'calendar_connections'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # 'google', 'outlook', 'apple'
    provider_account_id = Column(String(255))  # External account identifier

    # OAuth tokens (encrypted)
    access_token = Column(String(1000))  # Encrypted
    refresh_token = Column(String(1000))  # Encrypted
    token_expires_at = Column(DateTime)

    # Configuration
    calendar_id = Column(String(255))  # Specific calendar to sync with
    sync_enabled = Column(Boolean, default=True)
    sync_direction = Column(String(20), default='bidirectional')  # 'to_calendar', 'from_calendar', 'bidirectional'

    # Sync status
    last_sync_at = Column(DateTime)
    last_sync_status = Column(String(50))  # 'success', 'failed', 'partial'
    sync_errors = Column(JSON)  # Error details

    # Privacy settings
    include_task_details = Column(Boolean, default=True)
    privacy_level = Column(String(20), default='normal')  # 'minimal', 'normal', 'full'

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="calendar_connections")
    sync_mappings = relationship("CalendarEventMapping", back_populates="connection", cascade="all, delete-orphan")

class CalendarEventMapping(Base):
    """Maps tasks to calendar events"""
    __tablename__ = 'calendar_event_mappings'

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey('calendar_connections.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, index=True)

    # External event details
    external_event_id = Column(String(255), nullable=False, index=True)
    external_calendar_id = Column(String(255))

    # Sync tracking
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    task_version = Column(Integer, default=1)  # Track task changes
    event_version = Column(String(100))  # etag or version from provider

    # Conflict resolution
    sync_status = Column(String(50), default='synced')  # 'synced', 'conflict', 'error'
    conflict_data = Column(JSON)  # Store conflicting data for resolution

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    connection = relationship("CalendarConnection", back_populates="sync_mappings")
    task = relationship("Task", back_populates="calendar_mappings")
```

## Google Calendar Integration

### Setup & Authentication

```python
# integrations/google_calendar.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

class GoogleCalendarClient:
    """Google Calendar API client"""

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, connection: CalendarConnection):
        self.connection = connection
        self.credentials = self._get_credentials()
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials"""
        creds = Credentials(
            token=decrypt(self.connection.access_token),
            refresh_token=decrypt(self.connection.refresh_token),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=self.SCOPES
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_refreshed_token(creds)

        return creds

    def _save_refreshed_token(self, creds: Credentials):
        """Save refreshed OAuth token"""
        self.connection.access_token = encrypt(creds.token)
        if creds.refresh_token:
            self.connection.refresh_token = encrypt(creds.refresh_token)
        self.connection.token_expires_at = creds.expiry
        db.session.commit()

    def create_event(self, task: Task) -> str:
        """Create calendar event from task"""
        event = {
            'summary': task.title,
            'description': self._format_description(task),
            'start': {
                'dateTime': task.due_date.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': (task.due_date + timedelta(hours=1)).isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
            'extendedProperties': {
                'private': {
                    'timeAppTaskId': str(task.id),
                    'timeAppVersion': str(task.version)
                }
            }
        }

        created_event = self.service.events().insert(
            calendarId=self.connection.calendar_id,
            body=event
        ).execute()

        return created_event['id']

    def update_event(self, event_id: str, task: Task):
        """Update existing calendar event"""
        event = self.service.events().get(
            calendarId=self.connection.calendar_id,
            eventId=event_id
        ).execute()

        # Update fields
        event['summary'] = task.title
        event['description'] = self._format_description(task)
        event['start']['dateTime'] = task.due_date.isoformat()
        event['end']['dateTime'] = (task.due_date + timedelta(hours=1)).isoformat()

        # Update metadata
        event['extendedProperties']['private']['timeAppVersion'] = str(task.version)

        updated_event = self.service.events().update(
            calendarId=self.connection.calendar_id,
            eventId=event_id,
            body=event
        ).execute()

        return updated_event

    def delete_event(self, event_id: str):
        """Delete calendar event"""
        self.service.events().delete(
            calendarId=self.connection.calendar_id,
            eventId=event_id
        ).execute()

    def list_events(self, time_min: datetime, time_max: datetime):
        """List calendar events in time range"""
        events_result = self.service.events().list(
            calendarId=self.connection.calendar_id,
            timeMin=time_min.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    def watch_calendar(self, webhook_url: str) -> str:
        """Set up push notifications for calendar changes"""
        request_body = {
            'id': f'time-app-{self.connection.id}',
            'type': 'web_hook',
            'address': webhook_url,
            'token': generate_webhook_token(),
            'expiration': (datetime.utcnow() + timedelta(days=7)).timestamp() * 1000
        }

        response = self.service.events().watch(
            calendarId=self.connection.calendar_id,
            body=request_body
        ).execute()

        return response['resourceId']

    def _format_description(self, task: Task) -> str:
        """Format task details for calendar event description"""
        privacy_level = self.connection.privacy_level

        if privacy_level == 'minimal':
            return "Task from Time App"
        elif privacy_level == 'normal':
            return f"Task: {task.title}\nPriority: {task.priority}"
        else:  # full
            description = f"""
Task: {task.title}
Description: {task.description or 'No description'}
Priority: {task.priority}
Status: {task.status}
Project: {task.project.name if task.project else 'None'}

View in Time App: {get_task_url(task.id)}
            """.strip()
            return description
```

### OAuth Flow

```python
# api/routes/calendar_auth.py
from fastapi import APIRouter, HTTPException, Depends
from google_auth_oauthlib.flow import Flow

router = APIRouter()

@router.get("/auth/google/start")
async def start_google_auth(user: User = Depends(get_current_user)):
    """Initiate Google OAuth flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI')]
            }
        },
        scopes=['https://www.googleapis.com/auth/calendar']
    )

    flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Store state in session or cache
    cache_oauth_state(user.id, state)

    return {"authorization_url": authorization_url, "state": state}

@router.get("/auth/google/callback")
async def google_auth_callback(
    code: str,
    state: str,
    user: User = Depends(get_current_user)
):
    """Handle Google OAuth callback"""
    # Verify state
    cached_state = get_cached_oauth_state(user.id)
    if cached_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI')]
            }
        },
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    flow.fetch_token(code=code)

    credentials = flow.credentials

    # Get user's calendar list
    service = build('calendar', 'v3', credentials=credentials)
    calendars = service.calendarList().list().execute()

    # Get primary calendar
    primary_calendar = next(
        (cal for cal in calendars['items'] if cal.get('primary')),
        calendars['items'][0] if calendars['items'] else None
    )

    if not primary_calendar:
        raise HTTPException(status_code=400, detail="No calendars found")

    # Create calendar connection
    connection = CalendarConnection(
        user_id=user.id,
        provider='google',
        provider_account_id=primary_calendar['id'],
        access_token=encrypt(credentials.token),
        refresh_token=encrypt(credentials.refresh_token) if credentials.refresh_token else None,
        token_expires_at=credentials.expiry,
        calendar_id=primary_calendar['id'],
        sync_enabled=True
    )

    db.session.add(connection)
    db.session.commit()

    return {
        "success": True,
        "connection_id": connection.id,
        "calendar_name": primary_calendar['summary']
    }
```

## Microsoft Outlook Integration

### Microsoft Graph API Client

```python
# integrations/outlook_calendar.py
import msal
import requests
from typing import Dict, List

class OutlookCalendarClient:
    """Microsoft Outlook Calendar client via Graph API"""

    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    SCOPES = ['Calendars.ReadWrite', 'User.Read']

    def __init__(self, connection: CalendarConnection):
        self.connection = connection
        self.access_token = self._get_access_token()
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def _get_access_token(self) -> str:
        """Get or refresh access token"""
        # Check if token is expired
        if self.connection.token_expires_at < datetime.utcnow():
            return self._refresh_token()

        return decrypt(self.connection.access_token)

    def _refresh_token(self) -> str:
        """Refresh OAuth token using MSAL"""
        app = msal.ConfidentialClientApplication(
            os.getenv('MICROSOFT_CLIENT_ID'),
            authority=f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID')}",
            client_credential=os.getenv('MICROSOFT_CLIENT_SECRET')
        )

        result = app.acquire_token_by_refresh_token(
            decrypt(self.connection.refresh_token),
            scopes=self.SCOPES
        )

        if 'access_token' in result:
            # Save new tokens
            self.connection.access_token = encrypt(result['access_token'])
            if 'refresh_token' in result:
                self.connection.refresh_token = encrypt(result['refresh_token'])
            self.connection.token_expires_at = datetime.utcnow() + timedelta(seconds=result['expires_in'])
            db.session.commit()

            return result['access_token']
        else:
            raise Exception(f"Token refresh failed: {result.get('error_description')}")

    def create_event(self, task: Task) -> str:
        """Create Outlook calendar event"""
        event = {
            'subject': task.title,
            'body': {
                'contentType': 'HTML',
                'content': self._format_description(task)
            },
            'start': {
                'dateTime': task.due_date.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': (task.due_date + timedelta(hours=1)).isoformat(),
                'timeZone': 'UTC'
            },
            'isReminderOn': True,
            'reminderMinutesBeforeStart': 30,
            'categories': ['Time App'],
            'singleValueExtendedProperties': [
                {
                    'id': 'String {66f5a359-4659-4830-9070-00047ec6ac6e} Name timeAppTaskId',
                    'value': str(task.id)
                },
                {
                    'id': 'String {66f5a359-4659-4830-9070-00047ec6ac6f} Name timeAppVersion',
                    'value': str(task.version)
                }
            ]
        }

        response = requests.post(
            f'{self.GRAPH_API_ENDPOINT}/me/calendars/{self.connection.calendar_id}/events',
            headers=self.headers,
            json=event
        )

        response.raise_for_status()
        return response.json()['id']

    def update_event(self, event_id: str, task: Task):
        """Update Outlook calendar event"""
        event = {
            'subject': task.title,
            'body': {
                'contentType': 'HTML',
                'content': self._format_description(task)
            },
            'start': {
                'dateTime': task.due_date.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': (task.due_date + timedelta(hours=1)).isoformat(),
                'timeZone': 'UTC'
            }
        }

        response = requests.patch(
            f'{self.GRAPH_API_ENDPOINT}/me/events/{event_id}',
            headers=self.headers,
            json=event
        )

        response.raise_for_status()
        return response.json()

    def delete_event(self, event_id: str):
        """Delete Outlook calendar event"""
        response = requests.delete(
            f'{self.GRAPH_API_ENDPOINT}/me/events/{event_id}',
            headers=self.headers
        )
        response.raise_for_status()

    def list_events(self, time_min: datetime, time_max: datetime):
        """List Outlook calendar events"""
        params = {
            '$select': 'subject,start,end,id,categories',
            '$filter': f"start/dateTime ge '{time_min.isoformat()}' and end/dateTime le '{time_max.isoformat()}'",
            '$orderby': 'start/dateTime'
        }

        response = requests.get(
            f'{self.GRAPH_API_ENDPOINT}/me/calendars/{self.connection.calendar_id}/events',
            headers=self.headers,
            params=params
        )

        response.raise_for_status()
        return response.json()['value']

    def subscribe_to_changes(self, webhook_url: str) -> str:
        """Create webhook subscription for calendar changes"""
        subscription = {
            'changeType': 'created,updated,deleted',
            'notificationUrl': webhook_url,
            'resource': f'/me/calendars/{self.connection.calendar_id}/events',
            'expirationDateTime': (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z',
            'clientState': generate_webhook_token()
        }

        response = requests.post(
            f'{self.GRAPH_API_ENDPOINT}/subscriptions',
            headers=self.headers,
            json=subscription
        )

        response.raise_for_status()
        return response.json()['id']

    def _format_description(self, task: Task) -> str:
        """Format task description for Outlook"""
        privacy_level = self.connection.privacy_level

        if privacy_level == 'minimal':
            return "<p>Task from Time App</p>"
        elif privacy_level == 'normal':
            return f"""
<div>
    <p><strong>Task:</strong> {task.title}</p>
    <p><strong>Priority:</strong> {task.priority}</p>
</div>
            """.strip()
        else:  # full
            return f"""
<div>
    <h3>{task.title}</h3>
    <p><strong>Description:</strong> {task.description or 'No description'}</p>
    <p><strong>Priority:</strong> {task.priority}</p>
    <p><strong>Status:</strong> {task.status}</p>
    <p><strong>Project:</strong> {task.project.name if task.project else 'None'}</p>
    <p><a href="{get_task_url(task.id)}">View in Time App</a></p>
</div>
            """.strip()
```

## Apple Calendar (CalDAV) Integration

```python
# integrations/apple_calendar.py
import caldav
from caldav.elements import dav, cdav
from icalendar import Calendar, Event as ICalEvent

class AppleCalendarClient:
    """Apple Calendar client using CalDAV protocol"""

    def __init__(self, connection: CalendarConnection):
        self.connection = connection
        self.client = self._get_client()
        self.calendar = self._get_calendar()

    def _get_client(self) -> caldav.DAVClient:
        """Create CalDAV client"""
        url = 'https://caldav.icloud.com'
        username = self.connection.provider_account_id
        password = decrypt(self.connection.access_token)  # App-specific password

        client = caldav.DAVClient(
            url=url,
            username=username,
            password=password
        )

        return client

    def _get_calendar(self):
        """Get calendar object"""
        principal = self.client.principal()
        calendars = principal.calendars()

        # Find specific calendar or use default
        calendar_id = self.connection.calendar_id
        if calendar_id:
            calendar = next(
                (cal for cal in calendars if cal.id == calendar_id),
                calendars[0] if calendars else None
            )
        else:
            calendar = calendars[0] if calendars else None

        return calendar

    def create_event(self, task: Task) -> str:
        """Create iCloud calendar event"""
        cal = Calendar()
        cal.add('prodid', '-//Time App//Calendar Integration//EN')
        cal.add('version', '2.0')

        event = ICalEvent()
        event.add('summary', task.title)
        event.add('description', self._format_description(task))
        event.add('dtstart', task.due_date)
        event.add('dtend', task.due_date + timedelta(hours=1))
        event.add('dtstamp', datetime.utcnow())
        event['uid'] = f'time-app-task-{task.id}@timeapp.com'
        event.add('priority', self._map_priority(task.priority))
        event.add('categories', 'Time App')

        # Add custom properties
        event.add('x-time-app-task-id', str(task.id))
        event.add('x-time-app-version', str(task.version))

        cal.add_component(event)

        # Save to calendar
        created_event = self.calendar.add_event(cal.to_ical())

        return created_event.id

    def update_event(self, event_uid: str, task: Task):
        """Update iCloud calendar event"""
        # Find event by UID
        events = self.calendar.events()
        event = next((e for e in events if event_uid in e.data), None)

        if not event:
            raise ValueError(f"Event {event_uid} not found")

        # Parse and update
        cal = Calendar.from_ical(event.data)
        for component in cal.walk():
            if component.name == "VEVENT":
                component['summary'] = task.title
                component['description'] = self._format_description(task)
                component['dtstart'] = task.due_date
                component['dtend'] = task.due_date + timedelta(hours=1)
                component['priority'] = self._map_priority(task.priority)
                component['x-time-app-version'] = str(task.version)

        event.data = cal.to_ical()
        event.save()

    def delete_event(self, event_uid: str):
        """Delete iCloud calendar event"""
        events = self.calendar.events()
        event = next((e for e in events if event_uid in e.data), None)

        if event:
            event.delete()

    def list_events(self, time_min: datetime, time_max: datetime):
        """List iCloud calendar events"""
        events = self.calendar.date_search(
            start=time_min,
            end=time_max
        )

        return events

    def _map_priority(self, priority: str) -> int:
        """Map task priority to iCal priority (1-9)"""
        mapping = {
            'urgent': 1,
            'high': 3,
            'medium': 5,
            'low': 7,
            'none': 9
        }
        return mapping.get(priority, 5)

    def _format_description(self, task: Task) -> str:
        """Format task description for Apple Calendar"""
        privacy_level = self.connection.privacy_level

        if privacy_level == 'minimal':
            return "Task from Time App"
        elif privacy_level == 'normal':
            return f"Task: {task.title}\\nPriority: {task.priority}"
        else:  # full
            return f"""
Task: {task.title}
Description: {task.description or 'No description'}
Priority: {task.priority}
Status: {task.status}
Project: {task.project.name if task.project else 'None'}

View in Time App: {get_task_url(task.id)}
            """.strip()
```

## Synchronization Service

### Bidirectional Sync Engine

```python
# services/calendar_sync_service.py
from celery import group
from typing import List

class CalendarSyncService:
    """Manages bidirectional calendar synchronization"""

    @staticmethod
    async def sync_task_to_calendars(task: Task):
        """Sync task to all connected calendars"""
        user = task.assigned_to or task.created_by
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user.id,
            CalendarConnection.sync_enabled == True,
            CalendarConnection.sync_direction.in_(['to_calendar', 'bidirectional'])
        ).all()

        for connection in connections:
            # Queue sync job
            sync_task_to_calendar.delay(task.id, connection.id)

    @staticmethod
    async def sync_from_calendar(connection: CalendarConnection):
        """Sync events from calendar to tasks"""
        client = get_calendar_client(connection)

        # Get events since last sync
        time_min = connection.last_sync_at or datetime.utcnow() - timedelta(days=7)
        time_max = datetime.utcnow() + timedelta(days=90)

        events = client.list_events(time_min, time_max)

        for event in events:
            # Check if event is from Time App
            task_id = extract_task_id_from_event(event)

            if task_id:
                # Update existing task
                await sync_event_to_task(event, task_id, connection)
            else:
                # Create new task from external event
                if connection.sync_direction in ['from_calendar', 'bidirectional']:
                    await create_task_from_event(event, connection)

        # Update sync timestamp
        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = 'success'
        db.session.commit()


@celery_app.task(bind=True, max_retries=3)
def sync_task_to_calendar(self, task_id: int, connection_id: int):
    """Background job to sync task to calendar"""
    try:
        task = db.query(Task).get(task_id)
        connection = db.query(CalendarConnection).get(connection_id)

        if not task or not connection:
            return

        # Get calendar client
        client = get_calendar_client(connection)

        # Check if mapping exists
        mapping = db.query(CalendarEventMapping).filter(
            CalendarEventMapping.connection_id == connection_id,
            CalendarEventMapping.task_id == task_id
        ).first()

        if mapping:
            # Update existing event
            client.update_event(mapping.external_event_id, task)
            mapping.last_synced_at = datetime.utcnow()
            mapping.task_version = task.version
        else:
            # Create new event
            event_id = client.create_event(task)

            # Create mapping
            mapping = CalendarEventMapping(
                connection_id=connection_id,
                task_id=task_id,
                external_event_id=event_id,
                external_calendar_id=connection.calendar_id,
                task_version=task.version
            )
            db.session.add(mapping)

        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = 'success'
        db.session.commit()

    except Exception as exc:
        # Log error
        logger.error(f"Sync failed for task {task_id}: {exc}")

        # Update connection status
        connection.last_sync_status = 'failed'
        connection.sync_errors = {
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }
        db.session.commit()

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def sync_event_to_task(event: dict, task_id: int, connection: CalendarConnection):
    """Sync calendar event changes back to task"""
    task = db.query(Task).get(task_id)

    if not task:
        return

    # Extract event details
    event_title = extract_title_from_event(event, connection.provider)
    event_start = extract_start_time_from_event(event, connection.provider)

    # Check for conflicts
    if task.title != event_title or task.due_date != event_start:
        # Conflict detected - use last-write-wins or prompt user
        if connection.sync_direction == 'bidirectional':
            # Apply changes from calendar
            task.title = event_title
            task.due_date = event_start
            task.version += 1
            db.session.commit()


async def create_task_from_event(event: dict, connection: CalendarConnection):
    """Create new task from calendar event"""
    title = extract_title_from_event(event, connection.provider)
    start_time = extract_start_time_from_event(event, connection.provider)
    description = extract_description_from_event(event, connection.provider)

    # Create task
    task = Task(
        title=title,
        description=description,
        due_date=start_time,
        created_by_id=connection.user_id,
        assigned_to_id=connection.user_id,
        status='todo',
        priority='medium',
        source='calendar_import'
    )

    db.session.add(task)
    db.session.flush()

    # Create mapping
    event_id = extract_event_id_from_event(event, connection.provider)
    mapping = CalendarEventMapping(
        connection_id=connection.id,
        task_id=task.id,
        external_event_id=event_id,
        external_calendar_id=connection.calendar_id
    )

    db.session.add(mapping)
    db.session.commit()
```

## Webhook Handlers

### Google Calendar Webhooks

```python
# api/routes/calendar_webhooks.py
from fastapi import APIRouter, Request, HTTPException, Header

router = APIRouter()

@router.post("/webhooks/google/calendar")
async def google_calendar_webhook(
    request: Request,
    x_goog_channel_id: str = Header(None),
    x_goog_resource_state: str = Header(None)
):
    """Handle Google Calendar push notifications"""

    if x_goog_resource_state == 'sync':
        # Initial sync message, ignore
        return {"status": "ok"}

    # Parse connection from channel ID
    connection_id = parse_connection_id_from_channel(x_goog_channel_id)
    connection = db.query(CalendarConnection).get(connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Queue sync job
    sync_from_calendar_job.delay(connection.id)

    return {"status": "queued"}


@router.post("/webhooks/microsoft/calendar")
async def microsoft_calendar_webhook(
    request: Request,
    validationToken: str = None
):
    """Handle Microsoft Graph webhook notifications"""

    # Handle validation request
    if validationToken:
        return validationToken

    # Parse notification
    data = await request.json()

    for notification in data.get('value', []):
        subscription_id = notification['subscriptionId']
        change_type = notification['changeType']
        resource = notification['resource']

        # Find connection by subscription
        connection = db.query(CalendarConnection).filter(
            CalendarConnection.provider == 'outlook',
            CalendarConnection.sync_errors['subscription_id'] == subscription_id
        ).first()

        if connection:
            # Queue sync job
            sync_from_calendar_job.delay(connection.id)

    return {"status": "ok"}
```

## GDPR/CCPA Compliance

### Data Privacy Implementation

```python
# services/calendar_privacy_service.py

class CalendarPrivacyService:
    """Ensure GDPR/CCPA compliance for calendar integration"""

    @staticmethod
    def anonymize_calendar_data(user_id: int):
        """Anonymize user's calendar data (right to be forgotten)"""
        # Disconnect all calendars
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user_id
        ).all()

        for connection in connections:
            # Delete events from external calendars
            client = get_calendar_client(connection)
            mappings = connection.sync_mappings

            for mapping in mappings:
                try:
                    client.delete_event(mapping.external_event_id)
                except:
                    pass  # Event may already be deleted

            # Revoke OAuth tokens
            revoke_oauth_token(connection)

            # Delete connection
            db.session.delete(connection)

        db.session.commit()

    @staticmethod
    def export_calendar_data(user_id: int) -> dict:
        """Export user's calendar data (right to data portability)"""
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user_id
        ).all()

        export_data = {
            'user_id': user_id,
            'export_date': datetime.utcnow().isoformat(),
            'connections': []
        }

        for connection in connections:
            connection_data = {
                'provider': connection.provider,
                'calendar_id': connection.calendar_id,
                'sync_enabled': connection.sync_enabled,
                'sync_direction': connection.sync_direction,
                'privacy_level': connection.privacy_level,
                'created_at': connection.created_at.isoformat(),
                'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                'synced_events': []
            }

            for mapping in connection.sync_mappings:
                connection_data['synced_events'].append({
                    'task_id': mapping.task_id,
                    'external_event_id': mapping.external_event_id,
                    'last_synced_at': mapping.last_synced_at.isoformat()
                })

            export_data['connections'].append(connection_data)

        return export_data

    @staticmethod
    def get_consent_status(user_id: int) -> dict:
        """Get user's calendar integration consent status"""
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user_id
        ).all()

        return {
            'has_active_connections': len(connections) > 0,
            'connection_count': len(connections),
            'providers': [c.provider for c in connections],
            'consent_given_at': min([c.created_at for c in connections]) if connections else None
        }
```

### Privacy Settings UI

```python
# api/routes/calendar_settings.py

@router.put("/calendar/settings/{connection_id}/privacy")
async def update_privacy_settings(
    connection_id: int,
    privacy_level: str,
    include_task_details: bool,
    user: User = Depends(get_current_user)
):
    """Update calendar privacy settings"""
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == user.id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Validate privacy level
    if privacy_level not in ['minimal', 'normal', 'full']:
        raise HTTPException(status_code=400, detail="Invalid privacy level")

    # Update settings
    connection.privacy_level = privacy_level
    connection.include_task_details = include_task_details
    db.session.commit()

    # Resync all events with new privacy settings
    resync_all_events.delay(connection_id)

    return {
        "success": True,
        "privacy_level": privacy_level,
        "message": "Privacy settings updated. Events will be resynced."
    }


@router.delete("/calendar/connections/{connection_id}")
async def disconnect_calendar(
    connection_id: int,
    delete_events: bool = False,
    user: User = Depends(get_current_user)
):
    """Disconnect calendar (GDPR right to be forgotten)"""
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == user.id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    if delete_events:
        # Delete all synced events from external calendar
        client = get_calendar_client(connection)
        for mapping in connection.sync_mappings:
            try:
                client.delete_event(mapping.external_event_id)
            except:
                pass

    # Revoke OAuth token
    revoke_oauth_token(connection)

    # Delete connection and mappings
    db.session.delete(connection)
    db.session.commit()

    return {
        "success": True,
        "message": "Calendar disconnected successfully"
    }
```

## Real-Time Collaboration

### WebSocket Updates

```python
# services/realtime_service.py
from fastapi import WebSocket

class RealtimeCalendarService:
    """Real-time updates for calendar changes"""

    active_connections: Dict[int, List[WebSocket]] = {}

    @classmethod
    async def connect(cls, user_id: int, websocket: WebSocket):
        """Connect user to realtime updates"""
        await websocket.accept()
        if user_id not in cls.active_connections:
            cls.active_connections[user_id] = []
        cls.active_connections[user_id].append(websocket)

    @classmethod
    async def disconnect(cls, user_id: int, websocket: WebSocket):
        """Disconnect user from realtime updates"""
        cls.active_connections[user_id].remove(websocket)
        if not cls.active_connections[user_id]:
            del cls.active_connections[user_id]

    @classmethod
    async def broadcast_calendar_update(cls, user_id: int, update_data: dict):
        """Broadcast calendar update to user's connected clients"""
        if user_id in cls.active_connections:
            message = {
                'type': 'calendar_update',
                'data': update_data,
                'timestamp': datetime.utcnow().isoformat()
            }

            for connection in cls.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    await cls.disconnect(user_id, connection)


# WebSocket endpoint
@app.websocket("/ws/calendar/{user_id}")
async def calendar_websocket(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time calendar updates"""
    await RealtimeCalendarService.connect(user_id, websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except:
        await RealtimeCalendarService.disconnect(user_id, websocket)
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_calendar_integration.py
import pytest
from unittest.mock import Mock, patch

class TestGoogleCalendarClient:
    """Unit tests for Google Calendar integration"""

    def test_create_event(self, mock_connection, mock_task):
        """Test creating calendar event from task"""
        with patch('integrations.google_calendar.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service

            mock_service.events().insert().execute.return_value = {
                'id': 'test_event_123'
            }

            client = GoogleCalendarClient(mock_connection)
            event_id = client.create_event(mock_task)

            assert event_id == 'test_event_123'
            mock_service.events().insert.assert_called_once()

    def test_privacy_level_minimal(self, mock_connection, mock_task):
        """Test minimal privacy level only shows generic description"""
        mock_connection.privacy_level = 'minimal'
        client = GoogleCalendarClient(mock_connection)

        description = client._format_description(mock_task)

        assert description == "Task from Time App"
        assert mock_task.title not in description

    def test_token_refresh(self, mock_connection):
        """Test OAuth token refresh logic"""
        mock_connection.token_expires_at = datetime.utcnow() - timedelta(hours=1)

        with patch('integrations.google_calendar.Request') as mock_request:
            client = GoogleCalendarClient(mock_connection)

            # Verify token was refreshed
            assert mock_connection.access_token != mock_connection.access_token
```

### Integration Tests

```python
# tests/integration/test_calendar_sync.py
import pytest

@pytest.mark.integration
class TestCalendarSync:
    """Integration tests for calendar synchronization"""

    def test_end_to_end_sync(self, db_session, test_user, test_task):
        """Test complete sync flow from task to calendar"""
        # Create connection
        connection = CalendarConnection(
            user_id=test_user.id,
            provider='google',
            calendar_id='test_calendar',
            access_token=encrypt('test_token'),
            sync_enabled=True
        )
        db_session.add(connection)
        db_session.commit()

        # Sync task
        sync_task_to_calendar(test_task.id, connection.id)

        # Verify mapping created
        mapping = db_session.query(CalendarEventMapping).filter(
            CalendarEventMapping.task_id == test_task.id
        ).first()

        assert mapping is not None
        assert mapping.external_event_id is not None

    def test_conflict_resolution(self, db_session, test_task, test_connection):
        """Test conflict resolution when task and event differ"""
        # Create initial mapping
        mapping = CalendarEventMapping(
            connection_id=test_connection.id,
            task_id=test_task.id,
            external_event_id='event_123',
            task_version=1
        )
        db_session.add(mapping)

        # Simulate task update
        test_task.title = "Updated Task"
        test_task.version = 2

        # Simulate calendar event update
        mock_event = {
            'id': 'event_123',
            'summary': 'Different Title',
            'start': {'dateTime': test_task.due_date.isoformat()}
        }

        # Sync should detect conflict
        # Verify conflict is logged and resolved based on strategy
```

## Performance Considerations

- **Rate Limiting**: Respect API rate limits (Google: 1M requests/day, Microsoft: 10,000 requests/10 mins)
- **Batch Operations**: Use batch APIs when syncing multiple events
- **Caching**: Cache calendar event data to reduce API calls
- **Webhooks**: Use webhooks instead of polling for real-time updates
- **Background Jobs**: All sync operations run asynchronously via Celery
- **Retry Logic**: Exponential backoff for failed API calls
- **Connection Pooling**: Reuse HTTP connections for API requests

## Security Considerations

- **Token Encryption**: All OAuth tokens encrypted at rest using AES-256
- **Secure Storage**: Tokens stored in database with encryption key in secrets manager
- **HTTPS Only**: All API communications over TLS 1.3
- **Token Rotation**: Refresh tokens rotated on each use
- **Scope Limitation**: Request minimum necessary OAuth scopes
- **Webhook Verification**: Verify webhook signatures to prevent spoofing
- **Rate Limiting**: Implement rate limiting on webhook endpoints

## Deployment Checklist

- [ ] OAuth credentials configured for all providers
- [ ] Webhook URLs registered and accessible
- [ ] SSL/TLS certificates installed
- [ ] Redis/Celery workers running
- [ ] Database encryption enabled
- [ ] Token encryption keys securely stored
- [ ] Rate limiting configured
- [ ] Monitoring and alerting set up
- [ ] GDPR/CCPA compliance verified
- [ ] Privacy policy updated
- [ ] User consent flows implemented
- [ ] Data export/deletion tested
- [ ] Backup and recovery procedures documented

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: Implementation guide - awaiting development
**Owner**: Time Agent 2
