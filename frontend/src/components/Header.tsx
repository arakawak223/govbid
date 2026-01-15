"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Bell, BellOff, User } from "lucide-react";
import { authApi, setAccessToken, getAccessToken } from "@/lib/api";
import type { User as UserType } from "@/types";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      const token = getAccessToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const userData = await authApi.getMe();
        setUser(userData);
      } catch (error) {
        setAccessToken(null);
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  const handleLogout = () => {
    setAccessToken(null);
    router.push("/login");
  };

  const toggleNotification = async () => {
    if (!user) return;
    try {
      const updated = await authApi.updateNotification(!user.notification_enabled);
      setUser(updated);
    } catch (error) {
      console.error("Failed to update notification settings");
    }
  };

  if (loading) {
    return (
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="h-8 bg-gray-200 animate-pulse rounded w-32"></div>
        </div>
      </header>
    );
  }

  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">GovBid</h1>
            <p className="text-sm text-gray-500">
              九州・山口 入札情報収集システム
            </p>
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <User className="h-4 w-4" />
                  {user.name}
                </div>
                <button
                  onClick={toggleNotification}
                  className="p-2 rounded-md hover:bg-gray-100"
                  title={user.notification_enabled ? "通知ON" : "通知OFF"}
                >
                  {user.notification_enabled ? (
                    <Bell className="h-5 w-5 text-blue-600" />
                  ) : (
                    <BellOff className="h-5 w-5 text-gray-400" />
                  )}
                </button>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md"
                >
                  <LogOut className="h-4 w-4" />
                  ログアウト
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
