# Artwork Local Studio — UI specification 0.2

Skill: ui-ux-pro-max. Verified product search: Photo Editor & Filters (Minimalism & Swiss Style + dark editor surfaces). The design-system search returned a marketing-page layout which does not fit this workspace; it was rejected. The workspace layout below is explicit product guidance tailored to the user's requirements.

- Main work area: source/result side by side; dark neutral checker canvas, bright white controls.
- Right: persistent full-height Queue with visible current progress, selection and actions grouped by purpose.
- Bottom: output controls, text constraints and destination. No narrow form stack.
- Browser selector: image library left, stationary selection/rotation toolbar, aspect-correct central canvas, output controls at top right.
- Primary forest green #1F6B3A, hover #17532F, ink #153623, muted #3F594A, background #F5FBF7, surface white, borders #CCDFD2. User requested this palette for version 0.2.1.
- Explicit light QApplication palette and light dialog/tab/dropdown/menu surfaces prevent Windows dark mode from applying unreadable dark gray backgrounds.
- Four corner handles rotate the source around its center. Keep the center fixed and retain manual pan/zoom; constrain fitted images to the viewport so all corners stay visible. Shift snaps to 15°; numeric angle controls remain available.
- Font: local Segoe UI, no network font dependency. Titles 24–28px, body 13–14px, section captions 11–12px.
- Grid: 8px rhythm, 16/20px card insets, 12px corner radius, restrained borders. No decorative animation.
- Icons: consistent stroke SVG, 18–20px, accessible text/tooltips. App mark: an A in a crop frame with a lifted layer and cyan accent.
- Minimum desktop QA: 1280×800 and 1920×1080; controls remain legible with Windows scaling.
- Explicit minimum control heights avoid compressed dropdowns seen in the previous version.
- Canvas backing pixels are resized to actual viewport size and devicePixelRatio; one uniform scale preserves image proportions.
- Native/web rotation previews must match the pixel transformation sent to inference.
- Pointer and keyboard support, visible focus, inline loading state, disabled actions while loading/sending, manual reload fallback when permission cannot be granted automatically.
