import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface LicenciaResumen {
  id: string;
  modulo_codigo: string;
  modulo_nombre: string;
  activa_desde: string;
  activa_hasta: string | null;
  es_vigente: boolean;
}

const API_BASE_URL = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class LicenciaService {
  private readonly http = inject(HttpClient);

  listarLicencias(): Observable<LicenciaResumen[]> {
    return this.http.get<LicenciaResumen[]>(`${API_BASE_URL}/licencias/mi-tenant`);
  }
}
