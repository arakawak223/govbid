"use client";

export default function Header() {
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
        </div>
      </div>
    </header>
  );
}
