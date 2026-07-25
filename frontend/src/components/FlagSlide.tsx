import type { Flag, Rewrite } from "../api.ts";
import { dimensionLabel } from "../dimensions.ts";
import { RewriteBlock } from "./RewriteBlock.tsx";

interface FlagSlideProps {
  flag: Flag;
  rewrites: Rewrite[];
  slideIndex: number;
  totalFlags: number;
}

export function FlagSlide({
  flag,
  rewrites,
  slideIndex,
  totalFlags,
}: FlagSlideProps) {
  
  const rewrite = rewrites.find((r) => r.flag_id === flag.id);

  return (
    <article className="gl-flag gl-flag--attention stagger">
      <div className="flag-head">
        <span className="gl-flag-tag">{dimensionLabel(flag.dimension)}</span>
        <span className="flag-meta">
          Flag {slideIndex} of {totalFlags}
        </span>
      </div>
      <blockquote className="flag-quote">{flag.quoted_text}</blockquote>
      <p className="flag-reason">{flag.reason}</p>
      {rewrite && <RewriteBlock rewrite={rewrite} />}
    </article>
  );
}
