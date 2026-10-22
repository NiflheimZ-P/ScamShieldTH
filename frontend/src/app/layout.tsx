import type { Metadata } from "next";
import { Inter, Noto_Sans_Thai } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

// Design spec: Inter for Latin, Noto Sans Thai for Thai (Inter has no Thai glyphs).
const inter = Inter({ variable: "--font-inter", subsets: ["latin"], weight: ["400", "500", "600"] });
const thai = Noto_Sans_Thai({ variable: "--font-thai", subsets: ["thai"], weight: ["400", "500", "600"] });

export const metadata: Metadata = {
  title: "ScamShield TH",
  description: "ตรวจข้อความ SMS / LINE / อีเมล ว่าเป็นมิจฉาชีพหรือไม่ พร้อมแหล่งอ้างอิงทางการ",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th" data-theme="light" suppressHydrationWarning>
      <body className={`${inter.variable} ${thai.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
