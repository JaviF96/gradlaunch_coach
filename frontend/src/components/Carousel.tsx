import { useEffect, useState } from "react";
import type { FinalReport } from "../api.ts";
import { FlagSlide } from "./FlagSlide.tsx";
import { SummarySlide } from "./SummarySlide.tsx";

// Slide 0 is the summary; slides 1..N are flags[0..N-1].
export function Carousel({ report }: { report: FinalReport }) {
  const [slide, setSlide] = useState(0);
  const totalFlags = report.flags.length;

  // Keyboard navigation: arrows move between slides, digits jump to a
  // flag, 0 or S returns to the summary. Ignored while typing in the
  // input panel so the shortcuts never fight the textareas.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      if (target.tagName === "TEXTAREA" || target.tagName === "INPUT") return;
      // Let browser and OS chords through — otherwise Ctrl/Cmd+S jumps to the
      // summary slide while the user is trying to save the page.
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      if (event.key === "ArrowRight") {
        setSlide((s) => Math.min(s + 1, totalFlags));
      } else if (event.key === "ArrowLeft") {
        setSlide((s) => Math.max(s - 1, 0));
      } else if (event.key === "0" || event.key.toLowerCase() === "s") {
        setSlide(0);
      } else if (/^[1-9]$/.test(event.key)) {
        const index = Number(event.key);
        if (index <= totalFlags) setSlide(index);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [totalFlags]);

  if (totalFlags === 0) {
    return (
      <div className="slide-enter stagger">
        <SummarySlide context={report.context} />
        <div className="gl-flag gl-flag--strength">
          <span className="gl-flag-tag">No flags</span>
          <p>
            Nothing here needs fixing — the draft already covers what the
            question is looking for.
          </p>
        </div>
      </div>
    );
  }

  const flag = slide > 0 ? report.flags[slide - 1] : null;

  return (
    <>
      <nav className="carousel-nav" aria-label="Report sections">
        <CarouselDot index={0} current={slide} onJump={setSlide}>
          Summary
        </CarouselDot>
        {report.flags.map((_, i) => (
          <CarouselDot key={i + 1} index={i + 1} current={slide} onJump={setSlide}>
            Flag {i + 1}
          </CarouselDot>
        ))}
        <span className="carousel-hint" aria-hidden="true">
          ← → to move
        </span>
      </nav>

      {/* key forces a remount so the enter animation replays per slide */}
      <div key={slide} className="slide-enter">
        {flag ? (
          <FlagSlide
            flag={flag}
            rewrites={report.rewrites}
            slideIndex={slide}
            totalFlags={totalFlags}
          />
        ) : (
          <SummarySlide context={report.context} />
        )}
      </div>
    </>
  );
}

function CarouselDot({
  index,
  current,
  onJump,
  children,
}: {
  index: number;
  current: number;
  onJump: (index: number) => void;
  children: React.ReactNode;
}) {
  const active = index === current;
  return (
    <button
      type="button"
      className={`carousel-dot${active ? " is-active" : ""}`}
      aria-current={active || undefined}
      onClick={() => onJump(index)}
    >
      {children}
    </button>
  );
}
