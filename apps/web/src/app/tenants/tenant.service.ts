import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto (services/gateway/main.py, Sprint S1.1). No hay
// build de produccion todavia (Plan §8.1 solo pide "Angular minimo
// funcional") -- cuando exista, esto se mueve a environment.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface CrearTenantRequest {
  codigo: string;
  razon_social: string;
  // string, no number: son ids Snowflake de 64 bits (aerohub_kernel.
  // generar_id) que superan Number.MAX_SAFE_INTEGER -- un number de JS
  // pierde precision en silencio al serializar/parsear JSON por encima de
  // ese limite (hallazgo empirico de S1.1, reproducido con este mismo
  // formulario contra el backend real). El backend acepta el string y lo
  // parsea con precision completa.
  aeropuerto_id: string;
  plan_id: string;
  email_admin: string;
  nombre_admin: string;
}

export interface CrearTenantResponse {
  // Igual que arriba, en sentido inverso: el backend ya serializa estos
  // campos como string por el mismo motivo.
  tenant_id: string;
  usuario_admin_id: string;
  password_temporal: string;
}

@Injectable({ providedIn: 'root' })
export class TenantService {
  private readonly http = inject(HttpClient);

  crearTenant(peticion: CrearTenantRequest): Observable<CrearTenantResponse> {
    // S1.10: el token ya no viaja por parametro -- lo agrega
    // authInterceptor a partir de la sesion real (FR-029).
    return this.http.post<CrearTenantResponse>(`${API_BASE_URL}/tenants`, peticion);
  }
}
