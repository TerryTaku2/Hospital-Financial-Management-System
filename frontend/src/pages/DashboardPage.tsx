import { useEffect, useState } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { Paginated } from '../api/types';

const CARDS: { key: string; label: string; endpoint: string }[] = [
  { key: 'patients', label: 'Patients', endpoint: '/patients/' },
  { key: 'opd', label: 'OPD Visits', endpoint: '/opd-visits/' },
  { key: 'ipd', label: 'Active Admissions', endpoint: '/admissions/?status=admitted' },
  { key: 'appointments', label: 'Appointments', endpoint: '/appointments/' },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [counts, setCounts] = useState<Record<string, number | null>>({});

  useEffect(() => {
    CARDS.forEach((card) => {
      client
        .get<Paginated<unknown>>(card.endpoint)
        .then((res) => setCounts((prev) => ({ ...prev, [card.key]: res.data.count })))
        .catch(() => setCounts((prev) => ({ ...prev, [card.key]: null })));
    });
  }, []);

  return (
    <div>
      <h2>Welcome, {user?.first_name || user?.username}</h2>
      <p className="muted">
        {user?.role === 'super_admin' ? 'Viewing data across all branches.' : 'Viewing data for your branch.'}
      </p>
      <div className="card-grid">
        {CARDS.map((card) => (
          <div className="stat-card" key={card.key}>
            <div className="stat-value">{counts[card.key] ?? '—'}</div>
            <div className="stat-label">{card.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
