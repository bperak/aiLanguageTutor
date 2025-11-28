# AI Language Tutor - UI Component Library

A comprehensive guide to the UI component system built with Shadcn/UI and custom components for the AI Language Tutor platform.

## 📋 Overview

The UI component library follows a design system approach with consistent styling, accessibility standards, and reusable patterns. It's built on top of Shadcn/UI components with custom extensions for language learning features.

### Design Philosophy
- **Consistency**: Unified design language across all components
- **Accessibility**: WCAG 2.1 AA compliant with proper ARIA support
- **Responsiveness**: Mobile-first responsive design
- **Modularity**: Composable and reusable components
- **Type Safety**: Full TypeScript support with prop validation

## 🎨 Design System

### Color Palette
```css
/* Light Theme */
--background: 0 0% 100%;
--foreground: 224 71.4% 4.1%;
--primary: 262.1 83.3% 57.8%;
--primary-foreground: 210 20% 98%;
--secondary: 220 14.3% 95.9%;
--muted: 220 14.3% 95.9%;
--accent: 220 14.3% 95.9%;
--destructive: 0 84.2% 60.2%;
--border: 220 13% 91%;
--input: 220 13% 91%;
--ring: 262.1 83.3% 57.8%;

/* Dark Theme */
--background: 224 71.4% 4.1%;
--foreground: 210 20% 98%;
--primary: 263.4 70% 50.4%;
--primary-foreground: 210 20% 98%;
--secondary: 215 27.9% 16.9%;
--muted: 215 27.9% 16.9%;
--accent: 215 27.9% 16.9%;
--destructive: 0 62.8% 30.6%;
--border: 215 27.9% 16.9%;
--input: 215 27.9% 16.9%;
--ring: 263.4 70% 50.4%;
```

### Typography Scale
```css
/* Font Sizes */
--text-xs: 0.75rem;     /* 12px */
--text-sm: 0.875rem;    /* 14px */
--text-base: 1rem;      /* 16px */
--text-lg: 1.125rem;    /* 18px */
--text-xl: 1.25rem;     /* 20px */
--text-2xl: 1.5rem;     /* 24px */
--text-3xl: 1.875rem;   /* 30px */
--text-4xl: 2.25rem;    /* 36px */
```

### Spacing System
```css
/* Spacing Scale (Tailwind) */
--spacing-1: 0.25rem;   /* 4px */
--spacing-2: 0.5rem;    /* 8px */
--spacing-3: 0.75rem;   /* 12px */
--spacing-4: 1rem;      /* 16px */
--spacing-6: 1.5rem;    /* 24px */
--spacing-8: 2rem;      /* 32px */
--spacing-12: 3rem;     /* 48px */
```

## 🧱 Base Components (Shadcn/UI)

### Badge Component
**File**: `src/components/ui/badge.tsx`
**Purpose**: Status indicators, labels, and tags

```tsx
import { Badge } from "@/components/ui/badge";

// Variants
<Badge variant="default">Default</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="outline">Outline</Badge>
<Badge variant="destructive">Error</Badge>

// Usage Examples
<Badge variant="secondary">Japanese</Badge>
<Badge variant="outline">Beginner</Badge>
<Badge variant="destructive">Incorrect</Badge>
```

**Props**:
- `variant`: "default" | "secondary" | "outline" | "destructive"
- `className`: Additional CSS classes

### Button Component
**File**: `src/components/ui/button.tsx`
**Purpose**: Interactive buttons with various styles and sizes

```tsx
import { Button } from "@/components/ui/button";

// Variants
<Button variant="default">Primary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Outline</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link Style</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>

// States
<Button disabled>Disabled</Button>
<Button loading>Loading...</Button>
```

**Props**:
- `variant`: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
- `size`: "default" | "sm" | "lg" | "icon"
- `disabled`: boolean
- `loading`: boolean (custom prop)
- `onClick`: () => void

### Card Component
**File**: `src/components/ui/card.tsx`
**Purpose**: Content containers with headers, content areas, and footers

```tsx
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Grammar Pattern: は (wa)</CardTitle>
    <CardDescription>Topic marker particle</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Used to mark the topic of a sentence.</p>
  </CardContent>
  <CardFooter>
    <Button>Study Now</Button>
  </CardFooter>
</Card>
```

**Components**:
- `Card`: Main container
- `CardHeader`: Header section
- `CardTitle`: Title text (h3 by default)
- `CardDescription`: Subtitle/description
- `CardContent`: Main content area
- `CardFooter`: Footer with actions

### Form Components
**File**: `src/components/ui/form.tsx`
**Purpose**: Form wrapper with validation support

```tsx
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="username"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Username</FormLabel>
          <FormControl>
            <Input placeholder="Enter username" {...field} />
          </FormControl>
          <FormDescription>
            Your unique username for the platform.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  </form>
</Form>
```

### Input Component
**File**: `src/components/ui/input.tsx`
**Purpose**: Text inputs with validation states

```tsx
import { Input } from "@/components/ui/input";

<Input type="text" placeholder="Enter text" />
<Input type="email" placeholder="email@example.com" />
<Input type="password" placeholder="Password" />

// With validation states (handled by form)
<Input error="Username is required" />
<Input success="Username is available" />
```

**Props**:
- `type`: HTML input types
- `placeholder`: string
- `disabled`: boolean
- `error`: string (for error styling)
- `success`: string (for success styling)

### Label Component
**File**: `src/components/ui/label.tsx`
**Purpose**: Form labels with accessibility support

```tsx
import { Label } from "@/components/ui/label";

<Label htmlFor="username">Username</Label>
<Input id="username" />

// With required indicator
<Label htmlFor="email" required>Email Address</Label>
```

### Modal Component
**File**: `src/components/ui/Modal.tsx`
**Purpose**: Modal dialogs and overlays

```tsx
import { Modal } from "@/components/ui/Modal";

<Modal open={isOpen} onOpenChange={setIsOpen}>
  <ModalContent>
    <ModalHeader>
      <ModalTitle>Confirm Action</ModalTitle>
      <ModalDescription>
        This action cannot be undone.
      </ModalDescription>
    </ModalHeader>
    <ModalFooter>
      <Button variant="outline" onClick={() => setIsOpen(false)}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleConfirm}>
        Delete
      </Button>
    </ModalFooter>
  </ModalContent>
</Modal>
```

### Progress Component
**File**: `src/components/ui/progress.tsx`
**Purpose**: Progress bars and completion indicators

```tsx
import { Progress } from "@/components/ui/progress";

<Progress value={33} max={100} />
<Progress value={progress} className="w-full" />

// With label
<div>
  <Label>Learning Progress: {progress}%</Label>
  <Progress value={progress} />
</div>
```

**Props**:
- `value`: number (current progress)
- `max`: number (maximum value, default: 100)

### Select Component
**File**: `src/components/ui/select.tsx`
**Purpose**: Dropdown selectors

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

<Select onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select AI Provider" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="openai">OpenAI GPT-4</SelectItem>
    <SelectItem value="gemini">Google Gemini</SelectItem>
    <SelectItem value="claude">Anthropic Claude</SelectItem>
  </SelectContent>
</Select>
```

### Tabs Component
**File**: `src/components/ui/tabs.tsx`
**Purpose**: Tabbed interfaces for content organization

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="practice">Practice</TabsTrigger>
    <TabsTrigger value="history">History</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">
    <Card>Overview content</Card>
  </TabsContent>
  <TabsContent value="practice">
    <Card>Practice content</Card>
  </TabsContent>
  <TabsContent value="history">
    <Card>History content</Card>
  </TabsContent>
</Tabs>
```

## 🎯 Custom Components

### NavBar Component
**File**: `src/components/NavBar.tsx`
**Purpose**: Main navigation with responsive design

```tsx
import { NavBar } from "@/components/NavBar";

// Usage (typically in layout)
<NavBar />
```

**Features**:
- Responsive collapsible menu
- Active route highlighting
- User authentication status
- Theme toggle integration
- Mobile-friendly hamburger menu

**Key Routes**:
- Dashboard
- Conversations
- Grammar Learning
- Knowledge Search
- Content Analysis
- SRS Practice
- Profile

### ThemeToggle Component
**File**: `src/components/ThemeToggle.tsx`
**Purpose**: Dark/light mode switcher

```tsx
import { ThemeToggle } from "@/components/ThemeToggle";

<ThemeToggle />
```

**Features**:
- System preference detection
- Persistent theme storage
- Smooth transitions
- Icon indicators (sun/moon)

### Toast System
**Files**: 
- `src/components/Toast.tsx`
- `src/components/ToastProvider.tsx`

**Purpose**: Notification system for user feedback

```tsx
// Setup (in app root)
import { ToastProvider } from "@/components/ToastProvider";

<ToastProvider>
  {children}
</ToastProvider>

// Usage in components
import { useToast } from "@/components/ui/use-toast";

const { toast } = useToast();

toast({
  title: "Success!",
  description: "Your changes have been saved.",
  variant: "default",
});

toast({
  title: "Error",
  description: "Something went wrong.",
  variant: "destructive",
});
```

**Toast Variants**:
- `default`: General notifications
- `destructive`: Error messages
- `success`: Success messages (custom)

## 🎓 Grammar Learning Components

### GrammarLearningPath Component
**File**: `src/components/grammar/GrammarLearningPath.tsx`
**Purpose**: Learning progression visualization

```tsx
import { GrammarLearningPath } from "@/components/grammar/GrammarLearningPath";

<GrammarLearningPath 
  currentLevel="beginner"
  completedPatterns={["は", "が", "を"]}
  nextPatterns={["に", "で", "と"]}
/>
```

**Features**:
- Visual progress tracking
- Pattern difficulty indicators
- Completion status
- Interactive pattern selection
- Prerequisite relationships

### GrammarPatternCard Component
**File**: `src/components/grammar/GrammarPatternCard.tsx`
**Purpose**: Interactive grammar explanations

```tsx
import { GrammarPatternCard } from "@/components/grammar/GrammarPatternCard";

<GrammarPatternCard 
  pattern={{
    id: "wa_particle",
    japanese: "は",
    romaji: "wa",
    meaning: "Topic marker",
    examples: [
      {
        japanese: "私は学生です。",
        romaji: "Watashi wa gakusei desu.",
        english: "I am a student."
      }
    ],
    difficulty: "beginner",
    prerequisites: []
  }}
/>
```

**Features**:
- Expandable content sections
- Audio pronunciation (planned)
- Example sentences with translations
- Related patterns suggestions
- Progress tracking integration

## 📱 Responsive Design Patterns

### Mobile Navigation
```tsx
// Responsive navigation pattern
<nav className="hidden md:flex md:space-x-4">
  {/* Desktop navigation */}
</nav>

<div className="md:hidden">
  {/* Mobile hamburger menu */}
  <MobileMenu />
</div>
```

### Grid Layouts
```tsx
// Responsive grid for cards
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => (
    <Card key={item.id}>
      {/* Card content */}
    </Card>
  ))}
</div>
```

### Container Widths
```tsx
// Standard container pattern
<div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
  {/* Content */}
</div>
```

## ♿ Accessibility Guidelines

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Proper tab order implementation
- Focus indicators visible
- Escape key support for modals

### Screen Reader Support
```tsx
// Proper ARIA labels
<Button aria-label="Close dialog">
  <X className="h-4 w-4" />
</Button>

// Status announcements
<div aria-live="polite" className="sr-only">
  {statusMessage}
</div>

// Form field associations
<Label htmlFor="username">Username</Label>
<Input id="username" aria-describedby="username-help" />
<div id="username-help">Enter your unique username</div>
```

### Color and Contrast
- WCAG 2.1 AA compliant contrast ratios
- No information conveyed by color alone
- Focus indicators meet contrast requirements

## 🧪 Testing Components

### Component Testing Pattern
```tsx
// Example component test
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button Component', () => {
  test('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  test('handles click events', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('shows disabled state', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

## 📊 Component Usage Analytics

### Performance Considerations
- Components are tree-shakeable
- Lazy loading for heavy components
- Memoization for expensive computations
- Virtual scrolling for large lists

### Bundle Size Impact
- Base components: ~15KB gzipped
- Custom components: ~8KB gzipped
- Grammar components: ~12KB gzipped
- Total UI library: ~35KB gzipped

## 🔄 Version History

### Current Version: 1.0.0
- ✅ All base Shadcn/UI components integrated
- ✅ Custom components for navigation and theming
- ✅ Grammar learning components
- ✅ Responsive design system
- ✅ Accessibility compliance
- ✅ TypeScript support

### Upcoming Features (v1.1.0)
- 🚧 Voice interaction components
- 🚧 Advanced animation system  
- 🚧 Component composition utilities
- 🚧 Design token system
- 🚧 Storybook integration

## 🤝 Contributing

### Adding New Components
1. **Follow naming conventions**: PascalCase for components
2. **Include TypeScript interfaces**: Proper prop types
3. **Add accessibility**: ARIA labels and keyboard support
4. **Write tests**: Component behavior and accessibility
5. **Update documentation**: Add to this guide

### Component Checklist
- [ ] TypeScript interfaces defined
- [ ] Responsive design implemented
- [ ] Accessibility tested
- [ ] Unit tests written
- [ ] Documentation updated
- [ ] Storybook story created (planned)

---

*This component library serves as the foundation for a consistent, accessible, and maintainable UI across the AI Language Tutor platform. For implementation examples, see the frontend development guide.*
