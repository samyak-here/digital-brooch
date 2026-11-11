import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Get Clayed — a Digital Brooch built with Clay",
  description:
    "Paste in a company and watch it get enriched live through Clay's Public API. Built by Samyak Jain with Clay's platform — a working enrichment flow, end to end.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={inter.variable}>{children}</body>
    </html>
  );
}
