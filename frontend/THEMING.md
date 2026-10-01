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
| `src/components/AppHeader.tsx` | Top bar for signed-out pages (login, register). |
| `src/components/AppShell.tsx` | Layout for signed-in pages: sidebar with navigation, theme switch and sign out. Becomes a slide-in drawer below 900px. |
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
| `--color-danger` / `--color-danger-bg` | Error text and tinted error backgrounds |
| `--color-danger-solid` / `--color-danger-solid-hover` / `--color-on-danger` | Solid red buttons (sign out on hover, destructive confirms) |
| `--color-warning` / `--color-warning-bg` | "Almost ready" and other heads-up states |
| `--color-success` / `--color-success-bg` | Success messages |
| `--overlay-bg` | Dimmed backdrop behind dialogs and the mobile drawer |

**Form fields:** `--field-bg`, `--field-border`, `--field-border-focus`, `--focus-ring`

**Spacing:** `--space-1` (4px), `-2` (8px), `-3` (12px), `-4` (16px), `-5` (20px), `-6` (24px), `-8` (32px), `-10` (40px)

**Radius:** `--radius-sm` (8px), `--radius-md` (12px), `--radius-lg` (20px), `--radius-full`

**Type:** `--font-sans`, `--text-xs` through `--text-2xl`

**Motion:** `--duration-fast`, `--duration-base`, `--ease`. Motion is turned off for users with "reduce motion" enabled.

## Shared classes

| Class | What it is |
|---|---|
| `.glass` | Frosted panel |
| `.btn` + `.btn-primary` / `.btn-ghost` / `.btn-danger` | Buttons. Add `.btn-block` for full width, `.btn-pill` for rounded ends. |
| `.btn-danger-hover` | Quiet outline button that turns solid red on hover (sign out) |
| `.badge` + `.badge-success` / `-warning` / `-danger` / `-neutral` / `-primary` | Small rounded status labels |
| `.alert` + `.alert-error` / `.alert-success` | Inline status messages |
| `.visually-hidden` | Hidden on screen, still read by screen readers |

## Shared components

| Component | Use for |
|---|---|
| `AppShell` | Wraps every signed-in route (set up in `App.tsx`). Pages render inside it. |
| `PageHeader` | The title and description at the top of each signed-in page. |
| `ConfirmDialog` | "Are you sure?" popups. Built on the native `<dialog>`, so focus trapping and Escape work automatically. |
| `TextField` | Every text input (see below). |

## Icons

Use [React Icons](https://react-icons.github.io/react-icons/), Lucide set only (`react-icons/lu`), so icons share one style. Mark decorative icons `aria-hidden="true"`; an icon-only button needs an `aria-label`.

```tsx
import { LuHistory } from 'react-icons/lu'

<LuHistory aria-hidden="true" />
```

For text inputs, use the `TextField` component (`src/components/TextField.tsx`). It handles the label, hint, error message, accessibility attributes and the password Show/Hide button.
