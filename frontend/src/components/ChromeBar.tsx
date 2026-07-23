export function ChromeBar() {
  return (
    <header className="gl-chrome">
      <div className="gl-brand">
        <svg
          className="gl-mark"
          viewBox="0 0 24 24"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
        </svg>
        <span className="gl-wordmark">GradLaunch</span>
      </div>
      <span className="gl-chrome-rule" aria-hidden="true" />
      <h1 className="gl-product-name">Application feedback</h1>
    </header>
  );
}
