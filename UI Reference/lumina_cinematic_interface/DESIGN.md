---
name: Lumina Cinematic Interface
colors:
  surface: '#121415'
  surface-dim: '#121415'
  surface-bright: '#38393b'
  surface-container-lowest: '#0d0e10'
  surface-container-low: '#1a1c1d'
  surface-container: '#1e2022'
  surface-container-high: '#282a2c'
  surface-container-highest: '#333537'
  on-surface: '#e2e2e4'
  on-surface-variant: '#bbc9cf'
  inverse-surface: '#e2e2e4'
  inverse-on-surface: '#2f3032'
  outline: '#859398'
  outline-variant: '#3c494e'
  surface-tint: '#3cd7ff'
  primary: '#a8e8ff'
  on-primary: '#003642'
  primary-container: '#00d4ff'
  on-primary-container: '#00586b'
  inverse-primary: '#00677e'
  secondary: '#4bd9e7'
  on-secondary: '#00363b'
  secondary-container: '#03b7c5'
  on-secondary-container: '#004248'
  tertiary: '#d9dfe6'
  on-tertiary: '#2b3136'
  tertiary-container: '#bdc3ca'
  on-tertiary-container: '#4a5156'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b4ebff'
  primary-fixed-dim: '#3cd7ff'
  on-primary-fixed: '#001f27'
  on-primary-fixed-variant: '#004e5f'
  secondary-fixed: '#89f2ff'
  secondary-fixed-dim: '#4bd9e7'
  on-secondary-fixed: '#001f23'
  on-secondary-fixed-variant: '#004f56'
  tertiary-fixed: '#dde3ea'
  tertiary-fixed-dim: '#c1c7ce'
  on-tertiary-fixed: '#161c21'
  on-tertiary-fixed-variant: '#41484d'
  background: '#121415'
  on-background: '#e2e2e4'
  surface-variant: '#333537'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.05em
  mono-ui:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 20px
  margin-desktop: 64px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
This design system is built upon the concept of "Atmospheric Intelligence." It moves away from traditional software patterns toward a cinematic, immersive experience that feels "present" and alive. The target audience seeks a premium, calm, and highly organized AI companion that acts as a digital sanctuary rather than a utility tool.

The visual style is **Cinematic Glassmorphism**. It blends the structural precision of high-end automotive interfaces with the ethereal, layered depth of modern OS aesthetics. The interface relies on light, glow, and varying levels of transparency to communicate hierarchy. Surfaces are not solid; they are windows into a deep, dark environment, utilizing high-density background blurs and micro-interactions that mimic the behavior of light hitting glass.

## Colors
The palette is rooted in an "Obsidian Abyss" (#030405) to ensure maximum contrast for luminous elements. 

- **Primary Accent (#00D4FF):** Used for active states, critical AI signals, and focus indicators. It should be treated as a light source.
- **Secondary Accent (#68F0FF):** A softer tint used for secondary interactions, gradients, and supporting data visualizations.
- **Typography:** Primary text uses a high-value blue-white (#F2F8FF) for maximum legibility against dark backgrounds. Secondary text (#8E98A5) reduces visual noise for metadata and descriptions.
- **Atmospheric Gradients:** Backgrounds should occasionally feature extremely subtle radial gradients of the Primary Accent at 2-5% opacity to simulate ambient lighting from the AI entity.

## Typography
The typography system uses a tiered approach to balance character with technical precision. 

- **Sora** provides a futuristic, geometric personality for headlines and large display moments. 
- **Manrope** is used for body text and long-form memory views, offering a refined and trustworthy reading experience. 
- **Geist** is reserved for small UI labels, technical metadata, and navigation elements, providing a crisp, developer-inspired "pro" feel.

Spaciousness is key. Tracking (letter-spacing) should be slightly increased for labels to maintain legibility against blurred backgrounds, while display type should be tight and impactful.

## Layout & Spacing
The layout follows a **Fluid Floating Grid**. Elements are rarely "locked" to the screen edges; instead, they float as cohesive modules over the background.

- **Desktop:** A 12-column grid with wide 64px margins creates a breathable, gallery-like feel. 
- **The Floating Dock:** A left-aligned vertical navigation bar that sits independently from the main content container.
- **Responsiveness:** On mobile, the dock transitions to a bottom-fixed glass pill. Gutters compress to 16px.
- **Vertical Rhythm:** Spacing is strictly based on 4px increments, with heavy use of 32px (stack-lg) to separate distinct functional areas like the timeline from the action grid.

## Elevation & Depth
Depth is the primary communicator of hierarchy in this design system.

1.  **Level 0 (Background):** Pure #030405. No interaction.
2.  **Level 1 (Sub-surfaces):** Secondary background (#080B0E) used for grouped content or inset areas.
3.  **Level 2 (Floating Glass):** `rgba(255, 255, 255, 0.03)` with a 30px Backdrop Blur. This is the standard for cards and the dock.
4.  **Level 3 (Active/Focus):** Elements gain a 1px inner border `rgba(255, 255, 255, 0.1)` and a soft outer glow using the Primary Accent color at 10% opacity.

**Shadows:** Avoid black shadows. Instead, use "Environmental Shadows"—soft, 40px–60px blurs that are slightly tinted with the Primary Accent color to suggest the element is emitting or reflecting light.

## Shapes
The shape language is "Soft-Tech." It avoids the harshness of sharp corners but maintains a sense of structure through consistent radii.

- **Standard Cards/Containers:** 0.5rem (8px) for a modern, architectural feel.
- **Interactive Pills/Dock:** 2rem (32px) or fully rounded ends to signify "touchability" and fluid motion.
- **Borders:** All borders must be 1px and semi-transparent. Never use solid borders.

## Components
- **Floating Dock:** Vertical pill on the left. Icons use a dual-tone style (Neutral/Accent). Active state is indicated by a glass pill "glow" behind the icon.
- **Action Cards:** Large, glassmorphic surfaces with a 1px border. Use rich, abstract 3D illustrations or mesh gradients in the top-right corner to indicate the card's function.
- **Timeline View:** A vertical thread using a 1px Primary Accent line. Each "Memory" is a glass bubble with high-contrast typography.
- **Buttons:** Primary buttons are subtle glass pills with centered text. On hover, they "energize," increasing border opacity and adding a soft 15px glow of the Primary Accent.
- **Inputs:** Minimalist underlines or subtle glass wells. The cursor is a vertical 2px bar in the Primary Accent color, pulsing slightly to feel "alive."
- **Top Nav:** Only essential status indicators (Mic status, Time). Use monospaced Geist font for numerical data to emphasize precision.