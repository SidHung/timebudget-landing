# Focus page visual brief

This brief covers the temporary visual concepts added to `focus.html`. The page must remain understandable while these placeholders are present; final artwork should clarify the same story rather than introduce a new one.

## Shared visual direction

- Match the existing TimeBudget language: simple product UI, rounded geometry, black line work, blue and teal accents, pale blue surfaces, and restrained shadows.
- Communicate time trade-offs rather than generic productivity or speed.
- Do not portray a changed plan as failure. The emotional tone should be calm, capable, and intentional.
- Avoid dense calendar screens, red warning states, decorative characters, or arrows whose origin and destination are unclear.
- Do not bake interface copy into raster images. Text, task names, times, and status labels must remain editable in Figma and implementable as HTML.
- Supply icons or illustrative line work as SVG. If raster texture is essential, also provide a 2x PNG export with a transparent background.

## Position A: extended problem section

**Code marker:** `data-visual-placeholder="scenario-unexpected"`, `scenario-overrun`, and `scenario-ahead`

**Current placeholder:** three small inline SVG icons inside the scenario cards.

**Purpose:** make the three reasons for rescheduling distinguishable before the reader studies the text.

### A1 — Unexpected work

- Show a planned day receiving a new item.
- Recommended symbol: calendar block with a clearly attached plus sign.
- The plus sign must mean “new work added,” not “create an event.”

### A2 — Time overrun

- Show an estimate extending beyond its original boundary.
- Recommended symbol: clock with an extending arc, progress line, or time block crossing a marker.
- Avoid a stopwatch or racing metaphor; the issue is changed capacity, not working faster.

### A3 — Finish early

- Show available capacity opening up and the next valuable task moving forward.
- Recommended symbol: an empty time block followed by a task moving into it.
- Avoid an upward financial chart; it can incorrectly imply performance analytics.

### Layout and delivery

- Icon container in the current desktop layout: 52 × 52 px.
- SVG artwork safe area: approximately 34 × 34 px.
- Use one consistent stroke weight and corner treatment for all three icons.
- Provide normal and dark-background-safe SVG versions only if the icon colors cannot be tokenized.

## Position B: flexible rescheduling feature card

**Code marker:** `data-visual-placeholder="flexible-rescheduling-demo"`

**Current placeholder:** a coded prototype showing `Before → Urgent bug → Rebalanced`. Treat its information hierarchy as the required behavior, not as final visual polish.

**Purpose:** let a reader understand within three seconds that a new task causes an explicit trade-off. TimeBudget protects fixed and important work, then moves the work that no longer fits.

### Required story

1. Before: the day has 6 usable hours and three planned tasks.
2. Change: an urgent two-hour bug appears.
3. Rebalanced: the client call remains fixed, the release blocker remains protected, the urgent bug is added, and the launch post moves to tomorrow.
4. The final state remains within the six-hour capacity. Do not imply that all eight hours were squeezed into the original plan.

### Required visual states

- `Fixed`: neutral gray plus a lock or fixed-point cue.
- `Protected`: TimeBudget blue; visually persistent between states.
- `Added`: warm amber used only for the incoming change.
- `Moved`: muted treatment plus a visible destination such as `Tomorrow →`.
- Use motion arrows only where they connect a task to its new destination. A generic refresh icon is not enough.

### Preferred composition

- Primary direction: stacked Before, Change, and Rebalanced states inside the existing middle feature card.
- Desktop content width: approximately 330–340 px.
- Mobile: preserve the same vertical reading order; do not require horizontal scrolling.
- Keep text legible at the current card scale. If a task status needs a legend to be understood, simplify the status instead.

### Optional interaction or motion

- A 500–700 ms transition may move `Launch post` to `Tomorrow` and insert `Urgent bug`.
- The completed state must remain visible without hover or interaction.
- Provide a static final frame for reduced-motion users.
- Motion is optional and must not block implementation of the static card.

### Designer deliverables

- Figma component for the full middle card at desktop and mobile widths.
- Separate variants for Before and Rebalanced states.
- Status tokens and annotations for Fixed, Protected, Added, and Moved.
- SVG icons and arrows, if they differ from the coded placeholders.
- A short note describing which visual elements are decorative and which require accessible text.

## Review checklist

- A first-time reader can explain what changed and which task moved.
- All three problem scenarios remain visually distinct without reading their headings.
- Color is not the only signal for task status.
- No task silently disappears between Before and Rebalanced.
- Desktop at 1280 px and mobile at 390 px retain a clear reading order.
- Final artwork continues to support the page copy: plans adapt to capacity instead of overflowing the day.
