# Smell Report — Vortex Dashboard

## Strong Smells

### 1. Generic Tech Hue (CRITICAL)
Purple (#8b5cf6, #7c6df0, #6366f1) hardcoded in every JSX inline style across Overview.jsx, DashboardViews.jsx, and Modules.jsx. The CSS redesign to amber was completely bypassed by inline styles.

**Files**: Overview.jsx, DashboardViews.jsx, Modules.jsx
**Severity**: Strong

### 2. Glow Shadows Everywhere (STRONG)
Every stat card icon has `boxShadow: '0 0 15px rgba(139,92,246,0.2)'`. This is the "ambient glow" AI reflex applied to icons that don't need it.

**Files**: Overview.jsx (stat card icons)
**Severity**: Strong

### 3. Uniform Bento Grid (STRONG)
All overview cards have identical visual weight in a 4-column grid. No hierarchy, no leading element. Every card is the same size with the same border treatment.

**Files**: Overview.jsx, DashboardViews.jsx
**Severity**: Strong

### 4. Stat Monument (MODERATE)
Stat cards are oversized number clusters: big number + label + trend arrow. Five identical cards in a row with no differentiation.

**Files**: Overview.jsx, DashboardViews.jsx
**Severity**: Moderate

### 5. Feature Tile Pattern in Module Grid (MODERATE)
Module cards are all identical: icon, name, category, description, toggle, settings button. Every card has the same height and layout.

**Files**: Modules.jsx
**Severity**: Moderate

### 6. Default Color Assignment (MODERATE)
Chart colors, donut segments, and event icons all default to the same purple family. No color strategy — just the brand color everywhere.

**Files**: Overview.jsx, DashboardViews.jsx
**Severity**: Moderate

## Faint Smells

### 7. Icon Backgrounds
Every stat icon sits in a rounded-square background with 10% opacity color fill. Same treatment for every icon, no variation.

### 8. Leaderboard Bar Colors
All leaderboard progress bars use the same purple (#8b5cf6) regardless of rank.

### 9. Premium Card Checkmarks
Premium feature checkmarks all use #8b5cf6 — same color as the brand, no semantic meaning.
