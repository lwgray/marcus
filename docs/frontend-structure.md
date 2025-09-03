# Task Master Frontend Structure

## Framework: React with TypeScript

## Architecture Overview

### Directory Structure
```
src/
├── components/         # Reusable UI components
│   ├── common/        # Generic components
│   ├── layout/        # Layout components (Layout.tsx)
│   └── features/      # Feature-specific components
├── pages/             # Route page components (HomePage.tsx)
├── services/          # API service layer
│   ├── api.ts        # Base API client with auth headers
│   └── auth.service.ts # Authentication service
├── store/             # Redux store configuration
│   └── index.ts      # Store setup with TypeScript
├── hooks/             # Custom React hooks
│   └── redux.ts      # Typed Redux hooks
├── router/            # React Router configuration
│   └── index.tsx     # Route definitions
├── types/             # TypeScript type definitions
├── utils/             # Utility functions
└── styles/            # Global styles

```

## State Management: Redux Toolkit

- Store configured at `src/store/index.ts`
- Typed hooks at `src/hooks/redux.ts`
- Use `useAppDispatch` and `useAppSelector` for type safety

## Routing: React Router v6

- Router configuration at `src/router/index.tsx`
- Layout component at `src/components/layout/Layout.tsx`
- Add new routes as children of the Layout route

## API Service Layer

### Base API Client (`src/services/api.ts`)
- Automatic auth token injection from localStorage
- Error handling with custom ApiError class
- Methods: `api.get()`, `api.post()`, `api.put()`, `api.delete()`

### Authentication Service (`src/services/auth.service.ts`)
- Login: `POST /api/auth/login`
- Register: `POST /api/auth/register`
- Logout: `POST /api/auth/logout`
- Get current user: `GET /api/auth/me`

## Environment Configuration
- Use `.env` file for configuration
- API base URL: `VITE_API_BASE_URL` (default: http://localhost:3000/api)

## Build and Development
- Development: `npm run dev`
- Build: `npm run build`
- Preview: `npm run preview`

## Integration Points for Backend
- API endpoints should be prefixed with `/api`
- Authentication uses Bearer token in Authorization header
- Expected auth response format:
  ```typescript
  {
    token: string;
    user: {
      id: string;
      email: string;
      name: string;
    }
  }
  ```
