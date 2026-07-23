---
name: gradlaunch-design
description: The GradLaunch design system and visual direction for the Application Feedback Generator. Use this skill whenever designing, building, restyling, reviewing, or extending ANY GradLaunch interface — the feedback tool, its panels and flags, the marketing site, dashboards, emails, or any new page, screen, or component. Trigger on any mention of GradLaunch layouts, colours, typography, buttons, forms, feedback output, flags, empty states, or "make this look right" / "clean this up" / "design a screen for". Also use when writing HTML, React, or Tailwind for GradLaunch even when the request sounds purely functional ("add a settings page", "build the upload step"), because every surface must inherit the same chrome-and-canvas system. Do not design GradLaunch UI from scratch without reading this first.
---

# GradLaunch Design Direction

## The product this serves

The Application Feedback Generator is a **working surface**, not a shopfront. A student pastes in an application answer, a CV bullet, or a cover letter, and reads back several paragraphs of honest critique — then edits, and reads again. The core use case is a long, slightly uncomfortable editing session.

That single fact governs everything below. The marketing site's job is to sell a promise in three seconds. The tool's job is to disappear so someone can concentrate on hard feedback about their own writing. Design that fights the reading loses, no matter how on-brand it looks.

**The thesis:** the brand lives at the edges; the work happens in the light.

## The governing decision: two-tone

Of the four directions explored in the visual direction document, the system is **Theme 3 — Two-Tone**. This is settled, not open. Build every screen this way:

- A **navy chrome** frame — header, and where needed a footer or left rail — carries full brand weight: logo lockup, product name, navigation, account.
- A **light canvas** inside it carries all the actual work: inputs, generated feedback, flags, editing, reading.

Chrome is where someone remembers whose product this is. Canvas is where they forget they're using a product at all. Themes 1, 2 and 4 and the reasoning behind the choice are in `references/themes.md` — read that only if someone is explicitly reopening the direction, not to soften the rule on a given screen.

### The zone rule

This is the most load-bearing rule in the system. When unsure about any styling decision, ask which zone the element is in.

| | Chrome (navy) | Canvas (light) |
|---|---|---|
| Background | `#1E2A44`, `#2A3854` for nested panels | `#FFFFFF`, `#FAFAFA` for nested panels |
| Text | White, and muted white for secondary | Navy ink, muted slate for secondary |
| Corner radius | **0** — sharp edges throughout | 6px inputs and cards, 8px large panels |
| Type | Space Grotesk for the wordmark and product name | Inter for everything that is read as prose |
| What belongs here | Identity, navigation, account, global state | Every input, every word of feedback, every flag |
| What never belongs | Feedback prose, form fields, flag content | Large navy fills, hero photography, brand messaging |

The contrast in cornering is deliberate and does real work: sharp = brand zone, soft = work zone. It marks the boundary without needing a label.

### The transition

Two-tone systems read as an unfinished skin unless the join between the zones is deliberate. The join is a **hard colour break**: chrome ends at a flat horizontal edge with `box-shadow: 0 1px 0 rgba(0,0,0,0.08)` beneath it, and nothing else. No gradient fade, no rounded bottom corners on the chrome, no decorative divider, no navy tint bleeding into the canvas.

## Palette

Full token set with CSS custom properties in `references/tokens.css` — pull from there rather than retyping hex values.

**Brand**
- `#1E2A44` navy — chrome background, and canvas text
- `#2A3854` navy panel — nested surfaces inside the chrome only
- `#F59E0B` orange — the single accent
- `#3B82F6` bright blue — chrome microcopy and eyebrow labels only

**Canvas neutrals**
- `#FFFFFF` base · `#FAFAFA` panel · `#E5E5E5` hairline · `#5A6478` muted ink

**Feedback semantics** — the tool's whole reason for existing is telling someone what to fix, so severity must be legible at a glance, not decorative:
- `#B3391A` deep rust — must fix
- `#F59E0B` orange — worth improving
- `#3B82F6` blue — context or optional note
- `#157A5B` deep green — what's already working

Green sits outside the marketing palette on purpose. A coaching tool that only ever shows problems trains people to dread opening it; naming strengths in a distinct colour is a product requirement, not a decoration. Keep it to this one green.

### Colour rules

- Orange means two different things depending on zone, and the two must never blur. In the **chrome** it is brand: the CTA pill, the paper-plane mark. In the **canvas** it is diagnostic: a flag that needs attention. Never use orange in the canvas for decoration, dividers, headings, or emphasis — if it appears there, it must mean something.
- Never set body text in orange, and never place orange on navy for anything diagnostic. Orange-on-navy reads decorative; a flag needs to read urgent.
- Severity colour arrives as a **left border plus a small label**, never as a filled background behind the feedback prose. Filled tints hurt reading and turn critique into an alarm panel.
- Blue is the quietest of the accents. If a screen has more than a couple of blue elements, something is being over-signalled.
- No gradients anywhere. Flat colour only, in both zones.

## Typography

Three faces, three jobs, no exceptions:

- **Space Grotesk** — the wordmark, product name, page titles, section headings. Display duty only.
- **Inter** — all body copy, feedback prose, inputs, buttons, help text. Everything that gets read at length.
- **JetBrains Mono** — field labels, flag tags, counters, metadata. Uppercase, ~11px, letter-spacing ~0.08em. This is the small-caps micro-label idiom from the reference; it is a big part of what makes the tool read as precise rather than generic.

Scale (canvas): 28px page title · 20px section heading · 16px body and inputs · 14px secondary · 11px mono labels. Body line-height 1.6.

**Feedback prose is capped at 68–72ch.** This is not a soft preference. Full-width paragraphs of critique are the fastest way to make the tool exhausting, and the split-screen layout gives plenty of room to do it right.

Weight carries emphasis inside prose, not colour and not italics. Emphasis in the hero — the "faster." trick where colour alone does the work — belongs to the marketing site and stays there.

## Shape, space and depth

- **Radius:** 0 in chrome. 6px for inputs, buttons and cards in canvas. 8px for large panels. The generous 16–24px rounding from the landing page hero does not travel into the tool; it belongs to photography, and there is no photography here.
- **The pill exception:** the fully rounded pill button from the landing page CTA is permitted **once per screen, on the primary action only** — "Get feedback", "Save changes". It's the one place the marketing site's voice reaches into the work zone, and it stops being a signal if it's everywhere. Secondary and tertiary buttons take the standard 6px radius.
- **Borders:** 1px hairlines. Structure comes from whitespace and hairlines, not from boxes inside boxes.
- **Shadows:** essentially none. The one permitted shadow is the chrome-to-canvas join. Modals may take a single soft shadow. Cards, inputs, and buttons take none.
- **Spacing:** 4px base unit, 8px rhythm. Be generous — 24–32px between major blocks, 16px within them. Crowding reads as cheap far faster than any colour decision.

## Component patterns

Recipes for the recurring surfaces are in `references/tokens.css` alongside the tokens. The shapes worth holding in mind:

- **Chrome bar** — navy, sharp, fixed height around 56px. Orange paper-plane mark plus letter-spaced "GRADLAUNCH" wordmark on the left, product name in Space Grotesk, navigation and account on the right. It does not scroll away with the canvas content.
- **Split canvas** — input on the left, generated feedback on the right, on a hairline divider. This is the established layout; keep it. Below the mobile breakpoint it stacks input-first.
- **Input panel** — mono labels above each field, hairline-bordered inputs, generous internal padding, the orange pill CTA at the bottom.
- **Feedback item** — 4px left border in the severity colour, mono severity tag, then the critique as plain Inter prose within the character cap. One idea per item.
- **Empty state** — a direction, not a mood. Say what to paste and what will come back. No illustration, no encouragement, no exclamation marks.
- **Loading state** — the feedback panel is the slow surface, so it needs a real answer: skeleton lines matching the shape of the output, or a plain progress line. Never a spinner alone, never a rotating set of motivational messages.

## Voice inside the tool

Copy is design material here, and the tool's voice is the coach's: direct, specific, warm, unhurried. The marketing site is allowed urgency ("let's fix what's holding you back"); the tool has already been paid for and should stop selling.

- Name what's wrong and what to do about it. "No evidence of the decision you made — add one concrete choice and your reasoning" beats "This could be stronger."
- Buttons say what happens: "Get feedback", not "Submit".
- Errors explain and instruct; they don't apologise or go vague.
- Sentence case throughout. No exclamation marks. No emoji, ever, including as flag icons.

## Lean into

- Light canvas, long comfortable reading, generous whitespace
- Hairlines and mono micro-labels as the texture of the interface
- Severity colour used sparingly and always meaningfully
- Navy chrome that makes the product unmistakable in one glance at the top of the screen
- Flat, precise, quietly confident — a well-made instrument

## Avoid

- Feedback prose on any dark background — the single worst failure available in this system
- Rounded chrome, or chrome-navy fills sneaking into the canvas as "section headers"
- Gradients, glassmorphism, glow effects, animated backgrounds
- Purple/violet, sparkle icons, or any of the ambient "AI product" visual vocabulary
- Hero photography, illustrations, or mascots inside the tool
- Orange as decoration in the canvas, or as body text anywhere
- Pills on every button; heavy drop shadows; nested cards
- Centre-aligned paragraphs, full-bleed text columns
- Motion beyond ~150ms functional transitions on hover, focus, and content arrival

## Before calling a screen done

1. Is every word of feedback on a light background, inside the character cap?
2. Is chrome sharp-cornered and canvas soft-cornered, with a hard join between them?
3. Does every appearance of orange in the canvas carry a meaning?
4. Is there exactly one pill on the screen, on the primary action?
5. Are the three faces in their assigned roles — no Space Grotesk in prose, no Inter in mono labels?
6. Does it read as GradLaunch within one second, and become invisible within five?
7. Keyboard focus visible, contrast sufficient, layout holding at mobile width.

## References

- `references/tokens.css` — copy-paste CSS custom properties and base component styles
- `references/themes.md` — the four original directions and why Theme 3 was chosen; read only when the direction itself is being reopened
