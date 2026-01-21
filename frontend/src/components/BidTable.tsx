"use client";

import { ExternalLink } from "lucide-react";
import type { Bid } from "@/types";
import { formatCurrency, formatDate, formatDateShort, getStatusColor, cn } from "@/lib/utils";

interface BidTableProps {
  bids: Bid[];
  loading?: boolean;
}

export default function BidTable({ bids, loading }: BidTableProps) {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (bids.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        該当する案件がありません
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              案件タイトル
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              自治体
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              上限金額
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              実施期間
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              申込期限
            </th>
            <th className="px-2 py-2 text-left text-xs font-medium text-gray-500">
              詳細
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {bids.map((bid) => (
            <tr key={bid.id} className="hover:bg-gray-50">
              <td className="px-2 py-2 text-sm text-gray-900">
                <div className="max-w-2xl truncate" title={bid.title}>
                  {bid.title}
                </div>
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {bid.municipality}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {formatCurrency(bid.max_amount)}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {bid.period_end ? (
                  <span>
                    {bid.period_start ? formatDate(bid.period_start) : "契約日"}〜{formatDate(bid.period_end)}
                  </span>
                ) : (
                  "-"
                )}
              </td>
              <td className="px-2 py-2 text-xs text-gray-600 whitespace-nowrap">
                {formatDateShort(bid.application_end)}
              </td>
              <td className="px-2 py-2 text-xs whitespace-nowrap">
                <a
                  href={bid.announcement_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
