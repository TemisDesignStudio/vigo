'use client';

import { useState } from 'react';
import styles from './admin.module.css';

const welcome = 'سلام، من دستیار مدیریتی ویگو هستم. می‌توانم با دستور دقیق شما کمپین یا درخواست همکاری ایجاد، ویرایش یا وضعیت آن را تغییر دهم.';

function changeSummary(change) {
  if (!change) return '';
  const name = change.resource === 'campaign' ? change.record.brand_name : change.record.name;
  const action = change.action === 'create' ? 'ایجاد شد' : change.action === 'update' ? 'ویرایش شد' : 'وضعیت آن تغییر کرد';
  return `${change.resource === 'campaign' ? 'کمپین' : 'درخواست همکاری'} «${name}» ${action}.`;
}

export default function AdminAssistant({ onChange }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: welcome }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [change, setChange] = useState(null);

  async function send(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    const nextMessages = [...messages, { role: 'user', content }];
    setMessages(nextMessages); setInput(''); setError(''); setChange(null); setLoading(true);
    try {
      const response = await fetch('/api/admin/assistant', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: nextMessages.slice(-8) }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'دستیار نتوانست پاسخ دهد.');
      setMessages((current) => [...current, { role: 'assistant', content: data.message }]);
      if (data.change) { setChange(data.change); await onChange(); }
    } catch (reason) { setError(reason.message || 'ارسال پیام ناموفق بود.'); }
    finally { setLoading(false); }
  }

  return <aside className={styles.assistant} aria-label="دستیار مدیریتی">
    <header><small>دستیار مدیریتی</small><h2>دستور را به زبان ساده بنویس.</h2><p>تغییر فقط پس از اعتبارسنجی پاسخ اعمال می‌شود.</p></header>
    <div className={styles.assistantMessages}>{messages.map((message, index) => <p key={index} className={message.role === 'user' ? styles.assistantUser : styles.assistantReply}>{message.content}</p>)}{loading && <p className={styles.assistantReply}>در حال بررسی دستور...</p>}</div>
    {change && <p className={styles.change}>{changeSummary(change)}</p>}
    {error && <p className={styles.assistantError}>{error}</p>}
    <form onSubmit={send}><textarea value={input} maxLength="1000" onChange={(event) => setInput(event.target.value)} placeholder="مثلاً وضعیت کمپین شماره ۳ را به reviewing تغییر بده" aria-label="دستور برای دستیار مدیریتی" rows="4" /><button className="button" disabled={loading || !input.trim()}>{loading ? 'در حال ارسال...' : 'ارسال دستور'}</button></form>
  </aside>;
}
