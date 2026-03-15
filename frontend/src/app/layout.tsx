import type { Metadata } from "next";
import Image from "next/image";
import { Barlow_Condensed, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const barlow = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["300", "400", "700", "900"],
  variable: "--font-barlow",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "NovaStream 24/7 — The Infinite Broadcast",
  description: "Fully autonomous AI-powered television network. Powered by Amazon Nova.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <title>NovaStream 24/7 — The Infinite Broadcast</title>
      </head>
      <body
        className={`${barlow.variable} ${inter.variable} ${jetbrains.variable} antialiased bg-[#080B0F] text-[#C8D6E5]`}
        aria-label="NovaStream App"
      >
        {/* Logo at top left */}
        <div className="flex items-center p-4">
          <Image src="/logo.svg" alt="NovaStream logo, stylized NS in blue" width={40} height={40} priority />
          <span className="ml-3 font-barlow font-black text-xl tracking-[4px] uppercase text-[#C8D6E5]" aria-label="NovaStream brand">NovaStream</span>
        </div>
        {children}
      </body>
    </html>
  );
}
