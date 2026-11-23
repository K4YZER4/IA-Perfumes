interface Props {
  src?: string | null;
  alt: string;
  className?: string;
  gender?: string | null;
  family?: string | null;
}

interface ThemeConfig {
  gradient: string;
  bottleColor: string;
  accentColor: string;
  labelBg: string;
  textColor: string;
  iconName: string;
}

function getTheme(gender?: string | null, family?: string | null): ThemeConfig {
  const normFamily = (family || '').toUpperCase();
  const normGender = (gender || '').toLowerCase();

  // 1. Prioridad por familia olfativa si existe
  if (normFamily.includes('FLORAL')) {
    return {
      gradient: 'linear-gradient(145deg, #fce7f3 0%, #fbcfe8 100%)',
      bottleColor: '#db2777',
      accentColor: '#f472b6',
      labelBg: '#fdf2f8',
      textColor: '#9d174d',
      iconName: 'Floral',
    };
  }

  if (normFamily.includes('CITRUS')) {
    return {
      gradient: 'linear-gradient(145deg, #fef3c7 0%, #fde68a 100%)',
      bottleColor: '#d97706',
      accentColor: '#fbbf24',
      labelBg: '#fffbeb',
      textColor: '#b45309',
      iconName: 'Cítrico',
    };
  }

  if (normFamily.includes('WOODY') || normFamily.includes('LEATHER')) {
    return {
      gradient: 'linear-gradient(145deg, #eaddcf 0%, #cbb79f 100%)',
      bottleColor: '#5c4033',
      accentColor: '#8a6552',
      labelBg: '#f5f0ea',
      textColor: '#4a3328',
      iconName: 'Amaderado',
    };
  }

  if (normFamily.includes('AMBER') || normFamily.includes('ORIENTAL')) {
    return {
      gradient: 'linear-gradient(145deg, #ffedd5 0%, #fed7aa 100%)',
      bottleColor: '#c2410c',
      accentColor: '#f97316',
      labelBg: '#fff7ed',
      textColor: '#9a3412',
      iconName: 'Oriental',
    };
  }

  if (normFamily.includes('AROMATIC') || normFamily.includes('FOUGERE') || normFamily.includes('CHYPRE')) {
    return {
      gradient: 'linear-gradient(145deg, #dcfce7 0%, #bbf7d0 100%)',
      bottleColor: '#15803d',
      accentColor: '#4ade80',
      labelBg: '#f0fdf4',
      textColor: '#166534',
      iconName: 'Aromático',
    };
  }

  // 2. Por género cuando no hay familia definida
  if (normGender.includes('female') || normGender.includes('mujer')) {
    return {
      gradient: 'linear-gradient(145deg, #fae8ff 0%, #f5d0fe 100%)',
      bottleColor: '#9333ea',
      accentColor: '#c084fc',
      labelBg: '#faf5ff',
      textColor: '#7e22ce',
      iconName: 'Mujer',
    };
  }

  if (normGender.includes('male') || normGender.includes('hombre')) {
    return {
      gradient: 'linear-gradient(145deg, #e0f2fe 0%, #bae6fd 100%)',
      bottleColor: '#0284c7',
      accentColor: '#38bdf8',
      labelBg: '#f0f9ff',
      textColor: '#0369a1',
      iconName: 'Hombre',
    };
  }

  // 3. Unisex / Default
  return {
    gradient: 'linear-gradient(145deg, #f1f5f9 0%, #e2e8f0 100%)',
    bottleColor: '#64748b',
    accentColor: '#94a3b8',
    labelBg: '#f8fafc',
    textColor: '#475569',
    iconName: 'Unisex',
  };
}

export default function PerfumeImage({ src, alt, className = '', gender, family }: Props) {
  if (src) {
    return <img className={`perfume-image ${className}`} src={src} alt={alt} loading="lazy" />;
  }

  const theme = getTheme(gender, family);

  return (
    <div
      className={`perfume-image perfume-placeholder ${className}`}
      style={{ background: theme.gradient }}
      role="img"
      aria-label={`${alt} (${theme.iconName})`}
    >
      <svg viewBox="0 0 64 96" aria-hidden="true" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.08))' }}>
        {/* Tapa */}
        <rect x="23" y="6" width="18" height="12" rx="2" fill={theme.bottleColor} />
        {/* Cuello */}
        <rect x="27" y="16" width="10" height="4" fill={theme.accentColor} opacity="0.8" />
        {/* Frasco */}
        <rect x="16" y="20" width="32" height="66" rx="9" fill={theme.bottleColor} opacity="0.9" />
        {/* Brillo */}
        <line x1="20" y1="24" x2="20" y2="80" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
        {/* Etiqueta */}
        <rect x="23" y="38" width="18" height="28" rx="3" fill={theme.labelBg} />
        <rect x="26" y="44" width="12" height="2" rx="1" fill={theme.textColor} opacity="0.8" />
        <rect x="27" y="49" width="10" height="2" rx="1" fill={theme.textColor} opacity="0.5" />
      </svg>
      <span style={{ color: theme.textColor, fontWeight: 600 }}>{theme.iconName}</span>
    </div>
  );
}
