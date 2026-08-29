import { useEffect, useState, type FormEvent } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { Branch, Paginated, Patient } from '../api/types';

const emptyForm = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: 'female',
  blood_group: '',
  phone: '',
  email: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
};

export default function PatientsPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const [patients, setPatients] = useState<Patient[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [registeredBranch, setRegisteredBranch] = useState('');
  const [error, setError] = useState('');

  function loadPatients(query = '') {
    client
      .get<Paginated<Patient>>('/patients/', { params: query ? { search: query } : {} })
      .then((res) => setPatients(res.data.results));
  }

  useEffect(() => {
    const handle = setTimeout(() => loadPatients(search), 300);
    return () => clearTimeout(handle);
  }, [search]);

  useEffect(() => {
    // Super admins have no branch of their own, so they must pick one to
    // register a patient under; everyone else registers under their own.
    if (isSuperAdmin) {
      client.get<Paginated<Branch>>('/branches/').then((res) => setBranches(res.data.results));
    }
  }, [isSuperAdmin]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError('');
    const branchId = isSuperAdmin ? Number(registeredBranch) : user?.branch;
    if (!branchId) {
      setError('Select a branch to register this patient under.');
      return;
    }
    try {
      await client.post('/patients/', { ...form, registered_branch: branchId });
      setForm(emptyForm);
      setRegisteredBranch('');
      setShowForm(false);
      loadPatients(search);
    } catch {
      setError('Could not register patient. Check the form and try again.');
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Patients</h2>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? 'Cancel' : 'Register Patient'}</button>
      </div>

      <input
        className="search-box"
        placeholder="Search by name, MRN, phone…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {showForm && (
        <form className="inline-form" onSubmit={handleCreate}>
          {error && <div className="error-banner">{error}</div>}
          {isSuperAdmin && (
            <label>
              Registering branch
              <select
                required
                value={registeredBranch}
                onChange={(e) => setRegisteredBranch(e.target.value)}
              >
                <option value="">Select a branch…</option>
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="form-row">
            <label>
              First name
              <input
                required
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </label>
            <label>
              Last name
              <input
                required
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Date of birth
              <input
                type="date"
                required
                value={form.date_of_birth}
                onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
              />
            </label>
            <label>
              Gender
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              Blood group
              <input
                value={form.blood_group}
                onChange={(e) => setForm({ ...form, blood_group: e.target.value })}
                placeholder="O+"
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Phone
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label>
              Email
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
          </div>
          <label>
            Address
            <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </label>
          <div className="form-row">
            <label>
              Emergency contact name
              <input
                value={form.emergency_contact_name}
                onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })}
              />
            </label>
            <label>
              Emergency contact phone
              <input
                value={form.emergency_contact_phone}
                onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })}
              />
            </label>
          </div>
          <button type="submit">Save patient</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>MRN</th>
            <th>Name</th>
            <th>DOB</th>
            <th>Gender</th>
            <th>Phone</th>
          </tr>
        </thead>
        <tbody>
          {patients.map((p) => (
            <tr key={p.id}>
              <td>{p.mrn}</td>
              <td>
                {p.first_name} {p.last_name}
              </td>
              <td>{p.date_of_birth}</td>
              <td>{p.gender}</td>
              <td>{p.phone}</td>
            </tr>
          ))}
          {patients.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No patients found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
