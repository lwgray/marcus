# Timeline API Quick Reference

**Version:** 1.0  
**Base URL:** `/api/v1`

---

## Timeline Endpoints

### GET /timeline/home
Get authenticated user's home timeline.

```bash
curl -X GET "https://api.twitterclone.com/api/v1/timeline/home?limit=20" \
  -H "Authorization: Bearer <token>"
```

**Query Parameters:**
- `limit` (optional): 1-100, default 20
- `cursor` (optional): Pagination cursor
- `algorithm` (optional): `chronological` or `algorithmic`

**Response:**
```json
{
  "success": true,
  "data": {
    "tweets": [...],
    "next_cursor": "1697190000",
    "has_more": true
  }
}
```

**Rate Limit:** 180 requests / 15 min  
**Cache:** Private, 30 seconds

---

### GET /timeline/user/:id
Get specific user's timeline.

```bash
curl -X GET "https://api.twitterclone.com/api/v1/timeline/user/123?limit=20"
```

**Query Parameters:**
- `limit` (optional): 1-100, default 20
- `cursor` (optional): Pagination cursor
- `include_replies` (optional): boolean, default false
- `include_retweets` (optional): boolean, default true

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {...},
    "tweets": [...],
    "next_cursor": "1697190000",
    "has_more": true
  }
}
```

**Rate Limit:** 900 requests / 15 min  
**Cache:** Public, 60 seconds

---

## Tweet Endpoints

### POST /tweets
Create a new tweet.

```bash
curl -X POST "https://api.twitterclone.com/api/v1/tweets" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, world!",
    "parent_tweet_id": null
  }'
```

**Request Body:**
- `content` (required): 1-280 characters
- `parent_tweet_id` (optional): Reply to tweet ID

**Response (201):**
```json
{
  "success": true,
  "data": {
    "tweet": {
      "id": "1234567890",
      "content": "Hello, world!",
      "created_at": "2025-10-13T11:00:00Z",
      ...
    }
  }
}
```

**Rate Limit:** 
- 300 tweets / 3 hours
- 50 tweets / 15 min

---

### GET /tweets/:id
Get single tweet.

```bash
curl -X GET "https://api.twitterclone.com/api/v1/tweets/1234567890"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "tweet": {...}
  }
}
```

**Rate Limit:** 900 requests / 15 min  
**Cache:** Public, 300 seconds

---

### DELETE /tweets/:id
Delete own tweet.

```bash
curl -X DELETE "https://api.twitterclone.com/api/v1/tweets/1234567890" \
  -H "Authorization: Bearer <token>"
```

**Response (200):**
```json
{
  "success": true,
  "message": "Tweet deleted successfully"
}
```

**Rate Limit:** 300 requests / 15 min

---

### POST /tweets/:id/like
Like a tweet.

```bash
curl -X POST "https://api.twitterclone.com/api/v1/tweets/1234567890/like" \
  -H "Authorization: Bearer <token>"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "tweet_id": "1234567890",
    "is_liked": true,
    "like_count": 43
  }
}
```

**Idempotent:** Yes  
**Rate Limit:** 1000 likes / day

---

### DELETE /tweets/:id/like
Unlike a tweet.

```bash
curl -X DELETE "https://api.twitterclone.com/api/v1/tweets/1234567890/like" \
  -H "Authorization: Bearer <token>"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "tweet_id": "1234567890",
    "is_liked": false,
    "like_count": 42
  }
}
```

**Rate Limit:** 1000 requests / day

---

### POST /tweets/:id/retweet
Retweet a tweet.

```bash
curl -X POST "https://api.twitterclone.com/api/v1/tweets/1234567890/retweet" \
  -H "Authorization: Bearer <token>"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "retweet": {
      "id": "9876543210",
      "original_tweet_id": "1234567890",
      "created_at": "2025-10-13T11:05:00Z"
    }
  }
}
```

**Rate Limit:** 300 retweets / 3 hours

---

### POST /tweets/:id/reply
Reply to a tweet.

```bash
curl -X POST "https://api.twitterclone.com/api/v1/tweets/1234567890/reply" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Great tweet!"
  }'
```

**Request Body:**
- `content` (required): 1-280 characters

**Response (201):**
```json
{
  "success": true,
  "data": {
    "tweet": {
      "id": "1111111111",
      "content": "Great tweet!",
      "parent_tweet_id": "1234567890",
      ...
    }
  }
}
```

**Rate Limit:** 300 replies / 3 hours

---

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://api.twitterclone.com/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: '<access_token>'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Message Types

#### new_tweet
New tweet from followed user.

```json
{
  "type": "new_tweet",
  "data": {
    "tweet": {...}
  }
}
```

#### like
Someone liked your tweet.

```json
{
  "type": "like",
  "data": {
    "tweet_id": "1234567890",
    "user": {...}
  }
}
```

#### retweet
Someone retweeted your tweet.

```json
{
  "type": "retweet",
  "data": {
    "tweet_id": "1234567890",
    "user": {...}
  }
}
```

#### follow
Someone followed you.

```json
{
  "type": "follow",
  "data": {
    "user": {...}
  }
}
```

---

## Response Objects

### Tweet Object
```json
{
  "id": "1234567890",
  "user": {
    "id": "9876543210",
    "username": "johndoe",
    "display_name": "John Doe",
    "avatar_url": "https://cdn.example.com/avatars/johndoe.jpg",
    "is_verified": false
  },
  "content": "Hello, world!",
  "created_at": "2025-10-13T10:30:00Z",
  "like_count": 42,
  "retweet_count": 7,
  "reply_count": 3,
  "is_liked": false,
  "is_retweeted": false,
  "parent_tweet": null
}
```

### User Object
```json
{
  "id": "9876543210",
  "username": "johndoe",
  "display_name": "John Doe",
  "bio": "Software developer",
  "avatar_url": "https://cdn.example.com/avatars/johndoe.jpg",
  "followers_count": 1500,
  "following_count": 300,
  "tweets_count": 450,
  "is_verified": false,
  "created_at": "2025-01-15T08:00:00Z"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "content": ["Content must be between 1 and 280 characters"]
    }
  }
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to perform this action"
  }
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### 429 Too Many Requests
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 300
  }
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| GET /timeline/home | 180 | 15 min |
| GET /timeline/user/:id | 900 | 15 min |
| POST /tweets | 300 | 3 hours |
| POST /tweets | 50 | 15 min |
| DELETE /tweets/:id | 300 | 15 min |
| POST /tweets/:id/like | 1000 | 24 hours |
| POST /tweets/:id/retweet | 300 | 3 hours |
| POST /tweets/:id/reply | 300 | 3 hours |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 180
X-RateLimit-Remaining: 175
X-RateLimit-Reset: 1697194800
```

---

## Pagination

All list endpoints support cursor-based pagination.

**Request:**
```bash
curl "https://api.twitterclone.com/api/v1/timeline/home?limit=20&cursor=1697190000"
```

**Response:**
```json
{
  "data": {
    "tweets": [...],
    "next_cursor": "1697180000",
    "has_more": true
  }
}
```

**Notes:**
- Use `next_cursor` from response in next request
- `has_more` indicates if more results available
- Cursors are opaque strings (timestamp or ID)

---

## Filtering

### Timeline Filters

**Algorithm:**
- `chronological`: Sorted by time (newest first)
- `algorithmic`: ML-ranked by relevance

```bash
curl "https://api.twitterclone.com/api/v1/timeline/home?algorithm=chronological"
```

**Replies/Retweets:**
```bash
curl "https://api.twitterclone.com/api/v1/timeline/user/123?include_replies=true&include_retweets=false"
```

---

## Caching Strategy

| Endpoint | Cache-Control | CDN |
|----------|---------------|-----|
| GET /timeline/home | private, max-age=30 | No |
| GET /timeline/user/:id | public, max-age=60 | Yes |
| GET /tweets/:id | public, max-age=300 | Yes |

**ETag Support:**
```http
GET /api/v1/tweets/1234567890
If-None-Match: "abc123def456"

Response: 304 Not Modified (if unchanged)
```

---

## Best Practices

### Efficient Timeline Loading

**Use cursor pagination:**
```javascript
async function loadTimeline() {
  let cursor = null;
  let allTweets = [];
  
  do {
    const url = cursor 
      ? `/api/v1/timeline/home?limit=20&cursor=${cursor}`
      : '/api/v1/timeline/home?limit=20';
    
    const response = await fetch(url);
    const data = await response.json();
    
    allTweets.push(...data.data.tweets);
    cursor = data.data.next_cursor;
  } while (data.data.has_more);
  
  return allTweets;
}
```

### Real-time Updates

**Combine WebSocket + Polling:**
```javascript
// WebSocket for instant updates
const ws = new WebSocket('wss://api.twitterclone.com/ws');
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'new_tweet') {
    prependTweet(message.data.tweet);
  }
};

// Fallback polling every 30 seconds
setInterval(async () => {
  const response = await fetch('/api/v1/timeline/home?limit=1');
  const data = await response.json();
  // Check for new tweets
}, 30000);
```

### Optimistic UI Updates

```javascript
async function likeTweet(tweetId) {
  // Update UI immediately
  updateTweetLikeCount(tweetId, +1);
  
  try {
    // Make API call
    await fetch(`/api/v1/tweets/${tweetId}/like`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch (error) {
    // Revert on failure
    updateTweetLikeCount(tweetId, -1);
  }
}
```

---

## Testing Examples

### Jest/Vitest
```javascript
describe('Timeline API', () => {
  it('should fetch home timeline', async () => {
    const response = await fetch('/api/v1/timeline/home', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(Array.isArray(data.data.tweets)).toBe(true);
  });
});
```

### Postman Collection
```json
{
  "info": {
    "name": "Timeline API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/"
  },
  "item": [
    {
      "name": "Get Home Timeline",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/api/v1/timeline/home",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{accessToken}}"
          }
        ]
      }
    }
  ]
}
```

---

**Last Updated:** 2025-10-13  
**Document Version:** 1.0