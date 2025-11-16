# Desktop Kymera Theme Assets

This directory contains the Desktop Kymera UI theme for the Screener trading dashboard.

## Files

### kymera_theme.css (1200+ lines)
Complete CSS theme with:
- Color palette (20+ variables)
- Typography system (Inter + JetBrains Mono)
- Glass-morphism effects
- Component styling
- Animations and transitions
- Bootstrap component overrides
- Responsive design
- Accessibility features

**Auto-loaded by Dash** - No manual import needed.

### KYMERA_DESIGN_SYSTEM.md (500+ lines)
Complete design documentation with:
- Brand identity and values
- Color palette specifications
- Typography guidelines
- Component library
- Usage examples
- Best practices
- Accessibility notes

## Quick Start

The theme is automatically loaded when the dashboard starts:

```python
# In app.py
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],  # Dark base
    assets_folder='assets'  # Auto-loads kymera_theme.css
)
```

## Using the Theme

### Apply Kymera Classes

```python
# Glass-morphism card
dbc.Card([...], className="kymera-card")

# Branded button
dbc.Button("Execute", color="primary", className="kymera-button")

# Metric card
html.Div([
    html.Div("TOTAL P&L", className="kymera-metric-label"),
    html.Div("$1,234.56", className="kymera-metric-value")
], className="kymera-metric-card")

# Profit/loss styling
html.Span("+$125.50", className="kymera-profit")
html.Span("-$50.25", className="kymera-loss")
```

### Use Branding Components

```python
from src.dashboard.components.branding import (
    create_kymera_header,
    create_metric_card,
    create_badge,
    create_section_header
)

# Header with logo, status, clock
header = create_kymera_header()

# Metric card
card = create_metric_card("Total P&L", "$1,234.56", "+12.5%", True)

# Badge
badge = create_badge("Active", "success")
```

## Color Palette

### Primary Accents
- `--kymera-primary`: #00d4ff (cyan)
- `--kymera-secondary`: #8b5cf6 (purple)

### Functional Colors
- `--kymera-success`: #00ff9f (profit/positive)
- `--kymera-danger`: #ff6b6b (loss/negative)
- `--kymera-warning`: #ffa500 (caution)
- `--kymera-info`: #3b82f6 (neutral)

### Text Colors
- `--kymera-text-primary`: #f8fafc (main text)
- `--kymera-text-secondary`: #cbd5e1 (body text)
- `--kymera-text-muted`: #94a3b8 (subtle text)

See `KYMERA_DESIGN_SYSTEM.md` for complete palette.

## CSS Classes Reference

### Layout
- `kymera-dashboard` - Main container
- `kymera-card` - Glass-morphism card
- `kymera-navbar` - Branded navbar

### Typography
- `kymera-header` - Gradient header
- `kymera-metric-label` - Metric label (small, uppercase)
- `kymera-metric-value` - Large metric value (gradient)

### Components
- `kymera-button` - Primary button (gradient)
- `kymera-button-secondary` - Secondary button (glass)
- `kymera-badge` - Badge/tag element
- `kymera-badge-{variant}` - Colored badges (success, danger, etc.)

### Tables
- `kymera-table` - Table container
- `kymera-table-header` - Table header row
- `kymera-table-row` - Table body row
- `kymera-table-cell` - Table cell

### Status
- `kymera-status-dot` - Status indicator dot
- `kymera-status-text` - Status text
- `kymera-profit` - Profit text (green)
- `kymera-loss` - Loss text (red)
- `kymera-profit-bg` - Profit background
- `kymera-loss-bg` - Loss background

### Utilities
- `kymera-flex`, `kymera-flex-center` - Flexbox utilities
- `kymera-text-{left|center|right}` - Text alignment
- `kymera-m-{0-3}`, `kymera-p-{0-3}` - Spacing utilities

## Customization

### Override CSS Variables

```css
/* In a custom CSS file */
:root {
    --kymera-primary: #ff00ff;  /* Change primary color */
    --kymera-font-size-base: 1rem;  /* Increase base font size */
}
```

### Extend Theme

```css
/* Add custom component */
.my-custom-component {
    background: var(--kymera-glass-bg);
    border: 1px solid var(--kymera-border);
    border-radius: var(--kymera-radius-lg);
    padding: var(--kymera-space-md);
}
```

## Browser Support

- Chrome/Edge: Full support ✅
- Firefox: Full support ✅
- Safari: Full support ✅ (includes `-webkit-` prefixes)
- Mobile: Responsive design ✅

## Performance

- CSS file size: ~60KB
- Automatically minified in production
- Uses hardware-accelerated animations
- Optimized backdrop-filter for glass effects

## Accessibility

- WCAG AA contrast ratios ✅
- Focus states on all interactive elements ✅
- Semantic HTML support ✅
- Screen reader compatible ✅

## Development

### Testing Theme Changes

```bash
# Start dashboard
python src/dashboard/app.py

# Navigate to http://localhost:8050
# Changes auto-reload in debug mode
```

### Validate CSS

```bash
# Use CSS validator (optional)
npm install -g csslint
csslint src/dashboard/assets/kymera_theme.css
```

## Documentation

- Full design system: `KYMERA_DESIGN_SYSTEM.md`
- Branding components: `../components/branding.py`
- Dashboard integration: `../app.py`

## License

Part of the Screener Trading System project.

## Support

For questions or issues with the theme:
1. Check `KYMERA_DESIGN_SYSTEM.md` for design guidelines
2. Review example usage in `app.py`
3. Consult component documentation in `branding.py`

---

**Desktop Kymera** - Sophisticated AI Trading Intelligence
