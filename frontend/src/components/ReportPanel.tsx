import type { RefObject } from "react";
import type { FinalReport } from "../api.ts";
import type { ReportStatus } from "../App.tsx";
import { Carousel } from "./Carousel.tsx";
import { EmptyState } from "./EmptyState.tsx";
import { ErrorFlag } from "./ErrorFlag.tsx";
import { LoadingSkeleton } from "./LoadingSkeleton.tsx";

interface ReportPanelProps {
  status: ReportStatus;
  report: FinalReport | null;
  errorMessage: string;
  regionRef: RefObject<HTMLDivElement | null>;
}

export function ReportPanel({
  status,
  report,
  errorMessage,
  regionRef,
}: ReportPanelProps) {
  return (
    <section className="gl-panel gl-panel--report" aria-label="Feedback">
      <div id="report" aria-live="polite" tabIndex={-1} ref={regionRef}>
        {status === "idle" && <EmptyState />}
        {status === "loading" && <LoadingSkeleton />}
        {status === "error" && <ErrorFlag message={errorMessage} />}
        {status === "ready" && report && <Carousel report={report} />}
      </div>
    </section>
  );
}
