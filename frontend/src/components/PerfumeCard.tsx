import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import type { Perfume } from '../types';
import PerfumeImage from './PerfumeImage';
import Stars from './Stars';

interface Props {
  perfume: Perfume;
  rating?: number;
  footer?: ReactNode;
}

export default function PerfumeCard({ perfume, rating, footer }: Props) {
  const meta = [perfume.family, perfume.subfamily].filter(Boolean).join(' · ');

  return (
    <article className="perfume-card">
      <Link to={`/perfumes/${perfume.id}`} className="perfume-card-link">
        <PerfumeImage
          src={perfume.imageUrl}
          alt={`${perfume.brand} ${perfume.name}`}
          gender={perfume.gender}
          family={perfume.family}
        />
        <div className="perfume-card-body">
          <p className="eyebrow">{perfume.brand}</p>
          <h3>{perfume.name}</h3>
          {meta && <p className="meta">{meta}</p>}
          {typeof rating === 'number' && <Stars value={rating} />}
        </div>
      </Link>
      {footer && <div className="perfume-card-footer">{footer}</div>}
    </article>
  );
}
