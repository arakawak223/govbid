"use client";

import { Search, X, Building2 } from "lucide-react";
import type { BidResultFilter } from "@/types";

interface ResultFilterPanelProps {
  filters: BidResultFilter;
  onFilterChange: (filters: BidResultFilter) => void;
  municipalities: string[];
  categories: string[];
}

export default function ResultFilterPanel({
  filters,
  onFilterChange,
  municipalities,
  categories,
}: ResultFilterPanelProps) {
  const handleChange = (key: keyof BidResultFilter, value: string | undefined) => {
    onFilterChange({
      ...filters,
      [key]: value || undefined,
    });
  };

  const clearFilters = () => {
    onFilterChange({});
  };

  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== "");

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* 案件名 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="案件名で検索..."
            value={filters.search || ""}
            onChange={(e) => handleChange("search", e.target.value)}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* 落札企業 */}
        <div className="relative">
          <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="落札企業で検索..."
            value={filters.company || ""}
            onChange={(e) => handleChange("company", e.target.value)}
            title="前株/後株・（株）等の表記揺れを吸収して検索します"
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* 自治体 */}
        <select
          value={filters.municipality || ""}
          onChange={(e) => handleChange("municipality", e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">全ての自治体</option>
          {municipalities.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        {/* カテゴリ */}
        <select
          value={filters.category || ""}
          onChange={(e) => handleChange("category", e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">全てのカテゴリ</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {/* 紐付け */}
        <select
          value={filters.match_method || ""}
          onChange={(e) => handleChange("match_method", e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">全ての紐付け状態</option>
          <option value="bid">元案件と紐付きあり</option>
          <option value="orphan">紐付きなし</option>
        </select>
      </div>

      {hasFilters && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
          >
            <X className="h-4 w-4" />
            フィルターをクリア
          </button>
        </div>
      )}
    </div>
  );
}
