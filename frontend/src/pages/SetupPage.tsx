import { useEffect, useState, type FormEvent } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { Bed, Branch, Paginated, Ward } from '../api/types';

export default function SetupPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';

  const [branches, setBranches] = useState<Branch[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);

  const [branchForm, setBranchForm] = useState({ name: '', code: '', city: '' });
  const [wardForm, setWardForm] = useState({ name: '', ward_type: 'general', branch: '' });
  const [bedForm, setBedForm] = useState({ label: '', ward: '' });
  const [error, setError] = useState('');

  function loadAll() {
    client.get<Paginated<Branch>>('/branches/').then((res) => setBranches(res.data.results));
    client.get<Paginated<Ward>>('/wards/').then((res) => setWards(res.data.results));
    client.get<Paginated<Bed>>('/beds/').then((res) => setBeds(res.data.results));
  }

  useEffect(loadAll, []);

  async function createBranch(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await client.post('/branches/', branchForm);
      setBranchForm({ name: '', code: '', city: '' });
      loadAll();
    } catch {
      setError('Could not create branch. Codes must be unique.');
    }
  }

  async function createWard(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      const payload: Record<string, unknown> = { name: wardForm.name, ward_type: wardForm.ward_type };
      if (isSuperAdmin) payload.branch = Number(wardForm.branch);
      await client.post('/wards/', payload);
      setWardForm({ name: '', ward_type: 'general', branch: '' });
      loadAll();
    } catch {
      setError('Could not create ward.');
    }
  }

  async function createBed(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await client.post('/beds/', { label: bedForm.label, ward: Number(bedForm.ward) });
      setBedForm({ label: '', ward: '' });
      loadAll();
    } catch {
      setError('Could not create bed. Labels must be unique within a ward.');
    }
  }

  function branchName(id: number) {
    return branches.find((b) => b.id === id)?.name ?? `Branch ${id}`;
  }

  return (
    <div>
      <h2>Branches &amp; Beds</h2>
      {error && <div className="error-banner">{error}</div>}

      <section className="setup-section">
        <h3>Branches</h3>
        {isSuperAdmin && (
          <form className="inline-form-row" onSubmit={createBranch}>
            <input
              placeholder="Name"
              required
              value={branchForm.name}
              onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
            />
            <input
              placeholder="Code (e.g. HQ)"
              required
              value={branchForm.code}
              onChange={(e) => setBranchForm({ ...branchForm, code: e.target.value })}
            />
            <input
              placeholder="City"
              value={branchForm.city}
              onChange={(e) => setBranchForm({ ...branchForm, city: e.target.value })}
            />
            <button type="submit">Add branch</button>
          </form>
        )}
        <table className="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>City</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {branches.map((b) => (
              <tr key={b.id}>
                <td>{b.code}</td>
                <td>{b.name}</td>
                <td>{b.city}</td>
                <td>{b.is_active ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="setup-section">
        <h3>Wards</h3>
        <form className="inline-form-row" onSubmit={createWard}>
          <input
            placeholder="Ward name"
            required
            value={wardForm.name}
            onChange={(e) => setWardForm({ ...wardForm, name: e.target.value })}
          />
          <select
            value={wardForm.ward_type}
            onChange={(e) => setWardForm({ ...wardForm, ward_type: e.target.value })}
          >
            <option value="general">General</option>
            <option value="icu">ICU</option>
            <option value="maternity">Maternity</option>
            <option value="pediatric">Pediatric</option>
            <option value="emergency">Emergency</option>
            <option value="surgical">Surgical</option>
          </select>
          {isSuperAdmin && (
            <select
              required
              value={wardForm.branch}
              onChange={(e) => setWardForm({ ...wardForm, branch: e.target.value })}
            >
              <option value="">Branch…</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          )}
          <button type="submit">Add ward</button>
        </form>
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Branch</th>
            </tr>
          </thead>
          <tbody>
            {wards.map((w) => (
              <tr key={w.id}>
                <td>{w.name}</td>
                <td>{w.ward_type}</td>
                <td>{branchName(w.branch)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="setup-section">
        <h3>Beds</h3>
        <form className="inline-form-row" onSubmit={createBed}>
          <select required value={bedForm.ward} onChange={(e) => setBedForm({ ...bedForm, ward: e.target.value })}>
            <option value="">Ward…</option>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Bed label (e.g. A-12)"
            required
            value={bedForm.label}
            onChange={(e) => setBedForm({ ...bedForm, label: e.target.value })}
          />
          <button type="submit">Add bed</button>
        </form>
        <table className="data-table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Ward</th>
              <th>Occupied</th>
            </tr>
          </thead>
          <tbody>
            {beds.map((b) => (
              <tr key={b.id}>
                <td>{b.label}</td>
                <td>{wards.find((w) => w.id === b.ward)?.name ?? b.ward}</td>
                <td>{b.is_occupied ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
