"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Play, Loader2 } from "lucide-react";
import { winnerExtractApi } from "@/lib/api";

interface WinnerExtractButtonProps {
  /** 抽出対象を絞り込む自治体（未指定なら全自治体） */
  municipality?: string;
  /** 完了時に一覧を再読み込みする */
  onCompleted?: () => void;
}

/** 公募ページは入札後に削除されることが多く、結果ページの巡回に時間がかかるため進捗はポーリングで見る。 */
export default function WinnerExtractButton({
  municipality,
  onCompleted,
}: WinnerExtractButtonProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [targets, setTargets] = useState<number | null>(null);
  // 実行に立ち会っていない過去ジョブの結果を表示しないためのフラグ
  const wasRunningRef = useRef(false);

  const refreshTargets = useCallback(async () => {
    try {
      const t = await winnerExtractApi.getTargets({ municipality });
      setTargets(t.targets);
    } catch (error) {
      console.error("Failed to load winner extract targets:", error);
    }
  }, [municipality]);

  const refreshStatus = useCallback(async () => {
    try {
      const status = await winnerExtractApi.getStatus();

      if (status.is_running) {
        wasRunningRef.current = true;
        setIsRunning(true);
        setMessage("結果ページを巡回中...");
        return;
      }

      setIsRunning(false);
      if (!wasRunningRef.current) return;
      wasRunningRef.current = false;

      if (status.error) {
        setMessage(`エラー: ${status.error}`);
      } else if (status.result) {
        const r = status.result;
        setMessage(
          `完了: 対象${r.targets}件 / ${r.fetched_pages}ページ巡回 → ` +
            `新規${r.saved}件（重複${r.duplicated}件）`
        );
        refreshTargets();
        onCompleted?.();
      }
    } catch (error) {
      console.error("Winner extract status check failed:", error);
      setIsRunning(false);
    }
  }, [onCompleted, refreshTargets]);

  // 実行中はポーリングする
  useEffect(() => {
    if (!isRunning) return;
    const timer = setInterval(refreshStatus, 5000);
    return () => clearInterval(timer);
  }, [isRunning, refreshStatus]);

  // 初期表示: 対象件数のプレビューと、実行中ジョブへの再接続
  useEffect(() => {
    const init = async () => {
      await refreshTargets();
      await refreshStatus();
    };
    init();
  }, [refreshTargets, refreshStatus]);

  const handleRun = async () => {
    if (isRunning) return;
    wasRunningRef.current = true;
    setIsRunning(true);
    setMessage("落札企業抽出を開始中...");

    try {
      const response = await winnerExtractApi.run({ municipality });
      setMessage(
        response.status === "already_running"
          ? "落札企業抽出は既に実行中です"
          : "結果ページを巡回中..."
      );
    } catch (error) {
      console.error("Winner extraction failed:", error);
      setMessage("エラー: 落札企業抽出の開始に失敗しました");
      setIsRunning(false);
      wasRunningRef.current = false;
    }
  };

  return (
    <div className="flex items-center gap-3">
      {message && (
        <span
          className={`text-sm ${
            message.startsWith("エラー") ? "text-red-600" : "text-green-600"
          }`}
        >
          {message}
        </span>
      )}
      <button
        onClick={handleRun}
        disabled={isRunning}
        title={
          targets !== null
            ? `未確認の対象案件: ${targets}件（公告URLあり・上限金額の条件を満たすもの）`
            : undefined
        }
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-white font-medium transition-colors ${
          isRunning ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
        }`}
      >
        {isRunning ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            抽出中...
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            落札企業を抽出
            {targets !== null && targets > 0 && `（対象${targets}件）`}
          </>
        )}
      </button>
    </div>
  );
}
