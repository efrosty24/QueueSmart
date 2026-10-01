# Theming

QueueSmart uses one set of CSS variables (design tokens) for every color, glass effect, spacing value and font size. Light, dark and system modes all come from the same tokens, so components never need to know which mode is active.

## Files

| File | What it holds |
|---|---|
| `src/theme/tokens.css` | All tokens. Light values on `:root`, dark values on `:root[data-theme='dark']`. |
| `src/theme/global.css` | Base page styles and shared classes: `.glass`, `.btn`, `.alert`, `.visually-hidden`. |
| `src/theme/theme.ts` | Reads/saves the user's choice and applies it to `<html data-theme>`. |
| `src/theme/ThemeProvider.tsx` | React context. Exposes `useTheme()`. |
| `src/components/ThemeToggle.tsx` | The Light / System / Dark switch. |
| `src/components/AppHeader.tsx` | Top bar with the brand and theme switch. Use it on every page; pass extra buttons through `actions`. |
| `index.html` | Small inline script that applies the saved theme before first paint, so there's no flash. |

## Rules

1. **Use tokens, never raw colors.** Write `color: var(--color-text-muted)`, not `color: #475569`. Raw hex values belong only in `tokens.css`.
2. **New token? Add it to both blocks** in `tokens.css` (light and dark), then list it below.
3. **Panels use `.glass`.** Don't rebuild the frosted effect per component.
4. **Spacing uses the 4px scale** (`--space-*`). Avoid one-off pixel values.

## Light / dark / system

- The user's choice is saved in `localStorage` under `queuesmart-theme` (`light`, `dark` or `system`). Default is `system`.
- `system` follows the OS setting and updates live when it changes.
- The resolved mode is set as `data-theme="light"` or `data-theme="dark"` on `<html>`. Style mode-specific things through tokens, not by checking `data-theme` in components.

Reading or changing it in React:

```tsx
import { useTheme } from '../theme/ThemeProvider'

const { preference, resolvedTheme, setPreference } = useTheme()
setPreference('dark')
```

## Glass (frosted look)

`.glass` gives a translucent, blurred panel with a light border and soft shadow:

```tsx
<section className="glass">…</section>
```

It's built from these tokens, so tune the look here instead of in components:

| Token | Purpose |
|---|---|
| `--glass-bg` | Panel fill (translucent) |
| `--glass-bg-strong` | More opaque fill, for selected states and browsers without blur |
| `--glass-border` | Thin edge around the panel |
| `--glass-highlight` | Inner top highlight |
| `--glass-blur` | Blur amount (default `20px`) |
| `--glass-saturate` | Color boost behind the panel |
| `--glass-shadow` | Drop shadow |

Glass only looks frosted when there's something colorful behind it. The page background in `global.css` draws soft color blobs (`--color-bg-blob-1..3`) for that.

## Token reference

**Color**

| Token | Use for |
|---|---|
| `--color-primary` / `--color-primary-hover` | Main actions, links, brand mark |
| `--color-on-primary` | Text on top of primary |
| `--color-accent` | Secondary highlight |
| `--color-text` | Body text |
| `--color-text-muted` | Secondary text, hints |
| `--color-text-subtle` | Placeholders |
| `--color-bg` | Page background |
| `--color-danger` / `--color-danger-bg` | Errors |
| `--color-success` / `--color-success-bg` | Success messages |

**Form fields:** `--field-bg`, `--field-border`, `--field-border-focus`, `--focus-ring`

**Overlay:** `--scrim` — backdrop behind a modal dialog (see `ServiceFormDialog.tsx` for an example)

**Spacing:** `--space-1` (4px), `-2` (8px), `-3` (12px), `-4` (16px), `-5` (20px), `-6` (24px), `-8` (32px), `-10` (40px)

**Radius:** `--radius-sm` (8px), `--radius-md` (12px), `--radius-lg` (20px), `--radius-full`

**Type:** `--font-sans`, `--text-xs` through `--text-2xl`

**Motion:** `--duration-fast`, `--duration-base`, `--ease`. Motion is turned off for users with "reduce motion" enabled.

## Shared classes

| Class | What it is |
|---|---|
| `.glass` | Frosted panel |
| `.btn` + `.btn-primary` / `.btn-ghost` / `.btn-danger` | Buttons (add `.btn-block` for full width) |
| `.alert` + `.alert-error` / `.alert-success` | Inline status messages |
| `.dialog-scrim` + `.dialog` | Modal dialog (backdrop + centered glass panel) — see `ConfirmDialog.tsx` and `ServiceFormDialog.tsx` |
| `.visually-hidden` | Hidden on screen, still read by screen readers |

For text inputs, use the `TextField` component (`src/components/TextField.tsx`). It handles the label, hint, error message, accessibility attributes and the password Show/Hide button. For multi-line text use `TextArea`, and for a fixed set of choices use `SelectField` — both live alongside `TextField` and share its stylesheet, so all three always look consistent.
