"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import type { BidResult, BidResultFilter } from "@/types";
import { resultsApi } from "@/lib/api";

interface ResultExportButtonProps {
  filters: BidResultFilter;
  total: number;
}

export default function ResultExportButton({ filters, total }: ResultExportButtonProps) {
  const [exporting, setExporting] = useState(false);

  const exportToCSV = async () => {
    setExporting(true);
    try {
      const response = await resultsApi.getList(1, Math.max(total, 1000), filters);
      generateCSV(response.items);
    } catch (error) {
      console.error("Failed to fetch results for export:", error);
      alert("エクスポートに失敗しました");
    } finally {
      setExporting(false);
    }
  };

  const generateCSV = (results: BidResult[]) => {
    const headers = [
      "案件名",
      "自治体",
      "カテゴリ",
      "落札企業",
      "勝者ラベル",
      "上限金額",
      "落札金額",
      "結果ページURL",
      "公告URL",
      "抽出根拠",
      "抽出箇所",
      "紐付け",
      "取得日時",
    ];

    const rows = results.map((r) => [
      r.title,
      r.municipality,
      r.category || "",
      r.winning_company,
      r.winner_label || "",
      r.max_amount?.toString() || "",
      r.award_amount?.toString() || "",
      r.result_url,
      r.announcement_url || "",
      r.extract_source,
      r.evidence || "",
      r.match_method === "bid" ? "元案件あり" : "紐付きなし",
      r.scraped_at,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((cell) => {
            const escaped = cell.replace(/"/g, '""');
            return /[,\n"]/.test(cell) ? `"${escaped}"` : escaped;
          })
          .join(",")
      ),
    ].join("\n");

    // Excelで開いたときに文字化けしないようBOMを付ける
    const bom = "\uFEFF";
    const blob = new Blob([bom + csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `govbid_rakusatsu_${new Date().toISOString().split("T")[0]}.csv`
    );
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <button
      onClick={exportToCSV}
      disabled={total === 0 || exporting}
      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {exporting ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          エクスポート中...
        </>
      ) : (
        <>
          <Download className="h-4 w-4" />
          全{total}件をCSVエクスポート
        </>
      )}
    </button>
  );
}
