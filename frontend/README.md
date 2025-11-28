# AI Language Tutor - Frontend Development Guide

A comprehensive Next.js 14+ application with TypeScript, providing an intelligent and responsive UI for the AI Language Tutor platform.

## 🏗️ Architecture Overview

### Technology Stack
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + Shadcn/UI component library
- **State Management**: 
  - **Server State**: TanStack Query (React Query)
  - **Client State**: Zustand
- **Authentication**: JWT tokens with secure storage
- **API Integration**: Custom hooks with error handling
- **UI Components**: Shadcn/UI + custom components

### Project Structure
```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── (auth)/            # Authentication routes
│   │   ├── login/
│   │   └── register/
│   ├── dashboard/         # Main dashboard
│   ├── conversations/     # Real-time chat interface
│   ├── content/           # Content analysis
│   ├── grammar/           # Grammar learning
│   ├── knowledge/         # Knowledge search
│   ├── profile/           # User profile
│   ├── srs/              # Spaced repetition
│   └── layout.tsx        # Root layout with navigation
├── components/
│   ├── grammar/          # Grammar-specific components
│   ├── ui/               # Shadcn/UI base components
│   ├── NavBar.tsx        # Main navigation
│   ├── ThemeToggle.tsx   # Dark/light mode toggle
│   ├── Toast.tsx         # Notification system
│   └── ToastProvider.tsx # Toast context provider
└── lib/                  # Utilities and configurations
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm, yarn, or pnpm
- Backend API running on `http://localhost:8000`

### Environment Setup
1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Set up environment variables:
```bash
# Create .env.local file
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=AI Language Tutor
```

### Development Server
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## 📱 Key Features

### 1. Authentication System
- **Location**: `src/app/(auth)/`
- **Features**: 
  - User registration with validation
  - Secure login with JWT tokens
  - Password strength indicators
  - Form validation and error handling
  - Auto-redirect after authentication

### 2. Real-time Conversation Interface
- **Location**: `src/app/conversations/`
- **Features**:
  - Streaming AI responses
  - Multi-provider AI selection (OpenAI/Gemini)
  - Session management
  - Message history
  - Export functionality
  - Responsive chat UI

### 3. Learning Dashboard
- **Location**: `src/app/dashboard/`
- **Features**:
  - Personalized analytics
  - Progress visualization
  - Session summaries
  - Performance metrics
  - Learning insights

### 4. Content Analysis
- **Location**: `src/app/content/`
- **Features**:
  - Text analysis interface
  - File upload (PDF, TXT, DOCX)
  - URL content processing
  - Results visualization
  - Source attribution

### 5. Grammar Learning
- **Location**: `src/app/grammar/`
- **Features**:
  - Interactive pattern cards
  - Learning path visualization
  - Progress tracking
  - Study interface

### 6. SRS (Spaced Repetition)
- **Location**: `src/app/srs/`
- **Features**:
  - Review queue management
  - Practice sessions
  - Performance tracking
  - Scheduling algorithm integration

## 🎨 UI Component Library

### Base Components (Shadcn/UI)
- **`badge.tsx`** - Status indicators and labels
- **`button.tsx`** - Primary/secondary buttons with variants
- **`card.tsx`** - Content containers with headers/footers
- **`form.tsx`** - Form wrapper components with validation
- **`input.tsx`** - Text inputs with validation states
- **`label.tsx`** - Form labels with accessibility
- **`Modal.tsx`** - Modal dialogs and overlays
- **`progress.tsx`** - Progress bars and indicators
- **`select.tsx`** - Dropdown selectors
- **`tabs.tsx`** - Tabbed interfaces

### Custom Components
- **`NavBar.tsx`** - Main navigation with responsive design
- **`ThemeToggle.tsx`** - Dark/light mode switcher
- **`Toast.tsx`** - Notification messages
- **`ToastProvider.tsx`** - Toast context and management

### Grammar Components
- **`GrammarLearningPath.tsx`** - Learning progression visualization
- **`GrammarPatternCard.tsx`** - Interactive grammar explanations

## 🔄 State Management

### Server State (TanStack Query)
Used for API data fetching with automatic caching, background updates, and error handling:

```typescript
// Example: Fetching conversation data
const { data, isLoading, error } = useQuery({
  queryKey: ['conversations', userId],
  queryFn: () => fetchConversations(userId),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

### Client State (Zustand)
Used for UI state, user preferences, and temporary data:

```typescript
// Example: Theme store
interface ThemeStore {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const useThemeStore = create<ThemeStore>((set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({ 
    theme: state.theme === 'light' ? 'dark' : 'light' 
  })),
}));
```

## 🌐 API Integration

### Base Configuration
```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export const apiClient = {
  get: async (endpoint: string) => {
    const token = getAuthToken();
    return fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
  },
  // ... other methods
};
```

### Custom Hooks Pattern
```typescript
// hooks/useConversations.ts
export const useConversations = () => {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => apiClient.get('/api/v1/conversations/sessions'),
    select: (data) => data.json(),
  });
};
```

## 🎯 Responsive Design

### Mobile-First Approach
All components use Tailwind's responsive utilities:

```tsx
<div className="flex flex-col md:flex-row lg:gap-8">
  <aside className="w-full md:w-1/3 lg:w-1/4">
    {/* Sidebar content */}
  </aside>
  <main className="flex-1 mt-4 md:mt-0">
    {/* Main content */}
  </main>
</div>
```

### Breakpoint Strategy
- **Mobile**: Default styles (< 768px)
- **Tablet**: `md:` prefix (768px+)
- **Desktop**: `lg:` prefix (1024px+)
- **Large Desktop**: `xl:` prefix (1280px+)

## ⚡ Performance Optimizations

### Code Splitting
- **Dynamic Imports**: Heavy components loaded on demand
- **Route-based splitting**: Automatic with App Router
- **Component-level splitting**: For modal dialogs and complex features

### Image Optimization
```tsx
import Image from 'next/image';

<Image
  src="/language-flag.png"
  alt="Language flag"
  width={32}
  height={32}
  priority={false}
  className="rounded"
/>
```

### Bundle Optimization
```typescript
// next.config.ts
const config = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['example.com'],
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, 'src'),
    };
    return config;
  },
};
```

## 🧪 Development Guidelines

### Component Development
1. **Functional Components**: Use function declarations with TypeScript
2. **Props Interface**: Define explicit TypeScript interfaces
3. **Error Boundaries**: Wrap components with error handling
4. **Accessibility**: Include ARIA labels and keyboard navigation
5. **Testing**: Write unit tests for complex logic

### Code Style
```typescript
// ✅ Good: Clear component structure
interface UserProfileProps {
  userId: string;
  onUpdate?: (user: User) => void;
}

export function UserProfile({ userId, onUpdate }: UserProfileProps) {
  const { data: user, isLoading } = useUser(userId);
  
  if (isLoading) return <Skeleton />;
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>{user.name}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Content */}
      </CardContent>
    </Card>
  );
}
```

### Error Handling
```typescript
// Global error boundary
export function ErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ReactErrorBoundary
          onReset={reset}
          fallbackRender={({ error, resetErrorBoundary }) => (
            <ErrorFallback error={error} onReset={resetErrorBoundary} />
          )}
        >
          {children}
        </ReactErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}
```

## 🔒 Security Best Practices

### Token Management
- **Secure Storage**: JWT tokens stored in httpOnly cookies when possible
- **Auto Refresh**: Implement token refresh logic
- **Logout**: Clear all auth data on logout

### API Security
- **CSRF Protection**: Use proper headers and validation
- **XSS Prevention**: Sanitize user inputs
- **Content Security Policy**: Configure appropriate CSP headers

## 🚀 Build & Deployment

### Production Build
```bash
npm run build
npm run start
```

### Environment Variables
```bash
# Production
NEXT_PUBLIC_API_BASE_URL=https://api.ailanguagetutor.com
NEXT_PUBLIC_APP_NAME=AI Language Tutor
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=https://ailanguagetutor.com
```

### Deployment Options
- **Vercel**: Recommended for Next.js apps
- **Google Cloud Run**: Containerized deployment
- **Docker**: Custom container deployment

## 📊 Performance Monitoring

### Core Web Vitals
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms  
- **CLS** (Cumulative Layout Shift): < 0.1

### Monitoring Tools
- **Next.js Analytics**: Built-in performance monitoring
- **Web Vitals**: Real user monitoring
- **Lighthouse**: Development performance audits

## 🤝 Contributing

1. **Code Standards**: Follow TypeScript strict mode
2. **Component Structure**: Use consistent patterns
3. **Testing**: Write tests for new features
4. **Documentation**: Update README for new components
5. **Performance**: Monitor bundle size and Core Web Vitals

---

*This guide covers the essential aspects of frontend development for the AI Language Tutor platform. For backend integration details, see the main project documentation.*
