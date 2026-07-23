export function LoadingSkeleton() {
  return (
    <div role="status">
      <p className="gl-label loading-note">
        Analysing — usually 10 to 20 seconds
      </p>
      <div className="gl-skeleton" aria-hidden="true">
        <div className="gl-skeleton-line gl-skeleton-line--tag" />
        <div className="gl-skeleton-line" />
        <div className="gl-skeleton-line" />
        <div className="gl-skeleton-line" />
        <div className="gl-skeleton-line" />
        <div className="gl-skeleton-line" />
        <div className="gl-skeleton-line" />
      </div>
    </div>
  );
}
