import axios from "axios";
import type {
  User,
  Bid,
  BidListResponse,
  BidFilter,
  BidResult,
  BidResultListResponse,
  BidResultFilter,
  CompanyRanking,
  LoginCredentials,
  RegisterData,
  Token,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token management
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
};

export const getAccessToken = () => {
  if (!accessToken && typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
};

// Request interceptor to add auth header
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post<User>("/auth/register", data);
    return response.data;
  },

  login: async (credentials: LoginCredentials): Promise<Token> => {
    const formData = new URLSearchParams();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);

    const response = await api.post<Token>("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  updateNotification: async (enabled: boolean): Promise<User> => {
    const response = await api.put<User>("/auth/notification", {
      notification_enabled: enabled,
    });
    return response.data;
  },
};

// Bids API
export const bidsApi = {
  getList: async (
    page: number = 1,
    perPage: number = 20,
    filters?: BidFilter
  ): Promise<BidListResponse> => {
    const params = new URLSearchParams();
    params.append("page", page.toString());
    params.append("per_page", perPage.toString());

    if (filters?.municipality) {
      params.append("municipality", filters.municipality);
    }
    if (filters?.category) {
      params.append("category", filters.category);
    }
    if (filters?.status) {
      params.append("status", filters.status);
    }
    if (filters?.search) {
      params.append("search", filters.search);
    }
    if (filters?.min_amount !== undefined) {
      params.append("min_amount", filters.min_amount.toString());
    }
    if (filters?.max_amount !== undefined) {
      params.append("max_amount", filters.max_amount.toString());
    }

    const response = await api.get<BidListResponse>(`/bids?${params.toString()}`);
    return response.data;
  },

  getById: async (id: string): Promise<Bid> => {
    const response = await api.get<Bid>(`/bids/${id}`);
    return response.data;
  },

  getMunicipalities: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/municipalities");
    return response.data;
  },

  getCategories: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/categories");
    return response.data;
  },
};

// Scraping API
export interface ScrapeStartResult {
  status: "started" | "already_running";
  message: string;
  started_at?: string;
}

export interface ScrapeStatus {
  is_running: boolean;
  started_at: string | null;
  completed_at: string | null;
  result: {
    total_scraped: number;
    total_filtered: number;
    total_new: number;
    municipalities: Record<string, { scraped: number; filtered: number; new: number }>;
    errors: string[];
  } | null;
  error: string | null;
}

export interface ScrapeResult {
  status: string;
  total_new_bids: number;
  results: Array<{
    municipality: string;
    new_bids: number;
    status: string;
    error?: string;
  }>;
}

export const scrapeApi = {
  runAll: async (): Promise<ScrapeStartResult> => {
    const response = await api.post<ScrapeStartResult>("/scrape");
    return response.data;
  },

  getStatus: async (): Promise<ScrapeStatus> => {
    const response = await api.get<ScrapeStatus>("/scrape/status");
    return response.data;
  },

  runSingle: async (municipality: string): Promise<ScrapeResult> => {
    const response = await api.post<ScrapeResult>(`/scrape?municipality=${encodeURIComponent(municipality)}`, null, {
      timeout: 120000, // 2 minutes for single municipality
    });
    return response.data;
  },

  getMunicipalities: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/scrape/municipalities");
    return response.data;
  },
};

// 落札企業抽出 API
export const resultsApi = {
  getList: async (
    page: number = 1,
    perPage: number = 20,
    filters?: BidResultFilter
  ): Promise<BidResultListResponse> => {
    const params = new URLSearchParams();
    params.append("page", page.toString());
    params.append("per_page", perPage.toString());

    if (filters?.municipality) {
      params.append("municipality", filters.municipality);
    }
    if (filters?.category) {
      params.append("category", filters.category);
    }
    if (filters?.company) {
      params.append("company", filters.company);
    }
    if (filters?.search) {
      params.append("search", filters.search);
    }
    if (filters?.match_method) {
      params.append("match_method", filters.match_method);
    }

    const response = await api.get<BidResultListResponse>(
      `/results?${params.toString()}`
    );
    return response.data;
  },

  getById: async (id: string): Promise<BidResult> => {
    const response = await api.get<BidResult>(`/results/${id}`);
    return response.data;
  },

  getForBid: async (bidId: string): Promise<BidResult[]> => {
    const response = await api.get<BidResult[]>(`/bids/${bidId}/results`);
    return response.data;
  },

  getCompanyRanking: async (
    limit: number = 20,
    municipality?: string
  ): Promise<CompanyRanking[]> => {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    if (municipality) {
      params.append("municipality", municipality);
    }
    const response = await api.get<CompanyRanking[]>(
      `/results/companies?${params.toString()}`
    );
    return response.data;
  },
};

export interface WinnerExtractParams {
  municipality?: string;
  min_amount?: number;
  since_days?: number;
  limit?: number;
  max_pages_per_domain?: number;
}

export interface WinnerExtractTargets {
  targets: number;
  min_amount: number;
  municipality: string | null;
  since_days: number | null;
}

export interface WinnerExtractStatus {
  is_running: boolean;
  started_at: string | null;
  completed_at: string | null;
  result: {
    targets: number;
    domains: number;
    fetched_pages: number;
    extracted: number;
    saved: number;
    duplicated: number;
    errors: string[];
  } | null;
  error: string | null;
}

export const winnerExtractApi = {
  getTargets: async (
    params?: WinnerExtractParams
  ): Promise<WinnerExtractTargets> => {
    const query = new URLSearchParams();
    if (params?.municipality) query.append("municipality", params.municipality);
    if (params?.min_amount !== undefined)
      query.append("min_amount", params.min_amount.toString());
    if (params?.since_days !== undefined)
      query.append("since_days", params.since_days.toString());

    const response = await api.get<WinnerExtractTargets>(
      `/winner-extract/targets?${query.toString()}`
    );
    return response.data;
  },

  run: async (
    params?: WinnerExtractParams
  ): Promise<{ status: string; message: string; started_at?: string }> => {
    const response = await api.post("/winner-extract", params ?? {});
    return response.data;
  },

  getStatus: async (): Promise<WinnerExtractStatus> => {
    const response = await api.get<WinnerExtractStatus>("/winner-extract/status");
    return response.data;
  },
};

export default api;
