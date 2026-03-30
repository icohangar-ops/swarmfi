"use client";

import React from "react";
import { WalletProvider } from "@/lib/wallet";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <WalletProvider>
      <Navbar />
      <main className="min-h-screen pt-16">{children}</main>
      <Footer />
    </WalletProvider>
  );
}
