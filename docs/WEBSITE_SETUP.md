# Setting Up marcus-ai.dev Documentation Site

Complete guide to creating a documentation website that looks like docs.anthropic.com.

## Technology Stack

Anthropic uses **Next.js** with **Mintlify** or a similar documentation framework. For Marcus, I recommend:

### Option 1: Mintlify (Easiest - Like Anthropic)

**Pros**:
- Looks exactly like docs.anthropic.com
- Hosted solution (no infrastructure management)
- Built-in search, navigation, versioning
- Free tier available
- Markdown-based (your docs are already compatible)

**Cons**:
- Requires Mintlify account
- Less customization than self-hosted

### Option 2: Nextra (Self-Hosted Next.js)

**Pros**:
- Full control and customization
- Next.js-based (modern, fast)
- Free to host anywhere
- Used by many popular projects (Vercel, Tailwind)

**Cons**:
- Requires more setup
- Need to manage hosting

### Option 3: Docusaurus (Facebook's Docs Framework)

**Pros**:
- Battle-tested (React, Redux, Jest use it)
- Rich plugin ecosystem
- Excellent search and navigation
- Free and open source

**Cons**:
- Different look from Anthropic (but customizable)
- React-based learning curve

## Recommended: Mintlify Setup (Like Anthropic)

Mintlify is the fastest way to get an Anthropic-style docs site.

### Step 1: Install Mintlify CLI

```bash
npm i -g mintlify

# Or using yarn
yarn global add mintlify
```

### Step 2: Initialize in Your Docs Folder

```bash
cd /Users/lwgray/dev/marcus/docs
mintlify init
```

This creates a `mint.json` configuration file.

### Step 3: Configure mint.json

Create/edit `mint.json`:

```json
{
  "name": "Marcus AI",
  "logo": {
    "light": "/logo/light.svg",
    "dark": "/logo/dark.svg"
  },
  "favicon": "/favicon.png",
  "colors": {
    "primary": "#0D9373",
    "light": "#07C983",
    "dark": "#0D9373",
    "background": {
      "dark": "#0F0F0F"
    }
  },
  "topbarLinks": [
    {
      "name": "GitHub",
      "url": "https://github.com/lwgray/marcus"
    }
  ],
  "topbarCtaButton": {
    "name": "Get Started",
    "url": "https://marcus-ai.dev"
  },
  "anchors": [
    {
      "name": "Documentation",
      "icon": "book-open-cover",
      "url": "docs"
    },
    {
      "name": "Community",
      "icon": "discord",
      "url": "https://discord.gg/your-discord"
    },
    {
      "name": "Blog",
      "icon": "newspaper",
      "url": "https://marcus-ai.dev/blog"
    }
  ],
  "navigation": [
    {
      "group": "Getting Started",
      "pages": [
        "getting-started/introduction",
        "getting-started/quickstart",
        "getting-started/core-concepts",
        "getting-started/setup-local-llm"
      ]
    },
    {
      "group": "Concepts",
      "pages": [
        "concepts/philosophy",
        "concepts/core-values"
      ]
    },
    {
      "group": "Agent Workflows",
      "pages": [
        "guides/agent-workflows/agent-workflow",
        "guides/agent-workflows/registration",
        "guides/agent-workflows/requesting-tasks",
        "guides/agent-workflows/reporting-progress",
        "guides/agent-workflows/handling-blockers",
        "guides/agent-workflows/getting-context",
        "guides/agent-workflows/checking-dependencies"
      ]
    },
    {
      "group": "Project Management",
      "pages": [
        "guides/project-management/creating-projects",
        "guides/project-management/monitoring-status",
        "guides/project-management/analyzing-health"
      ]
    },
    {
      "group": "Collaboration",
      "pages": [
        "guides/collaboration/communication-hub",
        "guides/collaboration/logging-decisions",
        "guides/collaboration/tracking-artifacts"
      ]
    },
    {
      "group": "Advanced",
      "pages": [
        "guides/advanced/memory-system",
        "guides/advanced/agent-support-tools",
        "guides/advanced/agent-status",
        "guides/advanced/ping-system"
      ]
    },
    {
      "group": "Systems",
      "pages": [
        "systems/README",
        {
          "group": "Intelligence",
          "pages": [
            "systems/intelligence/01-memory-system",
            "systems/intelligence/07-ai-intelligence-engine",
            "systems/intelligence/17-learning-systems",
            "systems/intelligence/23-task-management-intelligence",
            "systems/intelligence/27-recommendation-engine",
            "systems/intelligence/44-enhanced-task-classifier"
          ]
        },
        {
          "group": "Coordination",
          "pages": [
            "systems/coordination/03-context-dependency-system",
            "systems/coordination/12-communication-hub",
            "systems/coordination/21-agent-coordination",
            "systems/coordination/26-worker-support",
            "systems/coordination/33-orphan-task-recovery",
            "systems/coordination/35-assignment-lease-system",
            "systems/coordination/36-task-dependency-system"
          ]
        }
      ]
    },
    {
      "group": "API Reference",
      "pages": [
        "api/README"
      ]
    },
    {
      "group": "Roadmap",
      "pages": [
        "roadmap/evolution",
        "roadmap/public-release-roadmap",
        "roadmap/future-systems"
      ]
    }
  ],
  "footerSocials": {
    "github": "https://github.com/lwgray/marcus",
    "twitter": "https://twitter.com/your-handle",
    "linkedin": "https://www.linkedin.com/company/your-company"
  },
  "analytics": {
    "ga4": {
      "measurementId": "G-XXXXXXXXXX"
    }
  }
}
```

### Step 4: Preview Locally

```bash
cd /Users/lwgray/dev/marcus/docs
mintlify dev
```

Visit `http://localhost:3000` to see your docs!

### Step 5: Deploy to Mintlify (Easiest)

```bash
# Connect to Mintlify
mintlify deploy

# Follow prompts to connect GitHub repo
# Choose subdomain or custom domain
```

Configure custom domain in Mintlify dashboard:
- Point `docs.marcus-ai.dev` to Mintlify
- Or use `marcus-ai.dev/docs` path

### Step 6: Connect Custom Domain

In your DNS settings (wherever you bought marcus-ai.dev):

```
Type: CNAME
Name: docs (or @)
Value: [provided by Mintlify]
```

## Alternative: Self-Hosted with Nextra

If you want more control, use Nextra (Next.js framework):

### Step 1: Create Nextra Project

```bash
# In your marcus repo
mkdir website
cd website

# Initialize Next.js with Nextra
npx create-next-app@latest --example with-nextra docs-site
cd docs-site
```

### Step 2: Configure Nextra

Edit `theme.config.jsx`:

```jsx
export default {
  logo: <span>Marcus AI Documentation</span>,
  project: {
    link: 'https://github.com/lwgray/marcus'
  },
  docsRepositoryBase: 'https://github.com/lwgray/marcus/tree/main/docs',
  footer: {
    text: 'Marcus AI - Intelligent Agent Coordination'
  },
  primaryHue: 162, // Teal color like Anthropic
  sidebar: {
    defaultMenuCollapseLevel: 1
  },
  navigation: {
    prev: true,
    next: true
  },
  toc: {
    float: true,
    title: 'On This Page'
  },
  search: {
    placeholder: 'Search documentation...'
  }
}
```

### Step 3: Copy Your Docs

```bash
# Copy your organized docs
cp -r /Users/lwgray/dev/marcus/docs/* pages/
```

### Step 4: Add Custom Styling (Anthropic Look)

Create `styles/global.css`:

```css
/* Anthropic-inspired styling */
:root {
  --primary-color: #0D9373;
  --secondary-color: #07C983;
  --background: #FFFFFF;
  --background-dark: #0F0F0F;
  --text-primary: #1A1A1A;
  --text-secondary: #666666;
}

[data-theme='dark'] {
  --background: var(--background-dark);
  --text-primary: #FFFFFF;
  --text-secondary: #A0A0A0;
}

/* Clean, modern typography like Anthropic */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Code blocks */
code {
  font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
}

/* Links */
a {
  color: var(--primary-color);
  text-decoration: none;
  transition: color 0.2s ease;
}

a:hover {
  color: var(--secondary-color);
}

/* Navigation sidebar */
.nextra-sidebar-container {
  border-right: 1px solid rgba(0, 0, 0, 0.1);
}

[data-theme='dark'] .nextra-sidebar-container {
  border-right-color: rgba(255, 255, 255, 0.1);
}

/* Search bar */
.nextra-search input {
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 8px 16px;
}

/* Cards (for homepage) */
.card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 24px;
  transition: all 0.2s ease;
}

.card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(13, 147, 115, 0.1);
}
```

### Step 5: Deploy to Vercel (Free)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Follow prompts
# Connect to GitHub
# Configure domain: marcus-ai.dev
```

Configure custom domain in Vercel dashboard:
- Add `marcus-ai.dev`
- Vercel provides DNS configuration
- Update your DNS records

## Main Landing Page (marcus-ai.dev)

For the main landing page (not docs), create a separate Next.js site or add to Nextra:

### Landing Page Structure

```
website/
├── pages/
│   ├── index.jsx              # Main landing page
│   ├── docs/                  # Documentation (linked above)
│   ├── blog/                  # Blog posts
│   └── api/                   # API if needed
├── components/
│   ├── Hero.jsx               # Hero section
│   ├── Features.jsx           # Feature cards
│   ├── CTA.jsx                # Call-to-action
│   └── Footer.jsx             # Footer
├── styles/
│   └── globals.css            # Anthropic-style CSS
└── public/
    ├── logo/                  # Logos
    └── images/                # Images
```

### Sample Hero Component (Anthropic Style)

```jsx
// components/Hero.jsx
export default function Hero() {
  return (
    <div className="hero">
      <div className="hero-content">
        <h1 className="hero-title">
          Intelligent Agent Coordination for Software Development
        </h1>
        <p className="hero-subtitle">
          Marcus enables AI agents to collaborate autonomously on projects,
          with context, intelligence, and transparency built-in.
        </p>
        <div className="hero-buttons">
          <a href="/docs/getting-started/quickstart" className="btn-primary">
            Get Started
          </a>
          <a href="/docs" className="btn-secondary">
            Documentation
          </a>
        </div>
      </div>
      <div className="hero-demo">
        {/* Add animated demo or screenshot */}
      </div>
    </div>
  )
}
```

### Landing Page CSS (Anthropic Style)

```css
/* styles/landing.css */
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  padding: 120px 60px;
  max-width: 1400px;
  margin: 0 auto;
  align-items: center;
}

.hero-title {
  font-size: 56px;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.hero-subtitle {
  font-size: 20px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 32px;
}

.hero-buttons {
  display: flex;
  gap: 16px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  padding: 14px 32px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: var(--secondary-color);
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(13, 147, 115, 0.2);
}

.btn-secondary {
  border: 2px solid var(--primary-color);
  color: var(--primary-color);
  padding: 12px 32px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: rgba(13, 147, 115, 0.05);
}

/* Feature cards */
.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
  padding: 80px 60px;
  max-width: 1400px;
  margin: 0 auto;
}

.feature-card {
  padding: 32px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.feature-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-4px);
}

.feature-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
  color: var(--primary-color);
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
}

.feature-description {
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 60px 24px;
  }

  .hero-title {
    font-size: 36px;
  }

  .features {
    grid-template-columns: 1fr;
    padding: 40px 24px;
  }
}
```

## DNS Configuration

For `marcus-ai.dev`:

### If Using Mintlify

```
# Docs subdomain
Type: CNAME
Name: docs
Value: [mintlify-provided-url]

# Main site (on Vercel/Netlify)
Type: A
Name: @
Value: [vercel-ip-address]
```

### If All-in-One with Vercel

```
# Point everything to Vercel
Type: A
Name: @
Value: 76.76.21.21 (Vercel's IP)

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

## Deployment Checklist

- [ ] Choose framework (Mintlify recommended)
- [ ] Set up local development
- [ ] Configure navigation and structure
- [ ] Customize colors/branding
- [ ] Add logo and favicon
- [ ] Test all internal links
- [ ] Set up custom domain
- [ ] Configure DNS records
- [ ] Test on mobile/tablet
- [ ] Add analytics (Google Analytics)
- [ ] Set up search functionality
- [ ] Add meta tags for SEO
- [ ] Create sitemap.xml
- [ ] Test page load speed
- [ ] Add social media preview images

## Recommended Quick Path

**For fastest deployment:**

1. Use **Mintlify** for docs → `docs.marcus-ai.dev`
2. Use **Vercel + Next.js** for landing page → `marcus-ai.dev`
3. Both can be live in < 1 hour

**Steps**:
```bash
# 1. Set up Mintlify docs
cd /Users/lwgray/dev/marcus/docs
npm i -g mintlify
mintlify init
mintlify dev  # test locally
mintlify deploy  # deploy

# 2. Create landing page
cd /Users/lwgray/dev/marcus
mkdir website && cd website
npx create-next-app@latest landing
cd landing
# Add Hero, Features, CTA components
vercel deploy  # deploy

# 3. Configure DNS
# Add records as shown above
```

**Result**: Professional docs site that looks like Anthropic's, deployed and live!

## Need Help?

- **Mintlify Docs**: https://mintlify.com/docs
- **Nextra Docs**: https://nextra.site
- **Vercel Docs**: https://vercel.com/docs
- **Next.js Docs**: https://nextjs.org/docs

---

**Want me to set this up for you?** I can create the complete website structure with Anthropic-style design!
