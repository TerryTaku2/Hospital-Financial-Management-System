import { useEffect, useState, type FormEvent } from 'react';
import client from '../api/client';
import PatientPicker from '../components/PatientPicker';
import { useDoctors } from '../hooks/useDoctors';
import type { Admission, Bed, Paginated, Ward } from '../api/types';

export default function IPDPage() {
  const doctors = useDoctors();
  const [admissions, setAdmissions] = useState<Admission[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [patientId, setPatientId] = useState<number | null>(null);
  const [doctorId, setDoctorId] = useState('');
  const [bedId, setBedId] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  function loadData() {
    client.get<Paginated<Admission>>('/admissions/').then((res) => setAdmissions(res.data.results));
    client.get<Paginated<Bed>>('/beds/').then((res) => setBeds(res.data.results));
    client.get<Paginated<Ward>>('/wards/').then((res) => setWards(res.data.results));
  }

  useEffect(loadData, []);

  function wardName(wardId: number) {
    return wards.find((w) => w.id === wardId)?.name ?? `Ward ${wardId}`;
  }

  const availableBeds = beds.filter((b) => !b.is_occupied);

  async function handleAdmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!patientId || !doctorId || !bedId) {
      setError('Select a patient, doctor, and bed.');
      return;
    }
    try {
      await client.post('/admissions/', {
        patient: patientId,
        attending_doctor: Number(doctorId),
        bed: Number(bedId),
        reason,
      });
      setShowForm(false);
      setPatientId(null);
      setDoctorId('');
      setBedId('');
      setReason('');
      loadData();
    } catch {
      setError('Could not admit patient. The bed may already be taken.');
    }
  }

  async function handleDischarge(id: number) {
    await client.post(`/admissions/${id}/discharge/`, {});
    loadData();
  }

  return (
    <div>
      <div className="page-header">
        <h2>IPD Admissions</h2>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? 'Cancel' : 'Admit Patient'}</button>
      </div>

      {showForm && (
        <form className="inline-form" onSubmit={handleAdmit}>
          {error && <div className="error-banner">{error}</div>}
          <label>Patient</label>
          <PatientPicker value={patientId} onChange={setPatientId} />
          <div className="form-row">
            <label>
              Attending doctor
              <select value={doctorId} onChange={(e) => setDoctorId(e.target.value)} required>
                <option value="">Select a doctor…</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.first_name || d.username} {d.last_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Bed
              <select value={bedId} onChange={(e) => setBedId(e.target.value)} required>
                <option value="">Select an available bed…</option>
                {availableBeds.map((b) => (
                  <option key={b.id} value={b.id}>
                    {wardName(b.ward)} — Bed {b.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Reason for admission
            <input required value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button type="submit">Admit</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Reason</th>
            <th>Admitted</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {admissions.map((a) => (
            <tr key={a.id}>
              <td>{a.patient_name}</td>
              <td>{a.reason}</td>
              <td>{new Date(a.admission_date).toLocaleString()}</td>
              <td>{a.status}</td>
              <td>
                {a.status === 'admitted' && (
                  <button className="btn-link" onClick={() => handleDischarge(a.id)}>
                    Discharge
                  </button>
                )}
              </td>
            </tr>
          ))}
          {admissions.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No admissions yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
