import { useCallback, useRef, useState } from "react";
import { analyze, type FinalReport } from "./api.ts";
import { ChromeBar } from "./components/ChromeBar.tsx";
import { InputPanel } from "./components/InputPanel.tsx";
import { ReportPanel } from "./components/ReportPanel.tsx";

export type ReportStatus = "idle" | "loading" | "error" | "ready";

export default function App() {
  const [status, setStatus] = useState<ReportStatus>("idle");
  const [report, setReport] = useState<FinalReport | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const reportRegionRef = useRef<HTMLDivElement>(null);

  const handleSubmit = useCallback(
    async (jobDescription: string, question: string, draftAnswer: string) => {
      setReport(null);
      setStatus("loading");

      try {
        const result = await analyze({
          job_description: jobDescription,
          question: question,
          draft_answer: draftAnswer,
        });
        setReport(result);
        setStatus("ready");
        reportRegionRef.current?.focus();
      } catch (error) {
        console.error("Analyze request failed:", error);
        setErrorMessage(
          error instanceof TypeError
            ? "The feedback service couldn't be reached. Check the backend is running, then try again."
            : error instanceof Error
              ? error.message
              : String(error),
        );
        setStatus("error");
      }
    },
    [],
  );

  return (
    <>
      <ChromeBar />
      <main className="gl-canvas">
        <div className="gl-split">
          <InputPanel busy={status === "loading"} onSubmit={handleSubmit} />
          <ReportPanel
            status={status}
            report={report}
            errorMessage={errorMessage}
            regionRef={reportRegionRef}
          />
        </div>
      </main>
    </>
  );
}
