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

export interface Aeropuerto {
  id: string;
  codigo_iata: string;
  codigo_icao: string;
  nombre: string;
  ciudad: string;
}

export interface Plan {
  id: string;
  codigo: string;
  nombre: string;
  tarifa_base_mensual: string;
  moneda: string;
}

export interface TenantResumen {
  id: string;
  codigo: string;
  razon_social: string;
  aeropuerto_id: string;
  plan_id: string;
  estado: string;
  es_sandbox: boolean;
}

export interface ActualizarTenantRequest {
  razon_social: string;
  plan_id: string;
  es_sandbox: boolean;
}

// Espejo de domain/tenant.py::ESTADOS_VALIDOS (services/tenancy) -- solo
// para mostrar el estado con su nombre real en el UI, el backend sigue
// siendo quien valida las transiciones.
export const ESTADOS_VALIDOS = ['en_onboarding', 'activo', 'suspendido', 'dado_de_baja'] as const;

// Etiqueta legible para el valor crudo que llega de la base (mismo
// criterio en toda la vista: nunca se muestra el enum tal cual --
// "en_onboarding" en vez de "En onboarding" no comunica nada al usuario
// final). Mapeo exhaustivo sobre ESTADOS_VALIDOS, sin caso ambiguo.
const ETIQUETAS_ESTADO: Record<string, string> = {
  en_onboarding: 'En onboarding',
  activo: 'Activo',
  suspendido: 'Suspendido',
  dado_de_baja: 'Dado de baja',
};

export function etiquetaEstadoTenant(estado: string): string {
  return ETIQUETAS_ESTADO[estado] ?? estado;
}

export interface ValidarDisponibilidadResponse {
  codigo_disponible: boolean;
  codigo_mensaje: string | null;
  email_disponible: boolean;
  email_mensaje: string | null;
}

// Workpanel de tenants (post S1.13): antes solo existia crearTenant --
// ni listar, ni ver detalle, ni editar, ni dar de baja.
@Injectable({ providedIn: 'root' })
export class TenantService {
  private readonly http = inject(HttpClient);

  crearTenant(peticion: CrearTenantRequest): Observable<CrearTenantResponse> {
    // S1.10: el token ya no viaja por parametro -- lo agrega
    // authInterceptor a partir de la sesion real (FR-029).
    return this.http.post<CrearTenantResponse>(`${API_BASE_URL}/tenants`, peticion);
  }

  validarDisponibilidad(codigo?: string, emailAdmin?: string): Observable<ValidarDisponibilidadResponse> {
    const params: Record<string, string> = {};
    if (codigo) params['codigo'] = codigo;
    if (emailAdmin) params['email_admin'] = emailAdmin;
    return this.http.get<ValidarDisponibilidadResponse>(`${API_BASE_URL}/tenants/validar`, { params });
  }

  listarAeropuertos(): Observable<Aeropuerto[]> {
    return this.http.get<Aeropuerto[]>(`${API_BASE_URL}/catalogo/aeropuertos`);
  }

  listarPlanes(): Observable<Plan[]> {
    return this.http.get<Plan[]>(`${API_BASE_URL}/catalogo/planes`);
  }

  listarTenants(): Observable<TenantResumen[]> {
    return this.http.get<TenantResumen[]>(`${API_BASE_URL}/tenants`);
  }

  obtenerTenant(tenantId: string): Observable<TenantResumen> {
    return this.http.get<TenantResumen>(`${API_BASE_URL}/tenants/${tenantId}`);
  }

  actualizarTenant(tenantId: string, peticion: ActualizarTenantRequest): Observable<TenantResumen> {
    return this.http.patch<TenantResumen>(`${API_BASE_URL}/tenants/${tenantId}`, peticion);
  }

  cambiarEstadoTenant(tenantId: string, estadoNuevo: string): Observable<TenantResumen> {
    return this.http.post<TenantResumen>(`${API_BASE_URL}/tenants/${tenantId}/estado`, {
      estado_nuevo: estadoNuevo,
    });
  }
}
