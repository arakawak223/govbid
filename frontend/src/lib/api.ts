import axios from "axios";
import type {
  User,
  Bid,
  BidListResponse,
  BidFilter,
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

export default api;
