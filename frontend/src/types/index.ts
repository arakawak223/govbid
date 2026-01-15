export interface User {
  id: string;
  email: string;
  name: string;
  notification_enabled: boolean;
  created_at: string;
}

export interface Bid {
  id: string;
  title: string;
  municipality: string;
  category: string | null;
  max_amount: number | null;
  announcement_url: string;
  period_start: string | null;
  period_end: string | null;
  application_start: string | null;
  application_end: string | null;
  status: string;
  source_url: string;
  scraped_at: string;
  created_at: string;
  updated_at: string;
}

export interface BidListResponse {
  items: Bid[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface BidFilter {
  municipality?: string;
  category?: string;
  status?: string;
  search?: string;
  min_amount?: number;
  max_amount?: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}
