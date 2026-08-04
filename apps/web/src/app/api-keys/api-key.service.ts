import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ApiKeyResumen {
  id: string;
  prefijo: string;
  estado: string;
  creada_en: string;
  expira_en: string | null;
  rotada_en: string | null;
}

export interface ApiKeyCrearResponse {
  api_key_id: string;
  api_key_en_claro: string;
}

const API_BASE_URL = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class ApiKeyService {
  private readonly http = inject(HttpClient);

  listarApiKeys(): Observable<ApiKeyResumen[]> {
    return this.http.get<ApiKeyResumen[]>(`${API_BASE_URL}/api-keys`);
  }

  crearApiKey(): Observable<ApiKeyCrearResponse> {
    return this.http.post<ApiKeyCrearResponse>(`${API_BASE_URL}/api-keys`, {});
  }

  rotarApiKey(apiKeyId: string): Observable<ApiKeyCrearResponse> {
    return this.http.post<ApiKeyCrearResponse>(`${API_BASE_URL}/api-keys/${apiKeyId}/rotar`, {});
  }

  revocarApiKey(apiKeyId: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/api-keys/${apiKeyId}/revocar`, {});
  }
}
