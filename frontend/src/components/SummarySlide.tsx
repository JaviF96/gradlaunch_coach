import type { ContextBrief } from "../api.ts";

export function SummarySlide({ context }: { context: ContextBrief }) {
  return (
    <article className="gl-flag gl-flag--note stagger">
      <span className="gl-flag-tag">Question brief</span>
      <p className="summary-role">{context.role_focus}</p>
      <p>{context.question_intent}</p>
      <span className="gl-label summary-needs-label">
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
