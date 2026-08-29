export type Role =
  | 'super_admin'
  | 'branch_admin'
  | 'doctor'
  | 'nurse'
  | 'receptionist'
  | 'pharmacist'
  | 'lab_tech'
  | 'accountant';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  branch: number | null;
  phone: string;
  is_active: boolean;
  date_joined: string;
}

export interface Branch {
  id: number;
  name: string;
  code: string;
  address: string;
  city: string;
  phone: string;
  is_active: boolean;
  created_at: string;
}

export interface Ward {
  id: number;
  branch: number;
  name: string;
  ward_type: string;
}

export interface Bed {
  id: number;
  ward: number;
  label: string;
  is_occupied: boolean;
}

export interface Patient {
  id: number;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: 'male' | 'female' | 'other';
  blood_group: string;
  phone: string;
  email: string;
  address: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  registered_branch: number;
  created_at: string;
  updated_at: string;
}

export interface OPDVisit {
  id: number;
  patient: number;
  patient_name: string;
  branch: number;
  doctor: number;
  doctor_name: string;
  visit_date: string;
  chief_complaint: string;
  diagnosis: string;
  notes: string;
  status: 'waiting' | 'in_consultation' | 'completed' | 'cancelled';
  consultation_fee: string;
}

export interface Admission {
  id: number;
  patient: number;
  patient_name: string;
  branch: number;
  bed: number;
  attending_doctor: number;
  reason: string;
  status: 'admitted' | 'discharged';
  admission_date: string;
  discharge_date: string | null;
  discharge_notes: string;
}

export interface Appointment {
  id: number;
  patient: number;
  patient_name: string;
  branch: number;
  doctor: number;
  doctor_name: string;
  scheduled_time: string;
  reason: string;
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
