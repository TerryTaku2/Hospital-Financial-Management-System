import { useEffect, useState } from 'react';
import client from '../api/client';
import type { Paginated, Patient } from '../api/types';

export default function PatientPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (patientId: number | null) => void;
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Patient[]>([]);
  const [selected, setSelected] = useState<Patient | null>(null);

  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }
    const handle = setTimeout(() => {
      client
        .get<Paginated<Patient>>('/patients/', { params: { search: query } })
        .then((res) => setResults(res.data.results));
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  if (selected) {
    return (
      <div className="picker-selected">
        {selected.mrn} — {selected.first_name} {selected.last_name}
        <button
          type="button"
          className="btn-link"
          onClick={() => {
            setSelected(null);
            onChange(null);
          }}
        >
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="picker">
      <input
        placeholder="Search patient by name, MRN, phone…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {results.length > 0 && (
        <ul className="picker-results">
          {results.map((p) => (
            <li
              key={p.id}
              onClick={() => {
                setSelected(p);
                setQuery('');
                setResults([]);
                onChange(p.id);
              }}
            >
              {p.mrn} — {p.first_name} {p.last_name}
            </li>
          ))}
        </ul>
      )}
      {value === null && query && results.length === 0 && (
        <div className="muted small">No matches. Try registering the patient first.</div>
      )}
    </div>
  );
}
