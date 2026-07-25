import type { ContextBrief } from "../api.ts";

/* Model output arrives as lowercase fragments — render them as sentences. */
function asSentence(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  const capitalised = trimmed[0].toUpperCase() + trimmed.slice(1);
  return /[.!?:…]$/.test(capitalised) ? capitalised : `${capitalised}.`;
}

export function SummarySlide({ context }: { context: ContextBrief }) {
  return (
    <article className="gl-flag gl-flag--note stagger">
      <span className="gl-flag-tag">What this question entails</span>
      <p>{asSentence(context.role_focus)}</p>
      <p>{asSentence(context.question_intent)}</p>
      <span className="gl-flag-tag summary-needs-label">
        A strong answer needs
      </span>
      <ul className="summary-needs">
        {context.what_strong_answer_needs.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </article>
  );
}
