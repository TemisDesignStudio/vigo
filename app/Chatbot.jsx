'use client';

import { useRef, useState } from 'react';
import styles from './chatbot.module.css';

const welcome = 'سلام! من دستیار ویگو هستم. درباره تولید محتوا، کریتورها و روند کمپین چه سوالی دارید؟';
const suggestions = ['همکاری در ویگو چه مدل‌هایی دارد؟', 'بسته‌های ویگو از چه مبلغی شروع می‌شوند؟', 'کریتورها چقدر برای پاسخ فرصت دارند؟'];

function directionFor(text) {
  return /[\u0600-\u06FF]/.test(text) ? 'rtl' : 'ltr';
}

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([{ role: 'assistant', content: welcome }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  async function send(text = input) {
    const content = text.trim();
    if (!content || loading) return;
    const nextMessages = [...messages, { role: 'user', content }];
    setMessages(nextMessages);
    setInput('');
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: nextMessages }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'خطایی رخ داد.');
      setMessages((current) => [...current, { role: 'assistant', content: data.message }]);
    } catch (reason) {
      setError(reason.message || 'خطایی رخ داد.');
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  return <>
    <button className={styles.launcher} onClick={() => setOpen(true)} aria-label="باز کردن گفت‌وگو با دستیار ویگو">✦</button>
    {open && <section className={styles.panel} aria-label="گفت‌وگو با دستیار ویگو">
      <header className={styles.header}><div><h3>دستیار ویگو</h3><p>راهنمای کمپین و تولید محتوا</p></div><button className={styles.close} onClick={() => setOpen(false)} aria-label="بستن">×</button></header>
      <div className={styles.messages}>{messages.map((message, index) => <div key={index} className={`${styles.bubble} ${message.role === 'user' ? styles.user : styles.assistant}`} dir={directionFor(message.content)}>{message.content}</div>)}{loading && <div className={`${styles.bubble} ${styles.assistant} ${styles.typing}`}><i/><i/><i/></div>}</div>
      {messages.length === 1 && <div className={styles.suggestions}>{suggestions.map((question) => <button key={question} onClick={() => send(question)}>{question}</button>)}</div>}
      {error && <p className={styles.error}>{error}</p>}
      <form className={styles.form} onSubmit={(event) => { event.preventDefault(); send(); }}><input ref={inputRef} value={input} maxLength={1000} onChange={(event) => setInput(event.target.value)} placeholder="پیامت را بنویس…" aria-label="پیام شما" /><button type="submit" disabled={loading || !input.trim()}>ارسال</button></form>
    </section>}
  </>;
}
