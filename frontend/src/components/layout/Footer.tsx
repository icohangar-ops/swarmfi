import React from "react";
import Link from "next/link";
import { Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card/30 py-8 px-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold text-slate-400">
            SwarmFi
          </span>
          <span className="text-xs text-muted ml-2">
            AI Swarm Intelligence Oracle & Prediction Market
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm text-muted">
          <span>Initia Hackathon — INITIATE 2025</span>
          <Link href="/" className="hover:text-cyan-400 transition-colors">
            Docs
          </Link>
          <Link href="/" className="hover:text-cyan-400 transition-colors">
            GitHub
          </Link>
          <Link href="/" className="hover:text-cyan-400 transition-colors">
            Twitter
          </Link>
        </div>
      </div>
    </footer>
  );
}
