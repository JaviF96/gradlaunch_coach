import { useState, type FormEvent } from "react";
import { Field } from "./Field.tsx";

interface InputPanelProps {
  busy: boolean;
  onSubmit: (
    jobDescription: string,
    question: string,
    draftAnswer: string,
  ) => void;
}

export function InputPanel({ busy, onSubmit }: InputPanelProps) {
  const [jobDescription, setJobDescription] = useState("");
  const [question, setQuestion] = useState("");
  const [draftAnswer, setDraftAnswer] = useState("");

  const isReady = jobDescription.trim() !== "" && question.trim() !== "" && draftAnswer.trim() !== "";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(jobDescription, question, draftAnswer);
  }

  return (
    <section className="gl-panel gl-panel--entry" aria-label="Your application">
      <form id="analyze-form" onSubmit={handleSubmit}>
        <Field
          id="job-description"
          label="Job description"
          placeholder="Paste the job description here"
          maxLength={8000}
          rows={6}
          value={jobDescription}
          onChange={setJobDescription}
          fill="base"
        />
        <Field
          id="question"
          label="Question"
          placeholder="e.g. Describe a project you're proud of"
          maxLength={1000}
          rows={2}
          value={question}
          onChange={setQuestion}
          short
        />
        <Field
          id="draft-answer"
          label="Your draft answer"
          placeholder="Paste your draft answer here"
          maxLength={6000}
          rows={8}
          value={draftAnswer}
          onChange={setDraftAnswer}
          fill="large"
        />
        <div className="form-actions">
          <button type="submit" className="gl-btn-primary" disabled={busy || !isReady}>
            Get feedback
          </button>
        </div>
      </form>
    </section>
  );
}
