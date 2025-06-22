#!/usr/bin/env python3
"""
Clear the board and create a single detailed task with all features
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Detailed task definition
DETAILED_TASK = {
    "name": "Implement User Authentication System",
    "description": """## Overview
Implement a complete user authentication system for the Todo App that provides secure user registration, login, and session management.

## Background
The Todo App needs a robust authentication system to ensure that users can only access and modify their own todos. This is a critical security feature that must be implemented before the app can be deployed to production.

## Technical Requirements

### 1. User Registration
- **Email validation**: Verify email format and uniqueness
- **Password requirements**: 
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number
  - At least one special character
- **Password hashing**: Use bcrypt with salt rounds of 10
- **Email verification**: Send verification email with token (valid for 24 hours)
- **Rate limiting**: Max 5 registration attempts per IP per hour

### 2. User Login
- **Authentication methods**:
  - Email + Password
  - OAuth2 (Google, GitHub)
  - Optional: Magic link authentication
- **Security measures**:
  - Brute force protection (max 5 failed attempts, then 15-minute lockout)
  - CAPTCHA after 3 failed attempts
  - Log all login attempts with IP and timestamp
- **Session management**:
  - JWT tokens with 15-minute expiry
  - Refresh tokens with 7-day expiry
  - Secure httpOnly cookies
  - CSRF protection

### 3. Password Reset
- **Flow**:
  1. User requests reset via email
  2. Generate secure reset token (valid for 1 hour)
  3. Send email with reset link
  4. Validate token and allow password change
  5. Invalidate all existing sessions after reset
- **Security**: Rate limit to 3 reset requests per email per hour

### 4. API Endpoints
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/verify-email/:token
POST /api/auth/forgot-password
POST /api/auth/reset-password/:token
GET  /api/auth/me
```

### 5. Database Schema
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Email verification tokens
CREATE TABLE email_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Implementation Plan

### Phase 1: Backend Implementation (Days 1-3)
1. Set up database tables and migrations
2. Implement user model with validation
3. Create authentication service with JWT handling
4. Implement all auth endpoints
5. Add middleware for route protection

### Phase 2: Security Features (Days 4-5)
1. Implement rate limiting
2. Add brute force protection
3. Set up email service for verification and reset
4. Add logging and monitoring
5. Security testing and penetration testing

### Phase 3: Frontend Integration (Days 6-7)
1. Create login/register forms with validation
2. Implement auth context/state management
3. Add protected routes
4. Create user profile page
5. Handle token refresh automatically

### Phase 4: Testing & Documentation (Day 8)
1. Unit tests for all auth functions
2. Integration tests for auth flow
3. API documentation
4. Security audit
5. Performance testing

## Acceptance Criteria
- [ ] Users can register with email and password
- [ ] Email verification is required before login
- [ ] Users can log in and receive JWT tokens
- [ ] Tokens automatically refresh before expiry
- [ ] Password reset flow works end-to-end
- [ ] All routes are properly protected
- [ ] Rate limiting prevents abuse
- [ ] All security best practices are followed
- [ ] 90% test coverage for auth code
- [ ] API documentation is complete

## Dependencies
- **Backend**: Express.js, bcrypt, jsonwebtoken, nodemailer
- **Frontend**: React Router, Axios interceptors, React Context
- **Database**: PostgreSQL with migrations
- **Testing**: Jest, Supertest, React Testing Library

## Risks & Mitigations
- **Risk**: Email delivery issues
  - **Mitigation**: Use reliable service (SendGrid/AWS SES), implement retry logic
- **Risk**: Token theft
  - **Mitigation**: Short expiry times, secure storage, refresh token rotation
- **Risk**: Database breach
  - **Mitigation**: Proper hashing, encryption at rest, regular security audits

## Resources
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Node.js Security Checklist](https://blog.risingstack.com/node-js-security-checklist/)
""",
    "labels": ["Backend", "Frontend", "Database", "Feature", "High Priority", "Security"],
    "subtasks": [
        "Create database migrations for auth tables",
        "Implement User model with validation rules",
        "Set up bcrypt for password hashing",
        "Create JWT token generation and validation",
        "Implement registration endpoint with email verification",
        "Implement login endpoint with rate limiting",
        "Create password reset flow",
        "Set up email service (SendGrid/Nodemailer)",
        "Add brute force protection middleware",
        "Create auth middleware for protected routes",
        "Build login form component with validation",
        "Build registration form component",
        "Implement auth context with token management",
        "Add automatic token refresh",
        "Create password reset UI flow",
        "Write unit tests for auth service",
        "Write integration tests for auth endpoints",
        "Perform security audit",
        "Create API documentation",
        "Load test auth endpoints"
    ]
}

# Label color mapping for Planka
LABEL_COLORS = {
    "Feature": "lagoon-blue",
    "Frontend": "pink-tulip",
    "Backend": "berry-red",
    "Database": "pumpkin-orange",
    "Testing": "bright-moss",
    "Bug": "red-burgundy",
    "High Priority": "midnight-blue",
    "Enhancement": "sunny-grass",
    "Documentation": "light-mud",
    "Security": "tank-green"
}


async def clear_board_and_create_task():
    """Clear the board and create a detailed task"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🚀 Starting board cleanup and task creation...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # 1. Find Task Master Test project
            print("\n📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    print(f"✅ Found project: {project['name']} (ID: {project_id})")
                    break
            
            if not project_id:
                print("❌ Task Master Test project not found!")
                return
            
            # Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # 2. Get all cards and delete them
            print("\n🧹 Clearing existing cards...")
            try:
                result = await session.call_tool("mcp_kanban_card_manager", {
                    "action": "get_all",
                    "boardId": board_id
                })
                
                # Handle empty or non-JSON response
                if result.content and result.content[0].text:
                    try:
                        cards = json.loads(result.content[0].text)
                    except json.JSONDecodeError:
                        # If it's not JSON, it might be a plain array string representation
                        cards = []
                        print("Could not parse cards response, assuming empty board")
                else:
                    cards = []
                
                if isinstance(cards, list) and len(cards) > 0:
                    print(f"Found {len(cards)} cards to delete")
                    for card in cards:
                        try:
                            await session.call_tool("mcp_kanban_card_manager", {
                                "action": "delete",
                                "cardId": card["id"]
                            })
                            print(f"  ✅ Deleted card: {card.get('name', 'Unnamed')}")
                        except Exception as e:
                            print(f"  ❌ Error deleting card {card['id']}: {str(e)}")
                else:
                    print("No existing cards found")
            except Exception as e:
                print(f"Error getting cards: {str(e)}, continuing anyway...")
            
            # 3. Get lists
            print("\n📋 Getting lists...")
            result = await session.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            lists = json.loads(result.content[0].text)
            backlog_list = None
            
            for lst in lists:
                if "BACKLOG" in lst["name"].upper():
                    backlog_list = lst
                    print(f"✅ Found list: {lst['name']} (ID: {lst['id']})")
                    break
            
            if not backlog_list:
                print("❌ No Backlog list found!")
                return
            
            # 4. Create the detailed task
            print("\n📝 Creating detailed task...")
            result = await session.call_tool("mcp_kanban_card_manager", {
                "action": "create",
                "listId": backlog_list["id"],
                "name": DETAILED_TASK["name"],
                "description": DETAILED_TASK["description"]
            })
            
            card = json.loads(result.content[0].text)
            card_id = card["id"]
            print(f"✅ Created card: {card['name']} (ID: {card_id})")
            
            # 5. Create and add labels
            print("\n🏷️  Adding labels...")
            for label_name in DETAILED_TASK["labels"]:
                if label_name in LABEL_COLORS:
                    try:
                        # First create the label
                        label_result = await session.call_tool("mcp_kanban_label_manager", {
                            "action": "create",
                            "boardId": board_id,
                            "name": label_name,
                            "color": LABEL_COLORS[label_name]
                        })
                        label = json.loads(label_result.content[0].text)
                        
                        # Then add it to the card
                        await session.call_tool("mcp_kanban_label_manager", {
                            "action": "add_to_card",
                            "cardId": card_id,
                            "labelId": label["id"]
                        })
                        print(f"  ✅ Added label: {label_name}")
                    except Exception as e:
                        # Label might already exist, try to find and add it
                        try:
                            labels_result = await session.call_tool("mcp_kanban_label_manager", {
                                "action": "get_all",
                                "boardId": board_id
                            })
                            labels = json.loads(labels_result.content[0].text)
                            
                            for existing_label in labels:
                                if existing_label["name"] == label_name:
                                    await session.call_tool("mcp_kanban_label_manager", {
                                        "action": "add_to_card",
                                        "cardId": card_id,
                                        "labelId": existing_label["id"]
                                    })
                                    print(f"  ✅ Added existing label: {label_name}")
                                    break
                        except Exception as e2:
                            print(f"  ❌ Could not add label {label_name}: {str(e2)}")
            
            # 6. Create subtasks
            print("\n📋 Creating subtasks...")
            for i, subtask_name in enumerate(DETAILED_TASK["subtasks"], 1):
                try:
                    result = await session.call_tool("mcp_kanban_task_manager", {
                        "action": "create",
                        "cardId": card_id,
                        "name": subtask_name,
                        "position": i
                    })
                    print(f"  ✅ [{i}/{len(DETAILED_TASK['subtasks'])}] Created subtask: {subtask_name}")
                except Exception as e:
                    print(f"  ❌ Error creating subtask: {str(e)}")
            
            # 7. Add attachments (comments with attachment info)
            print("\n📎 Adding attachment references...")
            attachments = [
                "📄 auth-flow-diagram.png - Authentication flow diagram",
                "📄 database-schema.sql - Complete database schema",
                "📄 jwt-implementation.md - JWT implementation guide",
                "📄 security-checklist.pdf - Security audit checklist",
                "📄 api-documentation.yaml - OpenAPI specification"
            ]
            
            for attachment in attachments:
                try:
                    await session.call_tool("mcp_kanban_comment_manager", {
                        "action": "create",
                        "cardId": card_id,
                        "text": attachment
                    })
                    print(f"  ✅ Added attachment reference: {attachment.split(' - ')[0]}")
                except Exception as e:
                    print(f"  ❌ Error adding attachment: {str(e)}")
            
            # 8. Add a due date comment
            due_date = datetime.now() + timedelta(days=8)
            await session.call_tool("mcp_kanban_comment_manager", {
                "action": "create",
                "cardId": card_id,
                "text": f"📅 **Due Date**: {due_date.strftime('%B %d, %Y')}\n⏱️ **Estimated Time**: 8 days\n👥 **Team Size**: 2 developers (1 backend, 1 frontend)"
            })
            
            print("\n✅ Successfully created detailed task with all features!")
            print(f"\n📊 Summary:")
            print(f"  - Card: {DETAILED_TASK['name']}")
            print(f"  - Labels: {len(DETAILED_TASK['labels'])}")
            print(f"  - Subtasks: {len(DETAILED_TASK['subtasks'])}")
            print(f"  - Attachments: {len(attachments)}")


if __name__ == "__main__":
    asyncio.run(clear_board_and_create_task())