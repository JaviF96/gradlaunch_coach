export function ErrorFlag({ message }: { message: string }) {
  return (
    <div className="gl-flag gl-flag--critical slide-enter">
      <span className="gl-flag-tag">Error</span>
      <p>{message}</p>
    </div>
  );
}
