'use client';

import { useState } from 'react';
import styles from './login.module.css';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault();
    setError('');
    const response = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ username, password }) });
    if (!response.ok) { setError('نام کاربری یا رمز عبور نادرست است.'); return; }
    window.location.assign('/admin');
  }

  return <main className={styles.page}><form onSubmit={submit} className={styles.card}><div className={styles.heading}><span>VIGO</span><h1>ورود به پنل مدیریت</h1><p>برای ادامه، اطلاعات ورود خود را وارد کنید.</p></div><label className={styles.field}>نام کاربری<input dir="ltr" value={username} onChange={(event) => setUsername(event.target.value)} required /></label><label className={styles.field}>رمز عبور<input dir="ltr" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error && <p className={styles.error} role="alert">{error}</p>}<button className={`button ${styles.submit}`} type="submit">ورود</button></form></main>;
}
