export function Logo({ tamanho = 28 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="logo-gradiente" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#c4b5fd" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="14" r="11" fill="url(#logo-gradiente)" />
      <circle cx="12" cy="10" r="3" fill="#fff" opacity="0.55" />
      <rect x="8" y="26" width="16" height="3" rx="1.5" fill="#a78bfa" />
    </svg>
  );
}
