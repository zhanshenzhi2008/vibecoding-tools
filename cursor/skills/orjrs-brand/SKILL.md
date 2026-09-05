---
name: orjrs-brand
description: >-
  Applies the orjrs personal brand mark: lonely √3 (孤独的根号3). Use for
  favicons, headers, login branding, scaffolding personal orjrs/sqrt3lab
  projects, or when the user mentions orjrs brand, √3 logo, sqrt3lab,
  Solitary √3, lonely √3, personal project logo, or needs to copy the
  canonical logo SVG/PNG into a new repo.
---

# orjrs personal brand (lonely √3)

## Meaning

| | |
|--|--|
| Chinese | 孤独的根号3 |
| English on mark | **lonely √3** |
| Owner | orjrs (off-glyph: skill name, `com.orjrs`, git user) |

## What’s on the mark

| Element | Placement | Rule |
|---------|-----------|------|
| **lonely** | Top center caption, **above** vinculum | always **lowercase**; horizontal; never overlaps √3 |
| **√3** | Center hero below caption | large white radical + serif `3` |
| Bottom text | **none** | No `orjrs` / `Smart L` / product names on the icon |

Layout: stack reads *lonely* then *√3*. No corner sticker, no tilt.

## Brand layers

| Layer | Content | Reuse |
|-------|---------|--------|
| **Personal mark** | `lonely` + √3 | **Same file on every personal project** |
| **Product wordmark** | e.g. CogniForge | Text beside the mark only |

## Canonical assets (copy these)

Directory: `~/.cursor/skills/orjrs-brand/assets/`

| File | Use |
|------|-----|
| `logo.svg` / `orjrs-mark.svg` | **Source of truth** (identical) |
| `logo-hd.png` / `orjrs-mark-2048.png` | **2048×2048 HD** master |
| `orjrs-mark-1024.png` | 1024×1024 |
| `orjrs-mark.png` / `icon-512.png` | 512×512 |
| `icon-192.png` | PWA |
| `apple-touch-icon.png` | 180×180 |
| `favicon.png` / `favicon-32.png` / `favicon-16.png` | Favicons |

### Copy into a new project

```bash
SKILL="$HOME/.cursor/skills/orjrs-brand/assets"
PROJ_PUBLIC="/path/to/your-project/public"   # or static/
mkdir -p "$PROJ_PUBLIC"
cp "$SKILL/logo.svg" "$PROJ_PUBLIC/favicon.svg"
cp "$SKILL/favicon-16.png" "$SKILL/favicon-32.png" "$SKILL/favicon.png" \
   "$SKILL/apple-touch-icon.png" "$SKILL/icon-192.png" "$SKILL/icon-512.png" \
   "$PROJ_PUBLIC/"
# optional HD archive in repo docs/brand/
cp "$SKILL/logo-hd.png" "$SKILL/logo.svg" "$PROJ_PUBLIC/"
```

Do **not** redesign per project. Only change the product wordmark text beside the mark.

## Setup (Nuxt head)

```ts
link: [
  { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
  { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32.png' },
  { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16.png' },
  { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
]
```

Header: `[mark 36px] + ProductName`  
Login mark: ~80px.

## Colors — 黛青水墨

| Stop | Hex | Feel |
|------|-----|------|
| 远山青 | `#3d5c5a` | distant mountain |
| 黛青 | `#243a42` | dai blue-green |
| 玄青 | `#121c24` | deep night |
| 浓墨 | `#06090d` | ink black |
| mist | `#8fa8a4` radial | 烟雨 |
| Glyph / lonely | `#f2f5f4` / `#e8eef0` | 月白 |

## Do / Don’t

**Do:** reuse these assets; keep empty space under √3.

**Don’t:** invent a new personal logo per project; put product names on the tile; purple glow / letter-C AI marks.

---

## SVG source (copy-paste)

Same as `assets/logo.svg`. Paste into `{project}/public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="lonely square root of 3">
  <!--
    orjrs personal mark — 孤独的根号3 / lonely √3
    Layout: lonely caption above vinculum; √3 hero below
  -->
  <defs>
    <linearGradient id="inkWash" x1="8" y1="2" x2="56" y2="62" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#3d5c5a"/>
      <stop offset="0.35" stop-color="#243a42"/>
      <stop offset="0.7" stop-color="#121c24"/>
      <stop offset="1" stop-color="#06090d"/>
    </linearGradient>
    <radialGradient id="mist" cx="28%" cy="22%" r="65%">
      <stop offset="0" stop-color="#8fa8a4" stop-opacity="0.22"/>
      <stop offset="0.55" stop-color="#4a6a68" stop-opacity="0.06"/>
      <stop offset="1" stop-color="#06090d" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="64" height="64" rx="14" fill="url(#inkWash)"/>
  <rect width="64" height="64" rx="14" fill="url(#mist)"/>

  <text
    x="32"
    y="14"
    text-anchor="middle"
    font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace"
    font-size="9"
    font-weight="700"
    letter-spacing="0.14em"
    fill="#e8eef0"
  >lonely</text>

  <g fill="none" stroke="#f2f5f4" stroke-linecap="round" stroke-linejoin="round">
    <path stroke-width="3.2" d="M14 48 H21 L31 22"/>
    <path stroke-width="3" d="M31 22 H54"/>
  </g>
  <text
    x="43"
    y="47"
    text-anchor="middle"
    font-family="Georgia, 'Source Serif 4', 'Times New Roman', serif"
    font-size="22"
    font-weight="700"
    fill="#f2f5f4"
  >3</text>
</svg>
```
