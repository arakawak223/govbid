"use client";

import { useState, useEffect, useCallback } from "react";
import { scrapeApi } from "@/lib/api";

export default function Header() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // Poll for scrape status
  const pollStatus = useCallback(async () => {
    try {
      const status = await scrapeApi.getStatus();

      if (status.is_running) {
        // Still running, continue polling
        setTimeout(pollStatus, 3000);
      } else if (status.result) {
        // Completed successfully
        setResult(`完了: ${status.result.total_new}件の新規入札情報を取得しました`);
        setIsLoading(false);
        // ページをリロードして新しいデータを表示
        setTimeout(() => window.location.reload(), 2000);
      } else if (status.error) {
        // Error occurred
        setResult(`エラー: ${status.error}`);
        setIsLoading(false);
        setTimeout(() => setResult(null), 10000);
      } else {
        // Not running, no result (initial state or already finished)
        setIsLoading(false);
      }
    } catch (error) {
      console.error("Status check failed:", error);
      setIsLoading(false);
    }
  }, []);

  // Check initial status on mount
  useEffect(() => {
    const checkInitialStatus = async () => {
      try {
        const status = await scrapeApi.getStatus();
        if (status.is_running) {
          setIsLoading(true);
          setResult("スクレイピング実行中...");
          pollStatus();
        }
      } catch (error) {
        console.error("Initial status check failed:", error);
      }
    };
    checkInitialStatus();
  }, [pollStatus]);

  const handleScrape = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setResult("スクレイピング開始中...");

    try {
      const response = await scrapeApi.runAll();

      if (response.status === "started") {
        setResult("スクレイピング実行中... (バックグラウンドで処理中)");
        // Start polling for status
        setTimeout(pollStatus, 3000);
      } else if (response.status === "already_running") {
        setResult("スクレイピングは既に実行中です");
        // Start polling for status
        setTimeout(pollStatus, 3000);
      }
    } catch (error: unknown) {
      console.error("Scraping failed:", error);
      let errorMessage = "エラー: スクレイピングに失敗しました";
      if (error && typeof error === "object" && "code" in error) {
        if (error.code === "ECONNABORTED") {
          errorMessage = "エラー: タイムアウトしました。再度お試しください";
        }
      }
      setResult(errorMessage);
      setIsLoading(false);
      setTimeout(() => setResult(null), 10000);
    }
  };

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
            {result && (
              <span className={`text-sm ${result.startsWith("エラー") ? "text-red-600" : "text-green-600"}`}>
                {result}
              </span>
            )}
            <button
              onClick={handleScrape}
              disabled={isLoading}
              className={`px-4 py-2 rounded-md text-white font-medium transition-colors ${
                isLoading
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  取得中...
                </span>
              ) : (
                "入札情報を取得"
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
