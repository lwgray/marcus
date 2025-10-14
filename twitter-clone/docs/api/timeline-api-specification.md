# Timeline API Specification - Executive Summary

## API Overview

Complete REST API specification for Twitter Clone timeline features covering 3 timeline types and post management.

## Timeline Endpoints (5 endpoints)

**Home Timeline** - GET /timelines/home
- Personalized feed from followed users
- Authentication: Required  
- Rate limit: 180 req/15min
- Features: Pagination, filtering (media/links/text), exclude replies/retweets

**User Timeline** - GET /timelines/user/:userId
- Specific user's posts and retweets
- Authentication: Optional (required for private accounts)
- Rate limit: 900 req/15min
- Features: Pinned posts, exclude options, profile context

**Global Timeline** - GET /timelines/global
- Public posts from all users
- Authentication: Optional
- Rate limit: 450 req/15min
- Features: Language filtering, verified-only filter, trending

## Post Management (3 endpoints)

**Create Post** - POST /posts
- Create new post with text (280 char max), media (max 4), replies, quotes
- Rate limit: 300 posts/day
- Validation: Text length, media size (5MB max), visibility options

**Get Post** - GET /posts/:postId
- Retrieve single post with full context (conversation chain, quotes)
- Rate limit: 900 req/15min

**Update Post** - PUT /posts/:postId  
- Edit own posts within 30-minute window
- Rate limit: 100 req/hour
- Includes edit history tracking

**Delete Post** - DELETE /posts/:postId
- Remove own posts permanently
- Rate limit: 1000 req/day

## Key Features

**Pagination Strategy:**
- Cursor-based for infinite scroll
- Opaque tokens encode: lastId, timestamp, direction, filters
- Response includes: nextCursor, previousCursor, hasMore
- No total counts for performance

**Filtering & Sorting:**
- Filters: media, links, text, verified, trending
- Sorting: chronological (default), algorithmic (personalized)
- Date range: since_id, until_id parameters

**Authentication:**
- JWT Bearer token in Authorization header
- 15-minute access token expiry
- Auto-refresh on 401 TOKEN_EXPIRED

**Error Handling:**
- Consistent format: {success, error: {code, message, statusCode, details}}
- 15+ error codes covering auth, validation, resources, rate limits
- HTTP status codes: 200, 201, 400, 401, 403, 404, 409, 429, 500, 503

**Rate Limiting:**
- Sliding window algorithm with Redis
- Per-user limits (authenticated) or per-IP (unauthenticated)
- Response headers: X-Rate-Limit-Limit, X-Rate-Limit-Remaining, X-Rate-Limit-Reset
- Graduated penalties: 15min → 1hr → 24hr → account review

**Real-time Updates:**
- WebSocket connection: wss://api.twitter-clone.com/v1/stream
- 4 event types: post.new, post.deleted, post.edited, engagement.updated
- Channel subscriptions: timeline.home, timeline.user.{id}, timeline.global

## Data Models

**Post Object:**
- Core: id, type (original/retweet/quote/reply), author, content
- Media: Array of image/video/gif attachments with dimensions, thumbnails, alt text
- Engagement: likes, retweets, quotes, replies, views + user interaction state
- Metadata: timestamps, source, language, visibility, edit history

**User Profile:**
- Basic: id, username, displayName, avatar, bio
- Status: isVerified, isPrivate
- Stats: followers, following, posts, likes
- Relationship: isFollowing, isFollowedBy, isBlocked, isMuted

**Post Content:**
- Text: 280 char max
- Entities: mentions (with indices), hashtags (with indices), URLs (with expanded/display)
- Polls: (future feature)

**Engagement Metrics:**
- Counts: likes, retweets, quotes, replies, views
- User state: isLiked, isRetweeted, isBookmarked

## OpenAPI 3.0 Specification

Complete YAML specification included with:
- All 8 endpoints fully documented
- Request/response schemas with TypeScript interfaces
- Security schemes (BearerAuth)
- Component schemas (Post, UserProfile, PostContent, MediaAttachment, etc.)
- Reusable responses (UnauthorizedError, ForbiddenError, NotFoundError, etc.)
- Ready for import into Swagger UI, Postman, or SDK generation

## Implementation Highlights

**Developer Experience:**
- Clear RESTful design with predictable resource naming
- Comprehensive examples for all endpoints
- Consistent error format across API

**Performance:**
- Cursor-based pagination for efficient queries
- ETag support for conditional requests (304 Not Modified)
- Caching headers (Cache-Control, max-age=30)

**Scalability:**
- Rate limiting prevents abuse
- Cursor design supports high-volume timelines
- WebSocket for real-time updates reduces polling

**Security:**
- JWT authentication with short expiry
- Authorization checks for private content
- Privacy controls (public/followers/mentioned visibility)

Full specification: /Users/lwgray/dev/worktrees/independent-tasks/twitter-clone/docs/api/timeline-api-specification.md