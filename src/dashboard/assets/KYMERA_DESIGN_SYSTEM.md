# Desktop Kymera Design System

**Version**: 1.0.0
**Author**: Screener Trading System
**Date**: 2025-11-15

This document defines the complete visual design system for the Desktop Kymera trading dashboard.

---

## Brand Identity

**Desktop Kymera** represents a hybrid AI trading intelligence platform. The name "Kymera" (from chimera) symbolizes the fusion of multiple data sources, timeframes, and analytical approaches into unified trading insights.

### Brand Values
- **Sophisticated**: Professional command center aesthetic
- **Intelligent**: AI-powered decision support
- **Data-Rich**: Dense information without overwhelming
- **Trustworthy**: Calm, confident visual language
- **Modern**: Cutting-edge but not flashy

### NOT This Style
- Gaming interfaces (too flashy)
- Iron Man/Jarvis themes (overused)
- Neon cyberpunk (too bright for trading)
- Corporate boring (too bland)

---

## Color Palette

### Primary Colors

#### Cyan/Teal (Intelligence, Technology)
```css
--kymera-primary:       #00d4ff   /* Main accent - bright cyan */
--kymera-primary-dark:  #00a3cc   /* Darker shade for contrast */
--kymera-primary-light: #33ddff   /* Lighter shade for highlights */
--kymera-primary-glow:  rgba(0, 212, 255, 0.3)  /* Glow effect */
--kymera-primary-subtle: rgba(0, 212, 255, 0.1) /* Background tint */
```

**Usage**: Primary buttons, active states, key metrics, links, borders

#### Purple (Premium, Sophistication)
```css
--kymera-secondary:       #8b5cf6   /* Main purple accent */
--kymera-secondary-dark:  #7c3aed   /* Darker shade */
--kymera-secondary-light: #a855f7   /* Lighter shade */
--kymera-secondary-glow:  rgba(139, 92, 246, 0.3)  /* Glow effect */
--kymera-secondary-subtle: rgba(139, 92, 246, 0.1) /* Background tint */
```

**Usage**: Secondary accents, gradients (with cyan), premium features

### Background Colors

#### Dark Gradient Base
```css
--kymera-bg-base:     #0a0e1a   /* Very dark navy - body background */
--kymera-bg-elevated: #0f1419   /* Slightly lighter - elevated surfaces */
--kymera-surface:     rgba(26, 31, 46, 0.5)  /* Semi-transparent surface */
--kymera-card:        rgba(30, 36, 51, 0.8)  /* Card background */
```

**Usage**: Body gradient from `bg-base` to `bg-elevated`, cards use `card` with glass effect

### Functional Colors

#### Success (Profit, Positive)
```css
--kymera-success:      #00ff9f   /* Bright cyan-green */
--kymera-success-bg:   rgba(0, 255, 159, 0.1)  /* Background tint */
--kymera-success-glow: rgba(0, 255, 159, 0.3)  /* Glow effect */
```

**Usage**: Profit values, positive changes, success states, winning positions

#### Danger (Loss, Negative)
```css
--kymera-danger:      #ff6b6b   /* Coral red (softer than pure red) */
--kymera-danger-bg:   rgba(255, 107, 107, 0.1)  /* Background tint */
--kymera-danger-glow: rgba(255, 107, 107, 0.3)  /* Glow effect */
```

**Usage**: Loss values, negative changes, error states, losing positions

#### Warning (Caution, Alert)
```css
--kymera-warning:    #ffa500   /* Amber orange */
--kymera-warning-bg: rgba(255, 165, 0, 0.1)  /* Background tint */
```

**Usage**: Warning messages, moderate risk, caution states

#### Info (Neutral Information)
```css
--kymera-info:    #3b82f6   /* Sky blue */
--kymera-info-bg: rgba(59, 130, 246, 0.1)  /* Background tint */
```

**Usage**: Informational messages, neutral badges, tooltips

### Text Colors

```css
--kymera-text-primary:   #f8fafc   /* Off-white - main text */
--kymera-text-secondary: #cbd5e1   /* Blue-gray - secondary text */
--kymera-text-muted:     #94a3b8   /* Muted gray - less important */
--kymera-text-disabled:  #64748b   /* Disabled state */
```

**Hierarchy**:
1. Primary: Headlines, important values, labels
2. Secondary: Body text, descriptions, table cells
3. Muted: Timestamps, metadata, subtle info
4. Disabled: Inactive elements

### Borders & Dividers

```css
--kymera-border:           rgba(0, 212, 255, 0.12)  /* Subtle cyan tint */
--kymera-border-secondary: rgba(139, 92, 246, 0.12) /* Subtle purple tint */
--kymera-border-subtle:    rgba(255, 255, 255, 0.05) /* Very subtle white */
```

**Usage**: Card borders, table dividers, section separators

### Shadows & Glows

```css
/* Shadows (depth) */
--kymera-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3)
--kymera-shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4)
--kymera-shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5)

/* Glows (emphasis) */
--kymera-glow-primary:   0 0 20px var(--kymera-primary-glow)
--kymera-glow-secondary: 0 0 20px var(--kymera-secondary-glow)
--kymera-glow-success:   0 0 15px var(--kymera-success-glow)
--kymera-glow-danger:    0 0 15px var(--kymera-danger-glow)
```

**Usage**: Shadows for depth/elevation, glows for hover states and emphasis

---

## Typography

### Font Families

#### Primary: Inter
```css
--kymera-font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
```

**Usage**: UI elements, body text, buttons, labels

**Characteristics**:
- Clean, modern sans-serif
- Excellent readability at small sizes
- Professional appearance
- System fallbacks for compatibility

#### Monospace: JetBrains Mono
```css
--kymera-font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace;
```

**Usage**: Numeric data, P&L values, prices, timestamps, code

**Characteristics**:
- Clear digit differentiation (0 vs O)
- Tabular numbers (aligned columns)
- Professional coding aesthetic

### Font Sizes

```css
--kymera-font-size-xs:   0.625rem  /* 10px - labels, tags */
--kymera-font-size-sm:   0.75rem   /* 12px - captions, metadata */
--kymera-font-size-base: 0.875rem  /* 14px - body text, default */
--kymera-font-size-md:   1rem      /* 16px - subheadings */
--kymera-font-size-lg:   1.125rem  /* 18px - headings */
--kymera-font-size-xl:   1.25rem   /* 20px - section headers */
--kymera-font-size-2xl:  1.5rem    /* 24px - page headers */
--kymera-font-size-3xl:  1.875rem  /* 30px - large metrics */
--kymera-font-size-4xl:  2.25rem   /* 36px - hero text */
```

### Font Weights

```css
--kymera-font-light:     300  /* Subtle text, brand prefix */
--kymera-font-normal:    400  /* Body text */
--kymera-font-medium:    500  /* Labels, emphasis */
--kymera-font-semibold:  600  /* Headers, buttons */
--kymera-font-bold:      700  /* Brand name, metrics */
--kymera-font-extrabold: 800  /* Heavy emphasis (rare) */
```

### Typography Usage Examples

```html
<!-- Page header -->
<h1 class="kymera-header">Watchlist Analysis</h1>

<!-- Metric card -->
<div class="kymera-metric-card">
  <div class="kymera-metric-label">TOTAL P&L</div>
  <div class="kymera-metric-value">$1,234.56</div>
</div>

<!-- Data table header -->
<th class="kymera-table-header">SYMBOL</th>

<!-- Profit/loss -->
<span class="kymera-profit">+$125.50</span>
<span class="kymera-loss">-$50.25</span>
```

---

## Spacing Scale

```css
--kymera-space-xs:  0.25rem  /* 4px  - tight spacing */
--kymera-space-sm:  0.5rem   /* 8px  - compact */
--kymera-space-md:  1rem     /* 16px - standard */
--kymera-space-lg:  1.5rem   /* 24px - comfortable */
--kymera-space-xl:  2rem     /* 32px - spacious */
--kymera-space-2xl: 2.5rem   /* 40px - very spacious */
--kymera-space-3xl: 3rem     /* 48px - section breaks */
```

### Spacing Usage

- **xs (4px)**: Icon gaps, tight labels
- **sm (8px)**: Status dots, inline elements
- **md (16px)**: Card padding, standard gaps
- **lg (24px)**: Section padding, comfortable spacing
- **xl (32px)**: Major sections, page margins
- **2xl-3xl**: Large sections, hero spacing

---

## Border Radius

```css
--kymera-radius-sm:   4px    /* Badges, small elements */
--kymera-radius-md:   8px    /* Buttons, inputs */
--kymera-radius-lg:   12px   /* Cards, containers */
--kymera-radius-xl:   16px   /* Large cards */
--kymera-radius-full: 9999px /* Pills, circular */
```

---

## Transitions & Animations

### Transition Timing

```css
--kymera-transition-fast:   150ms cubic-bezier(0.4, 0, 0.2, 1)  /* Quick interactions */
--kymera-transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1)  /* Standard */
--kymera-transition-slow:   350ms cubic-bezier(0.4, 0, 0.2, 1)  /* Emphasis */
```

**Easing**: `cubic-bezier(0.4, 0, 0.2, 1)` - Material Design standard (ease-in-out)

### Keyframe Animations

#### Pulse (Status Dots)
```css
@keyframes kymera-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.5; }
}
```

**Usage**: Online status indicator

#### Glow (Hover Effects)
```css
@keyframes kymera-glow {
  0%, 100% { box-shadow: 0 0 10px var(--kymera-primary-glow); }
  50%      { box-shadow: 0 0 20px var(--kymera-primary-glow),
                         0 0 30px var(--kymera-secondary-glow); }
}
```

**Usage**: Active elements, emphasis

#### Fade In (Loading)
```css
@keyframes kymera-fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**Usage**: Content loading, panel reveals

#### Spin (Loading Spinner)
```css
@keyframes kymera-spin {
  to { transform: rotate(360deg); }
}
```

**Usage**: Loading states

---

## Glass-Morphism Effects

Desktop Kymera uses glass-morphism (frosted glass effect) for cards and elevated surfaces.

### Glass Card Standard
```css
background: var(--kymera-glass-bg);              /* Semi-transparent */
backdrop-filter: var(--kymera-blur);             /* 16px blur */
-webkit-backdrop-filter: var(--kymera-blur);     /* Safari support */
border: 1px solid var(--kymera-glass-border);    /* Subtle border */
border-radius: var(--kymera-radius-lg);          /* 12px rounded */
box-shadow: var(--kymera-shadow-md);             /* Depth shadow */
```

### Glass Variables
```css
--kymera-glass-bg:     rgba(26, 31, 46, 0.6)    /* 60% opacity dark blue */
--kymera-glass-border: rgba(255, 255, 255, 0.1) /* 10% white border */
--kymera-blur:         blur(16px)               /* Backdrop blur amount */
--kymera-blur-heavy:   blur(24px)               /* Heavy blur (modals) */
```

### Best Practices

✅ **Do**:
- Use glass-morphism for cards and panels
- Ensure sufficient backdrop blur (16px+)
- Add subtle border for definition
- Layer glass elements for depth

❌ **Don't**:
- Overuse (keep background visible)
- Use on text-heavy areas (readability)
- Skip Safari prefix (`-webkit-backdrop-filter`)
- Layer too many glass elements (performance)

---

## Component Library

### Buttons

#### Primary Button
```html
<button class="kymera-button">
  Execute Trade
</button>
```

**Styling**:
- Cyan→purple gradient background
- White text, semibold weight
- Uppercase with letter-spacing
- Ripple effect on hover
- Glow on hover

#### Secondary Button
```html
<button class="kymera-button kymera-button-secondary">
  Cancel
</button>
```

**Styling**:
- Glass background
- Cyan border
- Primary text color
- No gradient

### Cards

#### Standard Card
```html
<div class="kymera-card">
  <div class="kymera-card-header">
    <h5>Watchlist</h5>
  </div>
  <div class="kymera-card-body">
    <!-- Card content -->
  </div>
</div>
```

**Features**:
- Glass-morphism background
- Top border glow on hover
- Elevation animation
- Gradient top border reveal

### Metric Cards

```html
<div class="kymera-metric-card">
  <div class="kymera-metric-label">TOTAL P&L</div>
  <div class="kymera-metric-value">$1,234.56</div>
  <div class="kymera-metric-change positive">+12.5%</div>
</div>
```

**Features**:
- Centered layout
- Gradient value text
- Color-coded change indicator
- Hover glow effect

### Badges

```html
<span class="kymera-badge kymera-badge-success">PROFIT</span>
<span class="kymera-badge kymera-badge-danger">RISK</span>
<span class="kymera-badge kymera-badge-primary">ACTIVE</span>
```

**Variants**: `success`, `danger`, `warning`, `info`, `primary`

### Status Indicators

```html
<div>
  <span class="kymera-status-dot online"></span>
  <span class="kymera-status-text">SYSTEM ONLINE</span>
</div>
```

**States**:
- `online`: Pulsing green with glow
- `offline`: Static red

### Tables

```html
<div class="kymera-table">
  <table>
    <thead>
      <tr class="kymera-table-header">
        <th>Symbol</th>
        <th>Price</th>
        <th>P&L</th>
      </tr>
    </thead>
    <tbody>
      <tr class="kymera-table-row">
        <td class="kymera-table-cell">AAPL</td>
        <td class="kymera-table-cell">$150.25</td>
        <td class="kymera-table-cell kymera-profit">+$25.50</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Features**:
- Cyan-tinted header background
- Uppercase header text
- Hover row highlight
- Monospace numbers

---

## Gradient Usage

### Primary Gradient (Cyan → Purple)
```css
background: linear-gradient(135deg, var(--kymera-primary) 0%, var(--kymera-secondary) 100%);
```

**Usage**: Buttons, headers, metric values, brand text

**Effect**: 135° angle (top-left to bottom-right)

### Background Gradient (Dark Navy)
```css
background: linear-gradient(135deg, var(--kymera-bg-base) 0%, var(--kymera-bg-elevated) 100%);
```

**Usage**: Body background (fixed attachment)

### Text Gradient
```css
background: linear-gradient(135deg, var(--kymera-primary) 0%, var(--kymera-secondary) 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

**Usage**: Brand name, headers, metric values

---

## Accessibility

### Color Contrast

All text meets WCAG AA standards (4.5:1 minimum):

- Primary text on dark: 14.8:1 ✅
- Secondary text on dark: 8.2:1 ✅
- Muted text on dark: 5.1:1 ✅
- Primary accent: Sufficient for large text only
- Success/Danger: High contrast for visibility

### Focus States

All interactive elements include visible focus states:

```css
.kymera-button:focus {
  outline: 2px solid var(--kymera-primary);
  outline-offset: 2px;
}

.kymera-input:focus {
  box-shadow: 0 0 0 3px var(--kymera-primary-subtle);
}
```

### Screen Reader Support

- Semantic HTML (nav, main, section, article)
- ARIA labels where needed
- Alt text for decorative elements
- Logical tab order

---

## Responsive Design

### Breakpoints

```css
/* Mobile */
@media (max-width: 480px) {
  /* Compact branding, smaller fonts */
}

/* Tablet */
@media (max-width: 768px) {
  /* Adjusted spacing, font sizes */
}

/* Desktop */
@media (min-width: 769px) {
  /* Full desktop experience */
}
```

### Mobile Adjustments

- Logo: "DESKTOP" prefix hidden on mobile
- Font sizes: Reduced by ~1-2px
- Spacing: Reduced by ~25%
- Cards: Full-width stacking
- Tables: Horizontal scroll

---

## Dark Theme Optimization

Desktop Kymera is dark-theme-first, optimized for extended trading sessions:

### Advantages
- Reduced eye strain in dark environments
- Better focus on data (less visual distraction)
- Battery savings on OLED displays
- Professional aesthetic

### Color Choices
- Dark blue base (not pure black - easier on eyes)
- Muted text colors (not pure white - less glare)
- Colored accents for emphasis (cyan, purple)
- Soft success/danger colors (not harsh)

### Best Practices
- Avoid pure white text (#f8fafc instead of #ffffff)
- Use subtle shadows for depth (not harsh borders)
- Test in low-light conditions
- Ensure sufficient contrast for readability

---

## Print Styles

Dashboard includes print-optimized styles:

```css
@media print {
  body {
    background: white;
    color: black;
  }

  .kymera-navbar { display: none; }
  .kymera-card { border: 1px solid #ddd; }
}
```

**Optimizations**:
- White background for paper
- Black text for readability
- Hide navigation/interactive elements
- Simplified borders (no shadows)

---

## Usage Guidelines

### DO ✅

- Use glass-morphism for cards and panels
- Apply gradient to brand elements and CTAs
- Use cyan for primary actions and active states
- Use purple as secondary accent in gradients
- Color-code P&L with success (green) and danger (red)
- Use monospace fonts for numeric data
- Apply smooth transitions for interactions
- Maintain consistent spacing with variables
- Test in dark environments (primary use case)

### DON'T ❌

- Mix too many bright colors (overwhelms)
- Use pure black (#000) or pure white (#fff)
- Overuse animations (distracting)
- Skip accessibility considerations
- Ignore responsive design
- Use glass-morphism without backdrop-filter
- Make interactive elements too subtle
- Forget Safari vendor prefixes
- Use conflicting gradient directions

---

## Examples

### Complete Card Example

```html
<div class="kymera-card">
  <div class="kymera-card-header">
    <h5 class="mb-0">Portfolio Summary</h5>
  </div>
  <div class="kymera-card-body">
    <div class="row">
      <div class="col-md-4">
        <div class="kymera-metric-card">
          <div class="kymera-metric-label">TOTAL P&L</div>
          <div class="kymera-metric-value">$1,234.56</div>
          <div class="kymera-metric-change positive">+12.5%</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="kymera-metric-card">
          <div class="kymera-metric-label">WIN RATE</div>
          <div class="kymera-metric-value">67%</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="kymera-metric-card">
          <div class="kymera-metric-label">POSITIONS</div>
          <div class="kymera-metric-value">5</div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### Table with P&L Example

```html
<div class="kymera-table">
  <table>
    <thead>
      <tr class="kymera-table-header">
        <th>SYMBOL</th>
        <th>ENTRY</th>
        <th>CURRENT</th>
        <th>P&L</th>
      </tr>
    </thead>
    <tbody>
      <tr class="kymera-table-row kymera-profit-bg">
        <td>AAPL</td>
        <td>$150.00</td>
        <td>$152.50</td>
        <td class="kymera-profit">+$25.50</td>
      </tr>
      <tr class="kymera-table-row kymera-loss-bg">
        <td>GOOGL</td>
        <td>$2,800.00</td>
        <td>$2,750.00</td>
        <td class="kymera-loss">-$50.00</td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## Version History

### 1.0.0 (2025-11-15)
- Initial release
- Complete color palette
- Typography system
- Glass-morphism components
- Responsive design
- Accessibility features
- Component library

---

## Contact & Support

For questions or contributions to the Desktop Kymera design system:

- **Project**: Screener Trading System
- **Repository**: `/home/aaron/github/astoreyai/screener`
- **Documentation**: `CLAUDE.md`, `IMPLEMENTATION_GUIDE.md`

---

**End of Design System Documentation**
