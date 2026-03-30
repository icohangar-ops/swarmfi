"use client";

import React, { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface WalletContextType {
  isConnected: boolean;
  address: string;
  initiaAddress: string;
  username: string | null;
  connect: () => void;
  disconnect: () => void;
  openWallet: () => void;
}

const WalletContext = createContext<WalletContextType>({
  isConnected: false,
  address: "",
  initiaAddress: "",
  username: null,
  connect: () => {},
  disconnect: () => {},
  openWallet: () => {},
});

export function WalletProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const [address, setAddress] = useState("");
  const [initiaAddress, setInitiaAddress] = useState("");
  const [username, setUsername] = useState<string | null>(null);

  const connect = useCallback(() => {
    // Demo wallet — simulate connecting
    const demoAddr = "initia1q...x7k2m";
    const demoHex = "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18";
    setIsConnected(true);
    setAddress(demoHex);
    setInitiaAddress(demoAddr);
    setUsername("swarmfi_demo");
  }, []);

  const disconnect = useCallback(() => {
    setIsConnected(false);
    setAddress("");
    setInitiaAddress("");
    setUsername(null);
  }, []);

  const openWallet = useCallback(() => {
    // In production this opens the InterwovenKit wallet modal
    if (!isConnected) connect();
  }, [isConnected, connect]);

  return (
    <WalletContext.Provider
      value={{ isConnected, address, initiaAddress, username, connect, disconnect, openWallet }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useInitiaWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useInitiaWallet must be used within WalletProvider");
  return ctx;
}

export function useInitiaAddress() {
  const { initiaAddress } = useInitiaWallet();
  return initiaAddress;
}

export function useBalance() {
  // Demo balance
  return {
    balance: "24,789.45",
    symbol: "INIT",
    usdValue: "60,736.17",
  };
}
