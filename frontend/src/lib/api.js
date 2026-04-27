import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("arq_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const CATEGORIES = [
  { id: "music", label: "Music", tagline: "48kHz · Emotional Math · Creator Equity" },
  { id: "art_visual", label: "Art / Visual", tagline: "Color-managed · Provenance · Owned" },
  { id: "commerce", label: "Commerce", tagline: "Transparent splits · Non-extractive" },
  { id: "community", label: "Community", tagline: "Consent-first · Zero shadow-ban" },
  { id: "storytelling", label: "Storytelling", tagline: "First-person · Oral-history export" },
];
