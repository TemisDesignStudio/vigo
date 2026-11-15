'use client';

import { useEffect, useState } from 'react';

export default function AdminPage() {
  const [username, setUsername] = useState('');

  useEffect(() => { fetch('/api/auth/me', { credentials: 'include' }).then((response) => response.ok ? response.json() : Promise.reject()).then((user) => setUsername(user.username)).catch(() => window.location.assign('/login')); }, []);
  async function logout() { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); window.location.assign('/login'); }

  return <main className="shell" style={{ minHeight: '70vh', paddingTop: '4rem' }}><section className="card" style={{ padding: '2rem' }}><p>پنل مدیریت</p><h1>خوش آمدید {username || '...'}</h1><p>مدیریت کمپین‌ها و درخواست‌ها در مراحل بعدی اضافه می‌شود.</p><button className="button" onClick={logout}>خروج از حساب</button></section></main>;
}
