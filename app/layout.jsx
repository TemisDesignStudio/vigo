import './globals.css';

export const metadata = { title: 'VIGO | تولید محتوا', description: 'فضای مشترک بیزینس‌ها و کریتور‌ها' };

export default function RootLayout({ children }) {
  return <html lang="fa" dir="rtl"><body suppressHydrationWarning>{children}</body></html>;
}
