"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import ResultTable from "@/components/ResultTable";
import ResultFilterPanel from "@/components/ResultFilterPanel";
import ResultExportButton from "@/components/ResultExportButton";
import WinnerExtractButton from "@/components/WinnerExtractButton";
import Pagination from "@/components/Pagination";
import { bidsApi, resultsApi } from "@/lib/api";
import type { BidResult, BidResultFilter, CompanyRanking } from "@/types";

export default function ResultsPage() {
  const [results, setResults] = useState<BidResult[]>([]);
  const [ranking, setRanking] = useState<CompanyRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<BidResultFilter>({});
  const [municipalities, setMunicipalities] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const response = await resultsApi.getList(page, 20, filters);
      setResults(response.items);
      setTotalPages(response.pages);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to fetch bid results:", error);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  const fetchRanking = useCallback(async () => {
    try {
      setRanking(await resultsApi.getCompanyRanking(10, filters.municipality));
    } catch (error) {
      console.error("Failed to fetch company ranking:", error);
    }
  }, [filters.municipality]);

  const fetchFilters = useCallback(async () => {
    try {
      const [munis, cats] = await Promise.all([
        bidsApi.getMunicipalities(),
        bidsApi.getCategories(),
      ]);
      setMunicipalities(munis);
      setCategories(cats);
    } catch (error) {
      console.error("Failed to fetch filter options:", error);
    }
  }, []);

  useEffect(() => {
    fetchFilters();
  }, [fetchFilters]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  useEffect(() => {
    fetchRanking();
  }, [fetchRanking]);

  const handleFilterChange = (newFilters: BidResultFilter) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleExtractCompleted = useCallback(() => {
    fetchResults();
    fetchRanking();
  }, [fetchResults, fetchRanking]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header showScrapeButton={false} />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-gray-900">落札企業</h2>
            <p className="text-sm text-gray-500">
              公募ページは入札後に削除されることが多いため、自治体サイト内の結果ページを巡回して落札企業を抽出します
            </p>
          </div>
          <WinnerExtractButton
            municipality={filters.municipality}
            onCompleted={handleExtractCompleted}
          />
        </div>

        <ResultFilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          municipalities={municipalities}
          categories={categories}
        />

        {ranking.length > 0 && (
          <div className="bg-white p-4 rounded-lg shadow mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              落札件数ランキング{filters.municipality ? `（${filters.municipality}）` : ""}
            </h3>
            <div className="flex flex-wrap gap-2">
              {ranking.map((r) => (
                <button
                  key={r.company}
                  onClick={() => handleFilterChange({ ...filters, company: r.company })}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 hover:bg-blue-50 hover:text-blue-700"
                >
                  {r.company}
                  <span className="font-medium">{r.count}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow">
          <div className="px-4 py-4 border-b border-gray-200 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              {total > 0 ? `${total}件の落札情報が見つかりました` : ""}
            </div>
            <ResultExportButton filters={filters} total={total} />
          </div>

          <ResultTable results={results} loading={loading} />

          <div className="px-4 py-4 border-t border-gray-200">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={handlePageChange}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
