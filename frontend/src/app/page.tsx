"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import BidTable from "@/components/BidTable";
import FilterPanel from "@/components/FilterPanel";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import { bidsApi } from "@/lib/api";
import type { Bid, BidFilter } from "@/types";

export default function Home() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<BidFilter>({});
  const [municipalities, setMunicipalities] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  const fetchBids = useCallback(async () => {
    setLoading(true);
    try {
      const response = await bidsApi.getList(page, 20, filters);
      setBids(response.items);
      setTotalPages(response.pages);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to fetch bids:", error);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

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
    fetchBids();
  }, [fetchBids]);

  const handleFilterChange = (newFilters: BidFilter) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <FilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          municipalities={municipalities}
          categories={categories}
        />

        <div className="bg-white rounded-lg shadow">
          <div className="px-4 py-4 border-b border-gray-200 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              {total > 0 ? `${total}件の案件が見つかりました` : ""}
            </div>
            <ExportButton filters={filters} total={total} />
          </div>

          <BidTable bids={bids} loading={loading} />

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
