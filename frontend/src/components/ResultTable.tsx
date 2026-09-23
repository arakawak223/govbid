"use client";

import { ExternalLink, FileSearch } from "lucide-react";
import type { BidResult } from "@/types";
import { formatCurrency } from "@/lib/utils";

interface ResultTableProps {
  results: BidResult[];
  loading?: boolean;
}

/** 抽出経路のラベル。どの根拠で採ったかが分かると誤検出のレビューがしやすい。 */
const SOURCE_LABEL: Record<string, string> = {
  "crawl:heading": "結果ページ見出し",
  "crawl:table": "結果一覧表",
  "crawl:block": "同一行/ブロック",
};

export default function ResultTable({ results, loading }: ResultTableProps) {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        該当する落札情報がありません
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              案件名
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              自治体
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              落札企業
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              上限金額
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              落札金額
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              カテゴリ
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              抽出根拠
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              リンク
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {results.map((r) => (
            <tr key={r.id} className="hover:bg-gray-50">
              <td className="px-2 py-2 text-sm text-gray-900">
                <div className="max-w-md truncate" title={r.title}>
                  {r.title || "（元案件なし）"}
                </div>
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {r.municipality || "-"}
              </td>
              <td className="px-2 py-2 text-sm font-medium text-gray-900">
                <div className="max-w-xs truncate" title={r.winning_company}>
                  {r.winning_company}
                </div>
                {r.winner_label && (
                  <span className="inline-block mt-0.5 px-1.5 py-0.5 text-[10px] rounded bg-blue-50 text-blue-700">
                    {r.winner_label}
                  </span>
                )}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {formatCurrency(r.max_amount)}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {formatCurrency(r.award_amount)}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {r.category || "-"}
              </td>
              <td className="px-2 py-2 text-xs text-gray-500 whitespace-nowrap">
                <span title={r.evidence || ""}>
                  {SOURCE_LABEL[r.extract_source] || r.extract_source}
                </span>
              </td>
              <td className="px-2 py-2 text-xs whitespace-nowrap">
                <div className="flex items-center gap-2">
                  <a
                    href={r.result_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
                    title="落札情報を検出したページ"
                  >
                    <FileSearch className="h-3.5 w-3.5" />
                    結果
                  </a>
                  {r.announcement_url && (
                    <a
                      href={r.announcement_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-700"
                      title="元の公告ページ（削除済みの場合があります）"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      公告
                    </a>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
