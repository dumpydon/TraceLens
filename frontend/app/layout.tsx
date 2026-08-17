import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { BackendRuntimeProvider } from "@/components/backend-runtime-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "TraceLens",
  description: "Evidence-first incident investigation",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body>
        <BackendRuntimeProvider>
          <AppShell>{children}</AppShell>
        </BackendRuntimeProvider>
      </body>
    </html>
  );
}
