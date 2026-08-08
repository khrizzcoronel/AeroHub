import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UsuarioResumen {
  id: string;
  email: string;
  nombre: string;
  estado: string;
  creado_en: string;
  ultimo_acceso_en: string | null;
  rol_codigo: string | null;
  rol_nombre: string | null;
  aerolinea_id: string | null;
}

// Roles cuyo alcance de datos depende de una aerolínea concreta
// (hallazgo 3 de la auditoría de la capa operativa, 2026-08-08). Solo
// para estos el workpanel ofrece el selector: asignarle una aerolínea a
// un controlador de operaciones no cambiaría nada, el filtro de
// infrastructure/ solo se aplica a role_airline_coordinator.
export const ROLES_CON_AEROLINEA = ['role_airline_coordinator'] as const;

export interface UsuarioDetalle {
  id: string;
  email: string;
  nombre: string;
  estado: string;
  rol_codigo: string | null;
  rol_nombre: string | null;
  // Hallazgo 3 de la auditoría de la capa operativa (2026-08-08): la
  // aerolínea a la que pertenece el usuario. Solo tiene sentido para
  // role_airline_coordinator, que ve únicamente los vuelos y facturas de
  // esta aerolínea. `null` para el resto (personal del aeropuerto).
  aerolinea_id: string | null;
}

export interface InvitarResponse {
  invitacion_id: string;
  expira_en: string;
}

// Espejo de domain/usuario.py::ESTADOS_VALIDOS_USUARIO (services/tenancy)
// -- solo para mostrar el estado con su nombre real en el UI, el backend
// sigue siendo quien valida las transiciones.
export const ESTADOS_VALIDOS_USUARIO = ['activo', 'suspendido', 'eliminado_logicamente'] as const;

const ETIQUETAS_ESTADO_USUARIO: Record<string, string> = {
  activo: 'Activo',
  suspendido: 'Suspendido',
  eliminado_logicamente: 'Eliminado lógicamente',
};

export function etiquetaEstadoUsuario(estado: string): string {
  return ETIQUETAS_ESTADO_USUARIO[estado] ?? estado;
}

const API_BASE_URL = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class UsuarioService {
  private readonly http = inject(HttpClient);

  listarUsuarios(): Observable<UsuarioResumen[]> {
    return this.http.get<UsuarioResumen[]>(`${API_BASE_URL}/usuarios`);
  }

  invitarUsuario(email: string, rolCodigo: string): Observable<InvitarResponse> {
    return this.http.post<InvitarResponse>(`${API_BASE_URL}/usuarios/invitaciones`, {
      email,
      rol_codigo: rolCodigo,
    });
  }

  obtenerUsuario(usuarioId: string): Observable<UsuarioDetalle> {
    return this.http.get<UsuarioDetalle>(`${API_BASE_URL}/usuarios/${usuarioId}`);
  }

  actualizarRolUsuario(usuarioId: string, rolCodigo: string): Observable<UsuarioDetalle> {
    return this.http.patch<UsuarioDetalle>(`${API_BASE_URL}/usuarios/${usuarioId}`, {
      rol_codigo: rolCodigo,
    });
  }

  // Hallazgo 3 de la auditoría de la capa operativa (2026-08-08): puebla
  // `tenants.usuario.aerolinea_id`. Sin esto un role_airline_coordinator
  // no ve NINGÚN vuelo -- el recorte por aerolínea es fail-closed a
  // propósito. `null` desasigna.
  asignarAerolineaUsuario(
    usuarioId: string,
    aerolineaId: string | null,
  ): Observable<UsuarioDetalle> {
    return this.http.patch<UsuarioDetalle>(`${API_BASE_URL}/usuarios/${usuarioId}/aerolinea`, {
      aerolinea_id: aerolineaId,
    });
  }

  cambiarEstadoUsuario(usuarioId: string, estadoNuevo: string): Observable<UsuarioDetalle> {
    return this.http.post<UsuarioDetalle>(`${API_BASE_URL}/usuarios/${usuarioId}/estado`, {
      estado_nuevo: estadoNuevo,
    });
  }
}
