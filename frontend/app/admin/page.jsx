'use client';

import { useEffect, useState } from 'react';
import styles from './admin.module.css';
import AdminAssistant from './AdminAssistant';

const campaignStatuses = ['new', 'reviewing', 'approved', 'active', 'completed', 'rejected'];
const collaborationStatuses = ['new', 'reviewing', 'approved', 'rejected'];
const campaignInitial = { brand_name: '', requester_name: '', contact: '', budget: '', objective: '', description: '' };
const collaborationInitial = { name: '', contact: '', social_network: '', profile_url: '', activity_field: '', description: '' };
const labels = { brand_name: 'نام برند', requester_name: 'نام درخواست‌دهنده', contact: 'راه ارتباطی', budget: 'بودجه (تومان)', objective: 'هدف کمپین', description: 'توضیحات', name: 'نام و نام خانوادگی', social_network: 'شبکه اجتماعی', profile_url: 'لینک پروفایل', activity_field: 'حوزه فعالیت' };

export default function AdminPage() {
  const [username, setUsername] = useState('');
  const [tab, setTab] = useState('campaigns');
  const [campaigns, setCampaigns] = useState([]);
  const [collaborations, setCollaborations] = useState([]);
  const [campaign, setCampaign] = useState(campaignInitial);
  const [collaboration, setCollaboration] = useState(collaborationInitial);
  const [message, setMessage] = useState('');

  async function request(path, options = {}) {
    const response = await fetch(path, { credentials: 'include', ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
    if (!response.ok) throw new Error((await response.json()).detail || 'عملیات انجام نشد.');
    return response.status === 204 ? null : response.json();
  }
  async function load() {
    try {
      const [campaignData, collaborationData] = await Promise.all([request('/api/admin/campaigns'), request('/api/admin/collaboration-requests')]);
      setCampaigns(campaignData); setCollaborations(collaborationData);
    } catch { window.location.assign('/login'); }
  }
  useEffect(() => { request('/api/auth/me').then((user) => { setUsername(user.username); load(); }).catch(() => window.location.assign('/login')); }, []);
  async function logout() { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); window.location.assign('/login'); }
  async function submit(event) {
    event.preventDefault(); setMessage('');
    const isCampaign = tab === 'campaigns';
    const data = isCampaign ? { ...campaign, budget: Number(campaign.budget) } : collaboration;
    try {
      await request(isCampaign ? '/api/admin/campaigns' : '/api/admin/collaboration-requests', { method: 'POST', body: JSON.stringify(data) });
      isCampaign ? setCampaign(campaignInitial) : setCollaboration(collaborationInitial);
      setMessage('رکورد با موفقیت ثبت شد.'); await load();
    } catch (error) { setMessage(error.message); }
  }
  async function changeStatus(record, status) {
    try { await request(`/api/admin/${tab}/${record.id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }); setMessage('وضعیت به‌روزرسانی شد.'); await load(); }
    catch (error) { setMessage(error.message); }
  }
  const items = tab === 'campaigns' ? campaigns : collaborations;
  const fields = tab === 'campaigns' ? campaign : collaboration;
  const setFields = tab === 'campaigns' ? setCampaign : setCollaboration;
  const statuses = tab === 'campaigns' ? campaignStatuses : collaborationStatuses;
  return <main className={`shell ${styles.page}`}><header className={styles.header}><div><small>پنل مدیریت Vigo</small><h1>خوش آمدید {username || '...'}</h1></div><button className="button" onClick={logout}>خروج از حساب</button></header>
    <div className={styles.tabs}><button className={tab === 'campaigns' ? styles.active : ''} onClick={() => setTab('campaigns')}>کمپین‌ها</button><button className={tab === 'collaboration-requests' ? styles.active : ''} onClick={() => setTab('collaboration-requests')}>درخواست‌های همکاری</button></div>
    <div className={styles.workspace}><section className={styles.grid}><div className={styles.panel}><h2>ثبت {tab === 'campaigns' ? 'کمپین' : 'درخواست همکاری'}</h2><form onSubmit={submit}>{Object.entries(fields).map(([name, value]) => <label key={name}>{labels[name]}<input required={name !== 'description'} name={name} value={value} type={name === 'budget' ? 'number' : 'text'} dir={name.includes('contact') || name.includes('url') || name === 'budget' ? 'ltr' : undefined} onChange={(event) => setFields({ ...fields, [name]: event.target.value })} /></label>)}<button className="button">ثبت در پنل</button>{message && <p className={styles.message}>{message}</p>}</form></div>
      <div className={styles.panel}><h2>{tab === 'campaigns' ? 'فهرست کمپین‌ها' : 'فهرست درخواست‌های همکاری'}</h2>{items.length === 0 ? <p className={styles.empty}>هنوز رکوردی ثبت نشده است.</p> : <div className={styles.list}>{items.map((item) => <article key={item.id}><div><b>{tab === 'campaigns' ? item.brand_name : item.name}</b><span>{tab === 'campaigns' ? item.requester_name : item.social_network}</span></div><select value={item.status} onChange={(event) => changeStatus(item, event.target.value)}>{statuses.map((value) => <option key={value}>{value}</option>)}</select></article>)}</div>}</div>
    </section><AdminAssistant onChange={load} /></div></main>;
}
