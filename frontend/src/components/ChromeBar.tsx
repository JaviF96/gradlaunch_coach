import logo from "../assets/gradlaunch-logo.png";

export function ChromeBar() {
  return (
    <header className="gl-chrome">
      <div className="gl-brand">
        <img className="gl-logo" src={logo} alt="GradLaunch" />
      </div>
      <span className="gl-chrome-rule" aria-hidden="true" />
      <h1 className="gl-product-name">Application feedback</h1>
    </header>
  );
}
