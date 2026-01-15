"use client";

import { Download } from "lucide-react";
import type { Bid } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";

interface ExportButtonProps {
  bids: Bid[];
}

export default function ExportButton({ bids }: ExportButtonProps) {
  const exportToCSV = () => {
    const headers = [
      "案件タイトル",
      "自治体",
      "カテゴリ",
      "上限金額",
      "公告URL",
      "実施期間（開始）",
      "実施期間（終了）",
      "申込期間（開始）",
      "申込期限",
      "ステータス",
    ];

    const rows = bids.map((bid) => [
      bid.title,
      bid.municipality,
      bid.category || "",
      bid.max_amount?.toString() || "",
      bid.announcement_url,
      bid.period_start || "",
      bid.period_end || "",
      bid.application_start || "",
      bid.application_end || "",
      bid.status,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((cell) => {
            // Escape double quotes and wrap in quotes if contains comma or newline
            const escaped = cell.replace(/"/g, '""');
            return /[,\n"]/.test(cell) ? `"${escaped}"` : escaped;
          })
          .join(",")
      ),
    ].join("\n");

    // Add BOM for Excel to recognize UTF-8
    const bom = "\uFEFF";
    const blob = new Blob([bom + csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `govbid_export_${new Date().toISOString().split("T")[0]}.csv`
    );
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <button
      onClick={exportToCSV}
      disabled={bids.length === 0}
      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <Download className="h-4 w-4" />
      CSVエクスポート
    </button>
  );
}
