import "../styles/globals.css";
import { Navbar } from "../components/layout/Navbar";
import { Footer } from "../components/layout/Footer";
import { Providers } from "../components/layout/Providers";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CineMind AI",
  description: "Discover Movies Through Meaning.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-white">
        <Providers>
          <Navbar />
          <main className="pb-20 pt-6">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
