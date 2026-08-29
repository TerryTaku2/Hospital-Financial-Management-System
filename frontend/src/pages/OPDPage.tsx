import { useEffect, useState, type FormEvent } from 'react';
import client from '../api/client';
import PatientPicker from '../components/PatientPicker';
import { useDoctors } from '../hooks/useDoctors';
import type { OPDVisit, Paginated } from '../api/types';

export default function OPDPage() {
  const doctors = useDoctors();
  const [visits, setVisits] = useState<OPDVisit[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [patientId, setPatientId] = useState<number | null>(null);
  const [doctorId, setDoctorId] = useState('');
  const [complaint, setComplaint] = useState('');
  const [fee, setFee] = useState('0');
  const [error, setError] = useState('');

  function loadVisits() {
    client.get<Paginated<OPDVisit>>('/opd-visits/').then((res) => setVisits(res.data.results));
  }

  useEffect(loadVisits, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!patientId || !doctorId) {
      setError('Select a patient and a doctor.');
      return;
    }
    try {
      await client.post('/opd-visits/', {
        patient: patientId,
        doctor: Number(doctorId),
        chief_complaint: complaint,
        consultation_fee: fee,
      });
      setShowForm(false);
      setPatientId(null);
      setDoctorId('');
      setComplaint('');
      setFee('0');
      loadVisits();
    } catch {
      setError('Could not create OPD visit.');
    }
  }

  async function updateStatus(id: number, status: OPDVisit['status']) {
    await client.patch(`/opd-visits/${id}/`, { status });
    loadVisits();
  }

  return (
    <div>
      <div className="page-header">
        <h2>OPD Visits</h2>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? 'Cancel' : 'New Visit'}</button>
      </div>

      {showForm && (
        <form className="inline-form" onSubmit={handleCreate}>
          {error && <div className="error-banner">{error}</div>}
          <label>Patient</label>
          <PatientPicker value={patientId} onChange={setPatientId} />
          <div className="form-row">
            <label>
              Doctor
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
              Consultation fee
              <input type="number" step="0.01" value={fee} onChange={(e) => setFee(e.target.value)} />
            </label>
          </div>
          <label>
            Chief complaint
            <input required value={complaint} onChange={(e) => setComplaint(e.target.value)} />
          </label>
          <button type="submit">Create visit</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Patient</th>
            <th>Doctor</th>
            <th>Complaint</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {visits.map((v) => (
            <tr key={v.id}>
              <td>{new Date(v.visit_date).toLocaleString()}</td>
              <td>{v.patient_name}</td>
              <td>{v.doctor_name}</td>
              <td>{v.chief_complaint}</td>
              <td>
                <select value={v.status} onChange={(e) => updateStatus(v.id, e.target.value as OPDVisit['status'])}>
                  <option value="waiting">Waiting</option>
                  <option value="in_consultation">In Consultation</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </td>
            </tr>
          ))}
          {visits.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No OPD visits yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
