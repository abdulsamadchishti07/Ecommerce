# EvoCart — E-Commerce Color System

Built directly off your logo (navy + cobalt blue). Reusing your existing brand colors instead of picking new ones — consistency between your logo and UI is what makes a brand look intentional instead of assembled from a template.

---

## 1. Primary Color

| Name | Hex | Usage |
|---|---|---|
| **Primary / Cobalt Blue** | `#2454E0` | Main CTAs, primary buttons, active nav links, links, focus rings, price highlights |
| **Primary Dark** | `#1B3FB8` | Hover state for primary buttons |
| **Primary Darker** | `#122C86` | Active/pressed state for primary buttons |

This is pulled straight from the cart icon in your logo. Don't introduce a second "brand blue" — this is it.

## 2. Secondary Color

| Name | Hex | Usage |
|---|---|---|
| **Secondary / Deep Navy** | `#0B1F3A` | Header/footer background, nav bar, secondary buttons, dark UI sections |
| **Navy Light** | `#16345C` | Hover state on navy elements |
| **Navy Muted** | `#3C5578` | Secondary text on dark backgrounds, subtitles |

Also pulled from your logo. Navy + cobalt is your entire brand — everything else on this page is neutral or functional, not "brand."

## 3. Neutral Colors (backgrounds, text, borders)

| Name | Hex | Usage |
|---|---|---|
| **Background** | `#FFFFFF` | Page background |
| **Surface / Card BG** | `#F7F8FA` | Product cards, panels, table stripes |
| **Border Light** | `#E4E7EC` | Card borders, dividers, input borders |
| **Border Medium** | `#CBD1DA` | Stronger borders, disabled input borders |
| **Text Primary** | `#0F172A` | Headings, product titles, body copy |
| **Text Secondary** | `#5B6472` | Descriptions, meta text, timestamps |
| **Text Disabled / Placeholder** | `#9AA3AF` | Placeholder text, disabled labels |

Don't use pure black (`#000000`) for text — it reads harsher and lower quality against white than a near-black like `#0F172A`. This is a small detail but it's the difference between "designed" and "default browser styling."

## 4. Accent / Functional Colors

| Purpose | Hex | Notes |
|---|---|---|
| **CTA / Conversion Accent** | `#FF6A3D` (warm orange) | Use *sparingly* — "Add to Cart," "Buy Now," limited-time banners. This is your one non-blue accent. Orange against navy/blue is a proven high-contrast conversion pairing (complementary color, pulls the eye immediately). |
| **Success** | `#1E9E5A` | Order confirmed, in-stock, payment success |
| **Error / Danger** | `#D8392C` | Out of stock, form errors, failed payment |
| **Warning** | `#E8A93B` | Low stock, pending review, expiring cart/coupon |
| **Info** | `#2A7FD6` | Neutral info banners, "your order is on the way" |

**Why the orange CTA matters:** if "Add to Cart" is the same blue as your nav links, it doesn't stand out and your conversion rate suffers. Primary action buttons need to be visually distinct from the rest of the UI, not just "on-brand." This is not optional — it's the single highest-leverage color decision on the whole page.

---

## 5. UI State Reference (for Django templates / CSS variables)

| Element | Default | Hover | Active/Pressed | Disabled |
|---|---|---|---|---|
| **Primary Button** | `#2454E0` | `#1B3FB8` | `#122C86` | `#CBD1DA` bg / `#9AA3AF` text |
| **CTA Button (Add to Cart)** | `#FF6A3D` | `#E5572C` | `#C7481F` | `#E8C4B5` |
| **Secondary Button (outline)** | border `#2454E0`, text `#2454E0`, bg transparent | bg `#EEF2FF` | bg `#DCE5FF` | border/text `#9AA3AF` |
| **Link** | `#2454E0` | underline + `#1B3FB8` | `#122C86` | `#9AA3AF` |
| **Input Border** | `#CBD1DA` | — | focus: `#2454E0` (2px ring) | `#E4E7EC` bg `#F7F8FA` |
| **Success Alert** | bg `#E6F7EC`, text `#1E9E5A`, border `#1E9E5A` | — | — | — |
| **Error Alert** | bg `#FCEAE8`, text `#D8392C`, border `#D8392C` | — | — | — |
| **Warning Alert** | bg `#FDF3E1`, text `#8A5F1C`, border `#E8A93B` | — | — | — |
| **Info Alert** | bg `#E9F2FB`, text `#2A7FD6`, border `#2A7FD6` | — | — | — |

---

## 6. CSS Custom Properties (drop into your Django base template)

```css
:root {
  /* Primary */
  --color-primary: #2454E0;
  --color-primary-hover: #1B3FB8;
  --color-primary-active: #122C86;

  /* Secondary */
  --color-navy: #0B1F3A;
  --color-navy-hover: #16345C;
  --color-navy-muted: #3C5578;

  /* Neutrals */
  --color-bg: #FFFFFF;
  --color-surface: #F7F8FA;
  --color-border-light: #E4E7EC;
  --color-border-medium: #CBD1DA;
  --color-text-primary: #0F172A;
  --color-text-secondary: #5B6472;
  --color-text-disabled: #9AA3AF;

  /* CTA / Conversion */
  --color-cta: #FF6A3D;
  --color-cta-hover: #E5572C;
  --color-cta-active: #C7481F;

  /* Functional */
  --color-success: #1E9E5A;
  --color-error: #D8392C;
  --color-warning: #E8A93B;
  --color-info: #2A7FD6;

  /* Alert backgrounds */
  --bg-success: #E6F7EC;
  --bg-error: #FCEAE8;
  --bg-warning: #FDF3E1;
  --bg-info: #E9F2FB;
}
```

---

## 7. Rules to actually follow (not decoration)

1. **Orange is scarce.** If you put it on more than one element per screen (e.g., the CTA button *and* a promo banner *and* a badge), it stops meaning "act now" and just becomes noise. Pick one primary action per screen and reserve orange for it.
2. **Navy is structural, not decorative.** Use it for nav/header/footer — large fixed regions — not scattered across cards or badges.
3. **Don't invent new blues.** If you're tempted to add a "lighter accent blue" for some component, derive it from `--color-primary` with opacity/tint instead of picking a new hex. Scope creep in color palettes is how projects end up looking inconsistent.
4. **Contrast check your text colors** — `#0F172A` on white and white on `#0B1F3A` both pass WCAG AA. If you deviate from these pairs, run it through a contrast checker before shipping, not after.

This is a 4-color system (navy, blue, orange, neutrals) plus 4 functional colors. That's it — resist the urge to add more "just in case." A disciplined palette is what makes a project look like a product, not a school assignment.
