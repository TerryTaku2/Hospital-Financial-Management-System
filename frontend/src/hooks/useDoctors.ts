import { useEffect, useState } from 'react';
import client from '../api/client';
import type { Paginated, User } from '../api/types';

export function useDoctors() {
  const [doctors, setDoctors] = useState<User[]>([]);

  useEffect(() => {
    client
      .get<Paginated<User>>('/users/', { params: { role: 'doctor' } })
      .then((res) => setDoctors(res.data.results.filter((u) => u.role === 'doctor')))
      .catch(() => setDoctors([]));
  }, []);

  return doctors;
}
