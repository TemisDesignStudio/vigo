import { NextResponse } from 'next/server';
import { vigoAssistantInstructions } from '../../../lib/vigo-knowledge';

export const runtime = 'nodejs';

const MAX_MESSAGE_LENGTH = 1000;
const MAX_HISTORY = 8;
const WINDOW_MS = 5 * 60 * 1000;
const MAX_REQUESTS = 10;
const requests = new Map();

function clientKey(request) {
  return request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'local';
}

function isRateLimited(key) {
  const now = Date.now();
  const entries = (requests.get(key) || []).filter((time) => now - time < WINDOW_MS);
  if (entries.length >= MAX_REQUESTS) return true;
  entries.push(now);
  requests.set(key, entries);
  return false;
}

function validMessage(message) {
  return message && typeof message.content === 'string' && ['user', 'assistant'].includes(message.role) && message.content.trim().length > 0 && message.content.length <= MAX_MESSAGE_LENGTH;
}

function extractReply(content) {
  if (typeof content === 'string') return content.trim();
  if (Array.isArray(content)) {
    return content.map((part) => typeof part === 'string' ? part : part?.text || part?.content || '').join('').trim();
  }
  return '';
}

async function requestOpenRouter(payload, apiKey) {
  let lastError;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          'X-Title': 'Vigo Website Assistant',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(20_000),
      });
    } catch (error) {
      lastError = error;
      if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  throw lastError;
}

export async function POST(request) {
  if (isRateLimited(clientKey(request))) {
    return NextResponse.json({ error: 'تعداد پیام‌ها زیاد است. چند دقیقه دیگر دوباره تلاش کنید.' }, { status: 429 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'درخواست نامعتبر است.' }, { status: 400 });
  }

  const messages = Array.isArray(body?.messages) ? body.messages.slice(-MAX_HISTORY) : [];
  if (!messages.length || !messages.every(validMessage) || messages[messages.length - 1].role !== 'user') {
    return NextResponse.json({ error: 'پیام ارسالی نامعتبر است.' }, { status: 400 });
  }

  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.OPENROUTER_MODEL;
  const hasPlaceholderKey = !apiKey || /your|replace|placeholder/i.test(apiKey);
  if (hasPlaceholderKey || !model) {
    return NextResponse.json({ error: 'کلید OpenRouter در فایل .env معتبر پیکربندی نشده است. لطفاً مقدار OPENROUTER_API_KEY را بررسی کنید.' }, { status: 503 });
  }

  let upstream;
  try {
    upstream = await requestOpenRouter({
        model,
        messages: [{ role: 'system', content: vigoAssistantInstructions }, ...messages],
        max_tokens: 350,
        temperature: 0.35,
      }, apiKey);
  } catch {
    return NextResponse.json({ error: 'اتصال به سرویس دستیار برقرار نشد. لطفاً دوباره تلاش کنید.' }, { status: 503 });
  }

  if (!upstream.ok) {
    const message = upstream.status === 401
      ? 'اعتبار دستیار در سرور تایید نشد.'
      : upstream.status === 429
        ? 'مدل رایگان انتخاب‌شده فعلاً به سقف ظرفیت یا نرخ درخواست رسیده است. چند دقیقه دیگر دوباره امتحان کنید.'
        : upstream.status === 404 || upstream.status === 503
          ? 'مدل انتخاب‌شده فعلاً در دسترس نیست.'
          : 'پاسخ‌گویی دستیار با مشکل روبه‌رو شد. لطفاً دوباره تلاش کنید.';
    return NextResponse.json({ error: message }, { status: [401, 429, 503].includes(upstream.status) ? upstream.status : 502 });
  }

  try {
    const data = JSON.parse(await upstream.text());
    const reply = extractReply(data?.choices?.[0]?.message?.content);
    if (!reply) throw new Error('Missing response');
    return NextResponse.json({ message: reply });
  } catch {
    return NextResponse.json({ error: 'پاسخ دستیار قابل پردازش نبود. لطفاً دوباره تلاش کنید.' }, { status: 502 });
  }
}
