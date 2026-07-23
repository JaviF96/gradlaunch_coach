# The four directions, and why Theme 3

Read this only when the visual direction itself is being reopened. Do not read it looking for permission to bend the zone rule on a particular screen — the answer there is always the rule in SKILL.md.

## The tension being resolved

Two references drove the exploration. Reference A is a light, functional feedback-tool layout — its job is to disappear into sustained reading and editing. Reference B is the GradLaunch landing page hero — navy, orange, bold rounded type, student photography — and its job is to sell an emotional promise in three seconds.

They are not two aesthetic options for the same screen. They are doing different jobs. The question each theme answers differently: **how much of B survives the trip into A?**

## The four

**1 — Brand Immersion.** Full navy/orange identity carried into the tool floor to ceiling; both panels sit on navy. Wins: zero ambiguity about whose product this is, strongest emotional carryover. Costs: dark backgrounds fatigue the eye over the tool's core use case, and orange-on-navy flags read decorative rather than diagnostic, softening the urgency a flag needs.

**2 — Light Functional, Brand Accents.** Reference A unchanged; the brand appears only as accent colour. Wins: cheapest to build, best reading comfort, safest way to ship fast. Costs: least distinctive — reads as a generic SaaS tool with brand colours added afterwards.

**3 — Two-Tone System.** Navy chrome frame carrying full brand weight, wrapped around a light canvas where reading and editing happen. Wins: real estate for both aesthetics without either dominating; the pattern Linear and Notion use. Costs: needs a deliberate transition — a hard edge, a shadow, a colour break — or it reads as an unfinished skin. Slightly more component work than Theme 2.

**4 — Warm Neutral Bridge.** One softened palette for site and tool alike — warm cream base, muted slate instead of navy. Wins: a single genuinely reusable system, most forgiving to extend consistently. Costs: the boldest tonal step away from the current hero; safest and most cohesive, but least dramatic.

## Why 3

The brief asked for a clean UI for a tool whose central activity is reading several paragraphs of critique and then editing. That rules out Theme 1 on its own terms — the document's own cost analysis flags dark backgrounds against exactly this use case.

Between the remaining three, Theme 2 buys reading comfort at the price of the product looking like anyone's. Theme 4 solves a problem GradLaunch doesn't have yet (site/tool palette drift) by discarding the navy the brand is currently built on. Theme 3 gives the light working canvas the tool needs while keeping the landing page's navy and orange doing real work at the frame — and the "unfinished skin" risk is a solvable execution problem, addressed by the explicit transition rule in SKILL.md.

Theme 3 also degrades gracefully. If the chrome is ever stripped back, what remains is Theme 2 — still coherent, still shippable.

## If the direction is re-pointed

The change is contained. Rewrite the zone-rule table, the transition rule, and the radius section in SKILL.md, and swap the chrome variables in `tokens.css`. These stay true in every direction and shouldn't be touched:

- Feedback prose lives on a light background, capped at 68–72ch
- Severity colour arrives as a left border and a mono tag, never a filled tint
- Space Grotesk display / Inter body / JetBrains Mono labels, in fixed roles
- Orange means one thing per zone and never decorates
- No gradients, no ambient "AI product" visual vocabulary, no emoji
