'use client';

import { useState } from 'react';
import styles from './requestForms.module.css';

const initialCampaign = { requester_name: '', brand_name: '', contact: '', budget: '', objective: '', start_date: '', end_date: '', description: '' };
const initialCollaboration = { name: '', contact: '', social_network: '', profile_url: '', activity_field: '', description: '' };

export default function RequestForms() {
  const [kind, setKind] = useState('campaign');
  const [campaign, setCampaign] = useState(initialCampaign);
  const [collaboration, setCollaboration] = useState(initialCollaboration);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const values = kind === 'campaign' ? campaign : collaboration;

  function change(event) {
    const next = { ...values, [event.target.name]: event.target.value };
    kind === 'campaign' ? setCampaign(next) : setCollaboration(next);
  }

  async function submit(event) {
    event.preventDefault();
    setSending(true);
    setMessage('');
    const payload = kind === 'campaign' ? { ...campaign, budget: Number(campaign.budget) } : collaboration;
    try {
      const response = await fetch(kind === 'campaign' ? '/api/campaigns' : '/api/collaboration-requests', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      setMessage(kind === 'campaign' ? 'درخواست کمپین شما با موفقیت ثبت شد.' : 'درخواست همکاری شما با موفقیت ثبت شد.');
      kind === 'campaign' ? setCampaign(initialCampaign) : setCollaboration(initialCollaboration);
    } catch (error) {
      setMessage(error.message || 'ثبت درخواست ممکن نشد. لطفاً دوباره تلاش کنید.');
    } finally { setSending(false); }
  }

  return <section id="campaign-form" className="section shell"><div className={styles.wrap}>
    <div className={styles.intro}><small>ثبت درخواست</small><h2>برای شروع، چند اطلاعات کوتاه بده.</h2><p>پس از ثبت، درخواست شما برای بررسی در اختیار تیم ویگو قرار می‌گیرد.</p></div>
    <div className={styles.tabs}><button className={kind === 'campaign' ? styles.active : ''} onClick={() => { setKind('campaign'); setMessage(''); }}>درخواست کمپین</button><button className={kind === 'collaboration' ? styles.active : ''} onClick={() => { setKind('collaboration'); setMessage(''); }}>درخواست همکاری</button></div>
    <form className={styles.form} onSubmit={submit}>
      {kind === 'campaign' ? <>
        <Field label="نام درخواست‌دهنده" name="requester_name" value={campaign.requester_name} onChange={change} required />
        <Field label="نام برند یا کسب‌وکار" name="brand_name" value={campaign.brand_name} onChange={change} required />
        <Field label="شماره تماس یا ایمیل" name="contact" type="text" value={campaign.contact} onChange={change} required dir="ltr" />
        <Field label="بودجه (تومان)" name="budget" type="number" min="0" value={campaign.budget} onChange={change} required dir="ltr" />
        <Field label="هدف کمپین" name="objective" value={campaign.objective} onChange={change} required />
        <Field label="شروع بازه زمانی" name="start_date" type="date" value={campaign.start_date} onChange={change} dir="ltr" />
        <Field label="پایان بازه زمانی" name="end_date" type="date" value={campaign.end_date} onChange={change} dir="ltr" />
      </> : <>
        <Field label="نام و نام خانوادگی" name="name" value={collaboration.name} onChange={change} required />
        <Field label="شماره تماس یا ایمیل" name="contact" value={collaboration.contact} onChange={change} required dir="ltr" />
        <Field label="شبکه اجتماعی" name="social_network" value={collaboration.social_network} onChange={change} required />
        <Field label="لینک پروفایل" name="profile_url" value={collaboration.profile_url} onChange={change} required dir="ltr" />
        <Field label="حوزه فعالیت" name="activity_field" value={collaboration.activity_field} onChange={change} required />
      </>}
      <label className={styles.full}>توضیحات<textarea name="description" value={values.description} onChange={change} rows="4" /></label>
      <div className={styles.footer}><button className="button" disabled={sending}>{sending ? 'در حال ثبت...' : 'ثبت درخواست'}</button>{message && <p className={message.includes('موفقیت') ? styles.success : styles.error}>{message}</p>}</div>
    </form>
  </div></section>;
}

function Field({ label, dir, ...props }) { return <label>{label}<input {...props} dir={dir} /></label>; }
