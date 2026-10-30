import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// <img> tags and WebSockets can't send an Authorization header, so the token goes in the URL
export const withToken = (url) => {
  const token = localStorage.getItem('token');
  if (!token) return url;
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
};

const clearSessionAndRedirect = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  if (window.location.pathname !== '/login') window.location.assign('/login');
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLogin = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLogin) {
      clearSessionAndRedirect();
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: (credentials) => api.post('/auth/login', credentials),
  getMe: () => api.get('/auth/me'),
  changePassword: (current_password, new_password) =>
    api.post('/auth/change-password', { current_password, new_password }),
};

export const binService = {
  getAll: () => api.get('/bins'),
  getById: (id) => api.get(`/bins/${id}`),
  create: (data) => api.post('/bins', data),
  update: (id, data) => api.put(`/bins/${id}`, data),
  delete: (id) => api.delete(`/bins/${id}`),
  testCamera: (id) => api.post(`/bins/${id}/test-camera`),
  testCameraUrl: (data) => api.post('/bins/test-camera-url', data),
  startMonitoring: (id) => api.post(`/bins/${id}/start`),
  stopMonitoring: (id) => api.post(`/bins/${id}/stop`),
  getStatus: (id) => api.get(`/bins/${id}/status`),
  getReadings: (id, limit = 50) => api.get(`/bins/${id}/readings?limit=${limit}`),
  updateRoi: (id, data) => api.post(`/bins/${id}/roi`, data),
  getFrameUrl: (id) => withToken(`${API_BASE_URL}/bins/${id}/frame?t=${Date.now()}`),
  getStreamUrl: (id) => withToken(`${API_BASE_URL}/stream/${id}`),
  getEmptyReference: (id) => api.get(`/bins/${id}/empty-reference`),
  captureEmptyReference: (id) => api.post(`/bins/${id}/empty-reference`),
  clearEmptyReference: (id) => api.delete(`/bins/${id}/empty-reference`),
  overrideFill: (id, fill_percentage) => api.post(`/bins/${id}/override`, { fill_percentage }),
  triggerAlert: (id) => api.post(`/bins/${id}/trigger-alert`),
};

export const dashboardService = {
  getStats: () => api.get('/dashboard/stats'),
};

export const analyticsService = {
  getAnalytics: (hours = 24, bin_id = null) => {
    let url = `/analytics?hours=${hours}`;
    if (bin_id) url += `&bin_id=${bin_id}`;
    return api.get(url);
  },
};

export const alertService = {
  getAll: (status = null, bin_id = null) => {
    let url = '/alerts?';
    if (status) url += `status_filter=${status}&`;
    if (bin_id) url += `bin_id=${bin_id}&`;
    return api.get(url);
  },
  getSnapshotUrl: (id) => withToken(`${API_BASE_URL}/alerts/${id}/snapshot`),
};

export const emailSettingsService = {
  get: () => api.get('/email-settings'),
  update: (data) => api.put('/email-settings', data),
  sendTest: (recipient_email) => api.post('/email-settings/test', { recipient_email }),
};

export const systemSettingsService = {
  get: () => api.get('/system-settings'),
  update: (data) => api.put('/system-settings', data),
};

export default api;
