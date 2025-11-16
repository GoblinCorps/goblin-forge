"""
Desktop Kymera Branding Components

Provides branded UI elements for the Screener trading dashboard including
logo, navbar, and status indicators.

Features:
---------
- Desktop Kymera logo with gradient effect
- AI Trading Intelligence tagline
- System status indicators (online/offline)
- Glass-morphism navbar with sticky positioning
- Professional color scheme (cyan/purple accents)

Usage:
------
from src.dashboard.components.branding import create_kymera_header

# Add to dashboard layout
layout = html.Div([
    create_kymera_header(),
    # ... rest of layout
])

Author: Screener Trading System
Date: 2025-11-15
"""

from typing import Optional
import dash_bootstrap_components as dbc
from dash import html
from datetime import datetime


def create_kymera_logo(compact: bool = False) -> html.Div:
    """
    Create Desktop Kymera logo/branding element.

    Parameters:
    -----------
    compact : bool, default=False
        If True, use compact layout for mobile/small screens

    Returns:
    --------
    html.Div
        Logo component with gradient text effect and tagline

    Visual Design:
    --------------
    - "DESKTOP" in light gray (300 weight)
    - "KYMERA" in cyan→purple gradient (700 weight)
    - "AI Trading Intelligence" tagline (uppercase, small)
    - Gradient background-clip for modern effect

    Examples:
    ---------
    >>> # Standard logo
    >>> logo = create_kymera_logo()

    >>> # Compact logo (no tagline)
    >>> mobile_logo = create_kymera_logo(compact=True)
    """
    if compact:
        return html.Div([
            html.H3([
                html.Span("KYMERA", className="kymera-brand-name")
            ], className="kymera-logo mb-0")
        ], className="kymera-branding")

    return html.Div([
        html.H2([
            html.Span("DESKTOP ", className="kymera-brand-prefix"),
            html.Span("KYMERA", className="kymera-brand-name")
        ], className="kymera-logo"),
        html.P("AI Trading Intelligence", className="kymera-tagline")
    ], className="kymera-branding")


def create_status_indicator(
    status: str = "online",
    text: Optional[str] = None
) -> html.Div:
    """
    Create system status indicator with animated dot.

    Parameters:
    -----------
    status : str, default="online"
        Status type: "online" (green pulse) or "offline" (red static)
    text : str, optional
        Status text to display. Defaults to "SYSTEM ONLINE" or "SYSTEM OFFLINE"

    Returns:
    --------
    html.Div
        Status indicator with colored dot and text

    Visual Design:
    --------------
    - Online: Pulsing green dot with glow effect
    - Offline: Static red dot
    - Uppercase monospace text
    - Color-coded text matching dot

    Examples:
    ---------
    >>> # Online indicator
    >>> status = create_status_indicator("online")

    >>> # Offline with custom text
    >>> status = create_status_indicator("offline", "CONNECTION LOST")

    >>> # Custom status message
    >>> status = create_status_indicator("online", "TRADING ACTIVE")
    """
    if text is None:
        text = "SYSTEM ONLINE" if status == "online" else "SYSTEM OFFLINE"

    dot_class = f"kymera-status-dot {status}"

    return html.Div([
        html.Span(className=dot_class),
        html.Span(text, className="kymera-status-text")
    ], className="d-flex align-items-center")


def create_kymera_header(
    show_clock: bool = True,
    show_status: bool = True,
    system_status: str = "online"
) -> dbc.Navbar:
    """
    Create branded navbar header with logo, status, and clock.

    Parameters:
    -----------
    show_clock : bool, default=True
        Display live clock on right side
    show_status : bool, default=True
        Display system status indicator
    system_status : str, default="online"
        System status: "online" or "offline"

    Returns:
    --------
    dbc.Navbar
        Branded navbar with glass-morphism effect and sticky positioning

    Visual Design:
    --------------
    - Glass-morphism background with blur effect
    - Sticky top positioning (stays visible on scroll)
    - Gradient border at bottom
    - Logo on left, status/clock on right
    - Responsive layout

    Layout:
    -------
    [Logo]                          [Status] [Clock]
    DESKTOP KYMERA                  ● ONLINE  14:32:15
    AI Trading Intelligence

    Integration:
    ------------
    Add to dashboard layout:
        app.layout = html.Div([
            create_kymera_header(),
            dbc.Container([
                # ... dashboard content
            ])
        ], className="kymera-dashboard")

    Notes:
    ------
    - Clock updates via callback (requires 'live-clock' ID in layout)
    - Status can be updated dynamically via callback
    - Navbar uses Bootstrap dark theme with custom overrides

    Examples:
    ---------
    >>> # Standard header with all features
    >>> header = create_kymera_header()

    >>> # Header without clock
    >>> header = create_kymera_header(show_clock=False)

    >>> # Header showing offline status
    >>> header = create_kymera_header(system_status="offline")

    >>> # Minimal header (no status or clock)
    >>> header = create_kymera_header(show_clock=False, show_status=False)
    """
    # Build right-side content
    right_content = []

    if show_status:
        right_content.append(
            dbc.Col(
                create_status_indicator(system_status),
                width="auto",
                className="me-3"
            )
        )

    if show_clock:
        right_content.append(
            dbc.Col(
                html.Div(
                    id='live-clock',
                    className="text-white font-monospace",
                    children=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                width="auto"
            )
        )

    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                # Logo on left
                dbc.Col(
                    create_kymera_logo(),
                    width="auto"
                ),
                # Status and clock on right
                dbc.Col(
                    dbc.Row(
                        right_content,
                        align="center",
                        className="g-0"
                    ) if right_content else None,
                    className="ms-auto"
                )
            ], align="center", className="w-100")
        ], fluid=True),
        className="kymera-navbar",
        dark=True,
        sticky="top"
    )


def create_metric_card(
    label: str,
    value: str,
    change: Optional[str] = None,
    change_positive: bool = True
) -> html.Div:
    """
    Create branded metric card for key statistics.

    Parameters:
    -----------
    label : str
        Metric label (e.g., "Total P&L", "Win Rate")
    value : str
        Metric value (e.g., "$1,234.56", "67%")
    change : str, optional
        Change indicator (e.g., "+12.5%", "-3.2%")
    change_positive : bool, default=True
        Whether change is positive (green) or negative (red)

    Returns:
    --------
    html.Div
        Metric card with gradient value and optional change indicator

    Visual Design:
    --------------
    - Glass-morphism background
    - Uppercase label in secondary text color
    - Large value with cyan→purple gradient
    - Color-coded change indicator (green/red)
    - Hover effect with border glow

    Layout:
    -------
    ┌─────────────────┐
    │   TOTAL P&L     │  <- Label (small, uppercase)
    │   $1,234.56     │  <- Value (large, gradient)
    │   +12.5%        │  <- Change (green/red)
    └─────────────────┘

    Examples:
    ---------
    >>> # Profit metric with positive change
    >>> card = create_metric_card("Total P&L", "$1,234.56", "+12.5%", True)

    >>> # Win rate without change
    >>> card = create_metric_card("Win Rate", "67%")

    >>> # Loss metric with negative change
    >>> card = create_metric_card("Total Loss", "$-500.00", "-3.2%", False)
    """
    change_class = "positive" if change_positive else "negative"

    return html.Div([
        html.Div(label, className="kymera-metric-label"),
        html.Div(value, className="kymera-metric-value"),
        html.Div(
            change,
            className=f"kymera-metric-change {change_class}"
        ) if change else None
    ], className="kymera-metric-card")


def create_section_header(title: str, subtitle: Optional[str] = None) -> html.Div:
    """
    Create branded section header with gradient text.

    Parameters:
    -----------
    title : str
        Section title
    subtitle : str, optional
        Optional subtitle/description

    Returns:
    --------
    html.Div
        Section header with gradient effect

    Visual Design:
    --------------
    - Title in cyan→purple gradient
    - Semibold weight, large size
    - Optional muted subtitle below
    - Negative letter-spacing for modern look

    Examples:
    ---------
    >>> # Simple header
    >>> header = create_section_header("Watchlist")

    >>> # Header with subtitle
    >>> header = create_section_header(
    ...     "Active Positions",
    ...     "Real-time P&L tracking"
    ... )
    """
    return html.Div([
        html.H3(title, className="kymera-header"),
        html.P(subtitle, className="text-muted small mb-0") if subtitle else None
    ])


def create_badge(
    text: str,
    variant: str = "primary"
) -> html.Span:
    """
    Create branded badge/tag element.

    Parameters:
    -----------
    text : str
        Badge text
    variant : str, default="primary"
        Badge color variant: "primary", "success", "danger", "warning", "info"

    Returns:
    --------
    html.Span
        Badge element with appropriate styling

    Visual Design:
    --------------
    - Rounded corners
    - Uppercase text
    - Color-coded background and border
    - Small, semibold font

    Examples:
    ---------
    >>> # Primary badge (cyan)
    >>> badge = create_badge("Active", "primary")

    >>> # Success badge (green)
    >>> badge = create_badge("Profit", "success")

    >>> # Danger badge (red)
    >>> badge = create_badge("Risk", "danger")

    >>> # Warning badge (amber)
    >>> badge = create_badge("Alert", "warning")
    """
    return html.Span(
        text,
        className=f"kymera-badge kymera-badge-{variant}"
    )


def create_divider(
    with_glow: bool = False
) -> html.Hr:
    """
    Create themed divider line.

    Parameters:
    -----------
    with_glow : bool, default=False
        Add glow effect to divider

    Returns:
    --------
    html.Hr
        Horizontal divider with optional glow

    Visual Design:
    --------------
    - Subtle border color
    - Optional gradient glow
    - 1px height

    Examples:
    ---------
    >>> # Standard divider
    >>> divider = create_divider()

    >>> # Divider with glow
    >>> divider = create_divider(with_glow=True)
    """
    style = {
        "borderTop": "1px solid var(--kymera-border-subtle)",
        "margin": "var(--kymera-space-md) 0"
    }

    if with_glow:
        style["boxShadow"] = "0 0 10px var(--kymera-primary-glow)"

    return html.Hr(style=style)


def create_loading_spinner(size: str = "md") -> html.Div:
    """
    Create branded loading spinner.

    Parameters:
    -----------
    size : str, default="md"
        Spinner size: "sm", "md", "lg"

    Returns:
    --------
    html.Div
        Animated loading spinner with cyan accent

    Visual Design:
    --------------
    - Circular spinner
    - Cyan top border (rotating)
    - Transparent background
    - Smooth animation

    Examples:
    ---------
    >>> # Medium spinner
    >>> spinner = create_loading_spinner()

    >>> # Small spinner
    >>> spinner = create_loading_spinner("sm")

    >>> # Large spinner
    >>> spinner = create_loading_spinner("lg")
    """
    size_map = {
        "sm": "16px",
        "md": "24px",
        "lg": "32px"
    }

    size_px = size_map.get(size, "24px")

    return html.Div(
        className="kymera-loading",
        style={
            "width": size_px,
            "height": size_px
        }
    )


# Export all public functions
__all__ = [
    'create_kymera_logo',
    'create_status_indicator',
    'create_kymera_header',
    'create_metric_card',
    'create_section_header',
    'create_badge',
    'create_divider',
    'create_loading_spinner'
]
