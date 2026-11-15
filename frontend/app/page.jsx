'use client';

import { useState } from 'react';
import heroStyles from './hero.module.css';
import Chatbot from './Chatbot';

const collaboration = [
  ['۰۱', 'تولید محتوای UGC', 'ویدیو یا عکس را برای کانال‌های خودت تحویل بگیر.', 'peach'],
  ['۰۲', 'همکاری با اینفلوئنسر', 'با مخاطبان یک کریتور از طریق انتشار در صفحه او ارتباط بگیر.', 'pink'],
  ['۰۳', 'انتشار در پیج تبلیغاتی', 'محتوا را در یک صفحه موضوعی و متناسب با بازار هدفت منتشر کن.', 'green']
];
const benefits = [
  ['از بودجه‌ای که داری شروع کن', 'مبلغت را وارد کن تا ببینی با چه کسانی می‌توانی کار کنی و تقریباً چقدر ویو می‌گیری.'],
  ['سبک هر کریتور را از روی نمونه‌کارش بسنج', 'قبل از انتخاب، لحن، اجرا و کیفیت نمونه‌های ثبت‌شده را بررسی کن.'],
  ['کریتور و اینفلوئنسر مناسب را بر اساس حوزه و شهر پیدا کن', 'جست‌وجو را با ویژگی‌هایی محدود کن که برای کمپینت مهم‌اند.'],
  ['هم برای پیجت محتوا بساز، هم تبلیغ کن', 'با یک بودجه در ویگو، هم برای پیجت محتوا بساز و هم در پیج بلاگرها و اینفلوئنسرها تبلیغ کن.']
];
const steps = [
  ['۰۱', 'بگو چه محتوایی می‌خواهی', 'هدفت، نوع محتوا و بودجه‌ات را مشخص کن.'],
  ['۰۲', 'کریتورها و هزینه‌ها را مقایسه کن', 'پیشنهادهای ویگو را ببین و چهره‌های مناسب را انتخاب کن.'],
  ['۰۳', 'درخواست همکاری بفرست', 'خروجی و موعد تحویل را مشخص کن؛ کریتورها تا ۲۴ ساعت فرصت پاسخ دارند.']
];
const creators = [
  ['آوا احمدی', 'ورزش و تناسب اندام', '۱۲,۳۶۷ بازدید · ۵ ریِلز اخیر', '۴۹۶۷ دنبال‌کننده در اینستاگرام', '۵', 'right'],
  ['مینا فرقانی', 'غذا و رستوران', '۴,۲۵۵ بازدید · ۵ ریِلز اخیر', '۱۸۳۸ دنبال‌کننده در اینستاگرام', '۱۲', 'middle'],
  ['سحر ناظری', 'هوش مصنوعی', '۱,۰۹۰ بازدید · ۵ ریِلز اخیر', '۵۵۷ دنبال‌کننده در اینستاگرام', '۱۰', 'left']
];
const faqs = [
  ['ویگو چطور کریتور پیشنهاد می‌دهد؟', 'پیشنهادها براساس هدف کمپین، حوزه، مخاطب و بودجه ارائه می‌شوند.'],
  ['درخواست همکاری تا چه زمانی معتبر است؟', 'کریتور ۲۴ ساعت بعد از ارسال درخواست همکاری را رد یا پذیرفته می‌شود، رزرو اعتبار آزاد می‌شود.'],
  ['کردیت‌ها تا چه زمانی اعتبار دارند؟', 'بسته از زمان فعال‌سازی یک ماه اعتبار دارد. با تمدید به‌موقع، مانده به دوره جدید منتقل می‌شود.'],
  ['از کجا وضعیت پروژه را ببینم؟', 'وضعیت و فایل‌ها در داشبورد وب هستند. اعلان‌های مهم در بات تلگرام هم نمایش داده می‌شوند.']
];
const campaignOptions = {
  '۵ میلیون تومان': {
    credits: '۵۰ کردیت',
    collaborators: '۳ همکار',
    reels: '۳ ریلز تولیدی',
    views: 'حدود ۲۲ هزار بازدید',
    summary: 'ترکیب پیشنهادی نمونه: ۳ همکار، ۵۰ کردیت و ۳ خروجی آماده برند',
    details: ['۱ تولید و انتشار در پیج کریتور: ۱۲ هزار بازدید', '۲ تولید برای انتشار توسط برند: ۶ هزار بازدید', '۱ انتشار در پیج تبلیغاتی: ۴ هزار بازدید']
  },
  '۱۰ میلیون تومان': {
    credits: '۱۰۰ کردیت',
    collaborators: '۶ همکار',
    reels: '۷ ریلز تولیدی',
    views: 'حدود ۵۱ هزار بازدید',
    summary: 'ترکیب پیشنهادی نمونه: ۶ همکار، ۱۰۰ کردیت و ۷ خروجی آماده برند',
    details: ['۲ تولید و انتشار در پیج کریتور: ۳۰ هزار بازدید', '۴ تولید برای انتشار توسط برند: ۱۲ هزار بازدید', '۲ انتشار در پیج تبلیغاتی: ۹ هزار بازدید']
  },
  '۲۵ میلیون تومان': {
    credits: '۲۵۸ کردیت',
    collaborators: '۱۴ همکار',
    reels: '۱۸ ریلز تولیدی',
    views: 'حدود ۱۴۸ هزار بازدید',
    summary: 'ترکیب پیشنهادی نمونه: ۱۴ همکار، ۲۵۸ کردیت و ۱۸ خروجی آماده برند',
    details: ['۶ تولید و انتشار در پیج کریتور: ۸۴ هزار بازدید', '۹ تولید برای انتشار توسط برند: ۲۷ هزار بازدید', '۵ انتشار در پیج تبلیغاتی: ۳۷ هزار بازدید']
  }
};

function ScrollButton({ children = 'شروع کمپین' }) { return <button className="button" onClick={() => document.getElementById('budget').scrollIntoView({ behavior: 'smooth' })}>{children}</button> }

export default function Page() {
  const [budget, setBudget] = useState('۵ میلیون تومان');
  const [open, setOpen] = useState(null);
  const prices = [['شروع', '۵,۰۰۰,۰۰۰', '۵۰'], ['رشد', '۱۵,۰۰۰,۰۰۰', '۱۵۵'], ['گسترش', '۳۰,۰۰۰,۰۰۰', '۳۲۱']];
  const campaign = campaignOptions[budget];
  return <main>
    <header className="nav shell">
      <a className="logo" href="#top">VIGO</a><nav><a href="#creators">کریتورها و اینفلوئنسرها</a><a href="#how">چطور کار می‌کند؟</a><a href="#prices">تعرفه‌ها</a></nav><div className="nav-actions"><a href="/login/">ورود</a><ScrollButton>ساخت کمپین</ScrollButton></div>
    </header>
    <section id="top" className="hero shell">
      <h1>با هر بودجه‌ای که داری، برای برندت کمپین محتوایی بچین؛<br/>از تولید ریلز تا تبلیغات با میکرواینفلوئنسرها.<em>شروع از ۵ میلیون تومان.</em></h1>
      <div className="hero-actions"><ScrollButton/><a href="#creators">کریتور / اینفلوئنسرها</a></div>
      <div className="people">
        <div className={heroStyles.card}><img className={heroStyles.image} src="/images/hero-woman-navy.png" alt="کریتور در حال آماده‌سازی کمپین مد" /></div>
        <div className={`${heroStyles.card} ${heroStyles.featured}`}><img className={heroStyles.image} src="/images/hero-woman-peach.png" alt="کریتور در حال آماده‌سازی محتوای محصول" /><span className={heroStyles.play}>▶</span></div>
        <div className={heroStyles.card}><img className={heroStyles.image} src="/images/hero-man.png" alt="کریتور در حال آماده‌سازی صحنه کمپین" /></div>
      </div>
    </section>
    <section id="budget" className="calculator shell card">
      <div className="calc-intro"><small>برآورد نمونه کمپین</small><h2>با این بودجه چه می‌گیری؟</h2><p>یک بودجه انتخاب کن تا ظرفیت تولید و برآورد بازدید را ببینی.</p><b>بودجه نمونه</b><div className="budget-tabs">{Object.entries(campaignOptions).map(([amount, option]) => <button className={budget===amount?'active':''} onClick={()=>setBudget(amount)} key={amount}>{amount}<span>{option.credits}</span></button>)}</div></div>
      <div className="stat-grid"><div><small>تعداد همکار پیشنهادی</small><strong>{campaign.collaborators}</strong></div><div><small>ظرفیت تولید در این مثال</small><strong>{campaign.reels}</strong></div><div className="highlight"><small>بازدید تخمینی همین نمونه</small><strong>{campaign.views}</strong></div></div>
      <div className="calc-note"><b>{campaign.summary}</b>{campaign.details.map((detail) => <span key={detail}><br/>{detail}</span>)}</div><p className="disclaimer">جمع میانگین بازدید پیج کریتورها و پیج تبلیغاتی، به‌علاوه حدود ۲ هزار بازدید برای هر ریلز قابل انتشار توسط برند. بازدید تضمینی نیست.</p><ScrollButton/>
    </section>
    <section className="section shell"><SectionHeading tag="۰۲ / نوع همکاری" title="با یک بسته، چند نوع همکاری داشته باش." text="یک مبلغ مشخص برای بسته می‌پردازی و اعتبارش را بسته به نیازت بین تولید ریلز، همکاری با اینفلوئنسر و انتشار در پیج‌های تبلیغاتی تقسیم می‌کنی."/><div className="three-grid">{collaboration.map(([num,title,text,style])=><article className={'choice '+style} key={num}><i>{num}</i><h3>{title}</h3><p>{text}</p></article>)}</div></section>
    <section className="gray"><div className="section shell"><SectionHeading tag="۰۳ / مزیت‌ها" title="چرا ویگو برای تولید محتوای برندت؟" text="به اندازه کمپینت هزینه کن، برای هر محتوا چهره مناسب را انتخاب کن و کار را یکجا پیش ببر."/><div className="benefits">{benefits.map(([x,y])=><article key={x}><span>✦</span><h3>{x}</h3><p>{y}</p></article>)}</div></div></section>
    <section id="how" className="section shell"><SectionHeading tag="۰۴ / روند سفارش" title="سفارش محتوا در ویگو چطور پیش می‌رود؟"/><div className="three-grid steps">{steps.map(([n,x,y])=><article key={n}><i>{n}</i><h3>{x}</h3><p>{y}</p></article>)}</div></section>
    <section id="creators" className="section shell creators"><SectionHeading tag="۰۵ / ویترین" title="با کریتورهای ویگو آشنا شو." text="نمونه‌هایی از کریتورهای تاییدشده ویگو، با آمار ثبت‌شده ریلزهای اخیرشان."/><div className="creator-grid">{creators.map(([name,field,views,followers,c,cls])=><article className="creator" key={name}><div className={'creator-image '+cls}><span>▶</span></div><small>نمونه‌ویدیو · کاور پیش‌فرض</small><h3>{name}</h3><b>{field}</b><p>{views}</p><p>{followers}</p><strong>تولید از {c} کردیت</strong></article>)}</div></section>
    <section id="prices" className="gray"><div className="section shell"><SectionHeading tag="۰۶ / هزینه‌ها" title="بستهٔ تولید محتوا، متناسب با بودجه‌ات" text="از بسته کوچک برای چند ریلز تا اعتبار یک کمپین بزرگ‌تر، پیش از ارسال درخواست همکاری، هزینه و خروجی هر همکاری را دقیق می‌بینی."/><div className="price-grid">{prices.map(([name,price,credit],i)=><article className={'price '+(i===1?'featured':'')} key={name}><small>{i===0?'برای شروع':i===1?'پیشنهاد ویگو':'برای چند کمپین'}</small><h3>{name}</h3><strong>{price}</strong><p>تومان</p><hr/><b>{credit} کردیت</b><p>{credit==='۵۰'?'۵۰ کردیت پایه · بدون کردیت هدیه':credit==='۱۵۵'?'۱۵۰ کردیت پایه · ۵ کردیت هدیه':'۳۰۰ کردیت پایه · ۲۱ کردیت هدیه'}</p><em>نمونه ظرفیت: {credit==='۵۰' ? '۵' : credit==='۱۵۵' ? '۱۵' : '۳۲'} ریلز</em><p>با فرض ۱۰ کردیت برای هر ریلز</p></article>)}</div><a className="details" href="#footer">جزئیات تعرفه‌ها</a></div></section>
    <section className="shell telegram"><small>وب + تلگرام</small><h2>خبرهای مهم، مستقیم در تلگرام</h2><p>درخواست همکاری جدید، نزدیک‌شدن پایان مهلت پاسخ، تحویل محتوا و پیام‌های پروژه را در بات ویگو ببین.</p><button className="button">باز کردن بات ویگو</button></section>
    <section className="shell orange"><h2>کریتور، اینفلوئنسر یا صاحب پیج تبلیغاتی هستی؟</h2><p>پروفایلت را بساز، خدماتت را معرفی کن و درخواست‌ها را در داشبوردت ببین.</p><button className="button">ثبت‌نام کریتور</button></section>
    <section className="gray"><div className="section shell faq"><SectionHeading tag="۰۹ / پاسخ‌های کوتاه" title="سوال‌های متداول"/>{faqs.map(([q,a],i)=><article className="faq-row" key={q}><button onClick={()=>setOpen(open===i?null:i)}><b>{q}</b><span>{open===i?'−':'+'}</span></button>{open===i&&<p>{a}</p>}</article>)}</div></section>
    <footer id="footer" className="shell"><h2>VIGO</h2><p>ویگو، فضای مشترک بیزینس‌ها و کریتورها</p><div><a href="#prices">تعرفه‌ها</a><a href="#top">پشتیبانی</a></div></footer>
    <Chatbot />
  </main>;
}

function SectionHeading({tag,title,text}) { return <div className="section-heading"><small>{tag}</small><h2>{title}</h2>{text && <p>{text}</p>}</div> }
