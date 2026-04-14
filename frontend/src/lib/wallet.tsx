"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useMemo, type ReactNode } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { PhantomWalletName } from "@solana/wallet-adapter-wallets";
import { Connection, clusterApiUrl, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";

interface WalletContextType {
  isConnected: boolean;
  address: string;
  publicKey: PublicKey | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  openWallet: () => void;
  solBalance: number;
  cluster: "devnet" | "mainnet-beta";
  setCluster: (cluster: "devnet" | "mainnet-beta") => void;
  connection: Connection;
}

const WalletContext = createContext<WalletContextType>({
  isConnected: false,
  address: "",
  publicKey: null,
  connect: async () => {},
  disconnect: async () => {},
  openWallet: () => {},
  solBalance: 0,
  cluster: "devnet",
  setCluster: () => {},
  connection: new Connection(clusterApiUrl("devnet")),
});

export function SwarmWalletProvider({ children }: { children: ReactNode }) {
  const wallet = useWallet();
  const [solBalance, setSolBalance] = useState(0);
  const [cluster, setCluster] = useState<"devnet" | "mainnet-beta">("devnet");

  const connection = useMemo(
    () => new Connection(clusterApiUrl(cluster)),
    [cluster]
  );

  const address = wallet.publicKey?.toBase58() ?? "";

  // Fetch SOL balance when connected
  useEffect(() => {
    if (wallet.publicKey && connection) {
      connection
        .getBalance(wallet.publicKey)
        .then((bal) => setSolBalance(bal / LAMPORTS_PER_SOL))
        .catch(() => setSolBalance(0));
    } else {
      setSolBalance(0);
    }
  }, [wallet.publicKey, connection, wallet.connected]);

  const connect = useCallback(async () => {
    try {
      await wallet.connect();
    } catch (err) {
      console.error("Wallet connection failed:", err);
    }
  }, [wallet]);

  const disconnect = useCallback(async () => {
    try {
      await wallet.disconnect();
    } catch (err) {
      console.error("Wallet disconnect failed:", err);
    }
  }, [wallet]);

  const openWallet = useCallback(() => {
    if (!wallet.connected) {
      connect();
    } else {
      wallet.select?.(PhantomWalletName);
    }
  }, [wallet, connect]);

  return (
    <WalletContext.Provider
      value={{
        isConnected: wallet.connected,
        address,
        publicKey: wallet.publicKey ?? null,
        connect,
        disconnect,
        openWallet,
        solBalance,
        cluster,
        setCluster,
        connection,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useSolanaWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useSolanaWallet must be used within WalletProvider");
  return ctx;
}

export function useSolanaAddress() {
  const { address } = useSolanaWallet();
  return address;
}

export function useBalance() {
  const { solBalance } = useSolanaWallet();
  // Approximate USD value
  const solPrice = 175.42; // Mock price
  return {
    balance: solBalance.toFixed(4),
    symbol: "SOL",
    usdValue: (solBalance * solPrice).toFixed(2),
  };
}
