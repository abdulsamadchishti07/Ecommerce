# MyStore — Colour Scheme

## Theme: Dark Cosmic / Glassmorphism

Inspired by deep-space gradients with vibrant indigo/violet accents. Designed for high contrast, accessibility, and a premium feel on dark backgrounds.

---

## Background

| Role | Value | Usage |
|------|-------|-------|
| Gradient start | `#0f0c29` | Top-left — near-black deep indigo |
| Gradient mid | `#302b63` | Centre — rich dark purple |
| Gradient end | `#24243e` | Bottom-right — dark navy |

```css
background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
```

---

## Primary Accent (Indigo)

| Role | Hex | Tailwind equiv |
|------|-----|----------------|
| Primary | `#6366f1` | `indigo-500` |
| Hover / lighter | `#818cf8` | `indigo-400` |
| CTA gradient start | `#6366f1` | `indigo-500` |

---

## Secondary Accent (Violet)

| Role | Hex | Tailwind equiv |
|------|-----|----------------|
| Secondary | `#8b5cf6` | `violet-500` |
| CTA gradient end | `#8b5cf6` | `violet-500` |

### CTA Button Gradient
```css
background: linear-gradient(135deg, #6366f1, #8b5cf6);
```

---

## Glassmorphism Card

| Property | Value |
|----------|-------|
| Background | `rgba(255, 255, 255, 0.05)` |
| Border | `1px solid rgba(255, 255, 255, 0.10)` |
| Backdrop blur | `blur(20px)` |
| Box shadow | `0 25px 50px rgba(0, 0, 0, 0.40)` |
| Border radius | `1rem` (16px) / `1.5rem` (24px) for cards |

---

## Input Fields

| State | Background | Border |
|-------|-----------|--------|
| Default | `rgba(255,255,255,0.07)` | `rgba(255,255,255,0.12)` |
| Focus | `rgba(255,255,255,0.10)` | `rgba(99,102,241,0.60)` |
| Focus ring | — | `0 0 0 3px rgba(99,102,241,0.15)` |

---

## Typography (Text on Dark)

| Role | Colour | Tailwind |
|------|--------|---------|
| Headings / primary | `#ffffff` | `text-white` |
| Body / secondary | `rgba(255,255,255,0.60)` | `text-white/60` |
| Muted / placeholder | `rgba(255,255,255,0.30)` | `text-white/30` |
| Very subtle | `rgba(255,255,255,0.20)` | `text-white/20` |
| Links / accent | `#a5b4fc` (indigo-300) | `text-indigo-300` |
| Error | `#f87171` (red-400) | `text-red-400` |
| Success | `#4ade80` (green-400) | `text-green-400` |

---

## Ambient Orbs (Decorative)

Soft radial glows placed in corners to add depth.

| Orb | Colour | Blur | Opacity |
|-----|--------|------|---------|
| 1 | `#6366f1` | `80px` | `0.15` |
| 2 | `#8b5cf6` | `80px` | `0.15` |

```css
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
  animation: drift 8s ease-in-out infinite alternate;
}
```

---

## Password Strength Colours

| Level | Colour | Meaning |
|-------|--------|---------|
| Weak (1/4) | `#ef4444` | Too short |
| Fair (2/4) | `#f59e0b` | Needs uppercase or number |
| Good (3/4) | `#22c55e` | Strong |
| Strong (4/4) | `#22c55e` | Has special character |

---

## Google Sign-In Button

Always white background with dark text — Google brand requirement regardless of site theme.

---

## Typography

Font: `Inter` (Google Fonts) — weights 300/400/500/600/700

| Weight | Usage |
|--------|-------|
| 300 | Large decorative text |
| 400 | Body, inputs |
| 500 | Buttons, labels |
| 600 | Headings, card titles |
| 700 | Brand name |

---

## Tailwind Production Config

```css
:root {
  --color-bg-start:     #0f0c29;
  --color-bg-mid:       #302b63;
  --color-bg-end:       #24243e;
  --color-primary:      #6366f1;
  --color-secondary:    #8b5cf6;
  --color-accent-lt:    #818cf8;
  --color-glass-bg:     rgba(255,255,255,0.05);
  --color-glass-border: rgba(255,255,255,0.10);
}
```
