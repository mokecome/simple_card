import { api } from '../utils/apiClient';

export const login = (username, password) =>
  api.post('/auth/login', { username, password });
