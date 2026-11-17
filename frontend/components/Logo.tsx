/** A hand-mirror in comic ink: "nhìn lại chính mình". Decorative only. */
export function LogoMark({ className = "size-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden>
      {/* hard shadow */}
      <circle cx="19" cy="18" r="13" fill="var(--ink)" transform="translate(2.5 2.5)" />
      <rect x="25" y="27" width="6" height="12" rx="2" transform="rotate(-40 28 33) translate(2.5 2.5)" fill="var(--ink)" />
      {/* handle */}
      <rect x="25" y="27" width="6" height="12" rx="2" transform="rotate(-40 28 33)" fill="var(--gold)" stroke="var(--ink)" strokeWidth="2.5" />
      {/* frame + glass */}
      <circle cx="19" cy="18" r="13" fill="var(--primary)" stroke="var(--ink)" strokeWidth="2.5" />
      <circle cx="19" cy="18" r="8.5" fill="var(--card)" stroke="var(--ink)" strokeWidth="2" />
      {/* a tiny rising line in the reflection */}
      <path d="M13.5 21.5l3.5-3.5 2.5 2.5 5-5.5" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      {/* shine */}
      <path d="M8.5 12.5a11 11 0 0 1 5-5" fill="none" stroke="var(--card)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
