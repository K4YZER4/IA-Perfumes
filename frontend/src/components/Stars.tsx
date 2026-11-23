interface Props {
  value: number;
  onChange?: (value: number) => void;
}

export default function Stars({ value, onChange }: Props) {
  return (
    <div className={`stars ${onChange ? 'interactive' : ''}`}>
      {[1, 2, 3, 4, 5].map((star) => {
        const active = star <= value;
        if (onChange) {
          return (
            <button
              key={star}
              type="button"
              className={active ? 'star active' : 'star'}
              onClick={() => onChange(star)}
              aria-label={`Calificar con ${star} de 5`}
            >
              ★
            </button>
          );
        }
        return (
          <span key={star} className={active ? 'star active' : 'star'} aria-hidden="true">
            ★
          </span>
        );
      })}
    </div>
  );
}
