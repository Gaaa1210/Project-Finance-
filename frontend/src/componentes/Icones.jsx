// Ícones desenhados em SVG (assim não precisamos instalar nenhuma biblioteca).
// "currentColor" faz o ícone usar a mesma cor do texto em volta.

const base = {
  width: 26,
  height: 26,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function IconeInicio() {
  return (
    <svg {...base}>
      <path d="M3.5 10.5 12 3.5l8.5 7" />
      <path d="M5.5 9v10.5h4.5v-6h4v6h4.5V9" />
    </svg>
  );
}

export function IconeAtivos() {
  return (
    <svg {...base}>
      <rect x="3.5" y="4" width="17" height="4" rx="1.4" />
      <rect x="3.5" y="10" width="17" height="4" rx="1.4" />
      <rect x="3.5" y="16" width="17" height="4" rx="1.4" />
    </svg>
  );
}

export function IconeDesempenho() {
  return (
    <svg {...base}>
      <path d="M3.5 17.5 9 12l4 3.5 7.5-8" />
      <path d="M15.5 7.5h5v5" />
    </svg>
  );
}

export function IconeAdicionar() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8v8M8 12h8" />
    </svg>
  );
}

export function IconeVoltar() {
  return (
    <svg {...base} width={22} height={22} strokeWidth={2.4}>
      <path d="M15 4.5 7.5 12l7.5 7.5" />
    </svg>
  );
}

export function IconeAtualizar() {
  return (
    <svg {...base} width={20} height={20} strokeWidth={2.2}>
      <path d="M20 11a8 8 0 1 0-2.3 5.7" />
      <path d="M20 4.5V11h-6.5" />
    </svg>
  );
}

export function IconeSeta() {
  return (
    <svg {...base} width={16} height={16} strokeWidth={2.4}>
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}

export function IconeNoticias() {
  return (
    <svg {...base}>
      <path d="M5 4.5h11.5v14a1.5 1.5 0 0 0 1.5 1.5H6.5A1.5 1.5 0 0 1 5 18.5v-14Z" />
      <path d="M16.5 9H19v9.5a1.5 1.5 0 0 1-3 0" />
      <path d="M8 8h5.5M8 11.5h5.5M8 15h3.5" />
    </svg>
  );
}

export function IconeBusca() {
  return (
    <svg {...base} width={17} height={17} strokeWidth={2.3}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 4.5 4.5" />
    </svg>
  );
}

export function IconeFechar() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="currentColor" />
      <path d="m8.5 8.5 7 7m0-7-7 7" stroke="var(--cartao)" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function IconeEmAlta() {
  return (
    <svg {...base} width={14} height={14} strokeWidth={2.6}>
      <path d="M3.5 17.5 9 12l4 3.5 7.5-8" />
      <path d="M15.5 7.5h5v5" />
    </svg>
  );
}

export function IconeLinkExterno() {
  return (
    <svg {...base} width={14} height={14} strokeWidth={2.2}>
      <path d="M14 4.5h5.5V10M19.5 4.5 11 13" />
      <path d="M17 13.5v5a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 4 18.5v-10A1.5 1.5 0 0 1 5.5 7h5" />
    </svg>
  );
}

export function IconeEscudo() {
  return (
    <svg {...base} width={18} height={18} strokeWidth={2}>
      <path d="M12 3.5 5 6v5.5c0 4.3 3 7.9 7 9 4-1.1 7-4.7 7-9V6l-7-2.5Z" />
      <path d="m8.8 12 2.2 2.2 4.2-4.4" />
    </svg>
  );
}

export function IconeConfirmada() {
  return (
    <svg {...base} width={12} height={12} strokeWidth={3}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

export function IconeEmpresas() {
  return (
    <svg {...base}>
      <path d="M4 20.5V6.5l7-3v17" />
      <path d="M11 9.5h9v11" />
      <path d="M2.5 20.5h19" />
      <path d="M7 9h1M7 12.5h1M7 16h1M14.5 13h1M14.5 16.5h1" />
    </svg>
  );
}

export function IconeAlerta() {
  return (
    <svg {...base} width={18} height={18} strokeWidth={2}>
      <path d="M12 4 2.8 19.5h18.4L12 4Z" />
      <path d="M12 10v4.5M12 17.2v.3" />
    </svg>
  );
}

export function IconeInfo() {
  return (
    <svg {...base} width={15} height={15} strokeWidth={2}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.5M12 7.8v.2" />
    </svg>
  );
}
