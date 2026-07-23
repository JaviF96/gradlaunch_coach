import { useEffect, useRef, useState } from "react";
import type { Rewrite } from "../api.ts";

export function RewriteBlock({ rewrite }: { rewrite: Rewrite }) {
  const [copied, setCopied] = useState(false);
  const resetTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(resetTimer.current), []);

  async function copyRewrite() {
    try {
      await navigator.clipboard.writeText(rewrite.rewritten_text);
      setCopied(true);
      window.clearTimeout(resetTimer.current);
      resetTimer.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access denied — leave the button as-is; the text is
      // still selectable by hand.
    }
  }

  return (
    <div className="flag-rewrite">
      <div className="rewrite-head">
        <span className="gl-label">Suggested rewrite</span>
        <button
          type="button"
          className="gl-btn-copy"
          onClick={copyRewrite}
          aria-live="polite"
        >
          {copied ? "Copied" : "Copy rewrite"}
        </button>
      </div>
      <p className="rewrite-text">{rewrite.rewritten_text}</p>
      <p className="rewrite-reason">{rewrite.reason}</p>
    </div>
  );
}
