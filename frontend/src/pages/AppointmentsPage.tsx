import { useEffect, useState, type FormEvent } from 'react';
import client from '../api/client';
import PatientPicker from '../components/PatientPicker';
import { useDoctors } from '../hooks/useDoctors';
import type { Appointment, Paginated } from '../api/types';

export default function AppointmentsPage() {
  const doctors = useDoctors();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [patientId, setPatientId] = useState<number | null>(null);
  const [doctorId, setDoctorId] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  function loadAppointments() {
    client.get<Paginated<Appointment>>('/appointments/').then((res) => setAppointments(res.data.results));
  }

  useEffect(loadAppointments, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!patientId || !doctorId || !scheduledTime) {
      setError('Select a patient, doctor, and time.');
      return;
    }
    try {
      await client.post('/appointments/', {
        patient: patientId,
        doctor: Number(doctorId),
        scheduled_time: new Date(scheduledTime).toISOString(),
        reason,
      });
      setShowForm(false);
      setPatientId(null);
      setDoctorId('');
      setScheduledTime('');
      setReason('');
      loadAppointments();
    } catch {
      setError('Could not book appointment.');
    }
  }

  async function updateStatus(id: number, status: Appointment['status']) {
    await client.patch(`/appointments/${id}/`, { status });
    loadAppointments();
  }

  return (
    <div>
      <div className="page-header">
        <h2>Appointments</h2>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? 'Cancel' : 'Book Appointment'}</button>
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
              Date &amp; time
              <input
                type="datetime-local"
                required
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
              />
            </label>
          </div>
          <label>
            Reason
            <input value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button type="submit">Book</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>When</th>
            <th>Patient</th>
            <th>Doctor</th>
            <th>Reason</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.id}>
              <td>{new Date(a.scheduled_time).toLocaleString()}</td>
              <td>{a.patient_name}</td>
              <td>{a.doctor_name}</td>
              <td>{a.reason}</td>
              <td>
                <select
                  value={a.status}
                  onChange={(e) => updateStatus(a.id, e.target.value as Appointment['status'])}
                >
                  <option value="scheduled">Scheduled</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="no_show">No Show</option>
                </select>
              </td>
            </tr>
          ))}
          {appointments.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No appointments yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
