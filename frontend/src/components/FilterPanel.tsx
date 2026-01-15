"use client";

import { Search, X } from "lucide-react";
import type { BidFilter } from "@/types";

interface FilterPanelProps {
  filters: BidFilter;
  onFilterChange: (filters: BidFilter) => void;
  municipalities: string[];
  categories: string[];
}

export default function FilterPanel({
  filters,
  onFilterChange,
  municipalities,
  categories,
}: FilterPanelProps) {
  const handleChange = (key: keyof BidFilter, value: string | number | undefined) => {
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="キーワード検索..."
            value={filters.search || ""}
            onChange={(e) => handleChange("search", e.target.value)}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Municipality */}
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

        {/* Category */}
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

        {/* Status */}
        <select
          value={filters.status || ""}
          onChange={(e) => handleChange("status", e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">全てのステータス</option>
          <option value="募集中">募集中</option>
          <option value="終了">終了</option>
          <option value="不明">不明</option>
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
