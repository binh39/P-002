export function LogoIcon({ className = "" }: { className?: string }) {
  return (
    <span className={`brand-logo ${className}`.trim()} aria-hidden="true">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path
          d="M4 20C4 20 4 14 10 10C16 6 20 4 20 4C20 4 18 8 14 14C10 20 4 20 4 20Z"
          fill="white"
        />
        <path d="M4 20L10 14" stroke="white" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function Brand() {
  return (
    <span className="brand-lockup">
      <LogoIcon />
      <strong>PromptOpt</strong>
    </span>
  );
}
