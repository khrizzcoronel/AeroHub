import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario en tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface PuertaTablero {
  id: string;
  terminal_id: string;
  codigo: string;
  tipo: string;
  envergadura_max_m: number;
  tiene_pasarela: boolean;
}

export interface AsignacionTablero {
  id: string;
  puerta_id: string;
  puerta_codigo: string;
  vuelo_id: string;
  numero_vuelo: string;
  inicio_previsto: string;
  fin_previsto: string;
  estado: string;
}

export interface TableroResponse {
  puertas: PuertaTablero[];
  asignaciones: AsignacionTablero[];
}

export interface AsignarPuertaRequest {
  vuelo_id: string;
  puerta_id: string;
  inicio_previsto: string;
  fin_previsto: string;
}

export interface AsignarPuertaResponse {
  asignacion_id: string;
}

export interface AsignacionAutomaticaResponse {
  asignados: string[];
  sin_asignar: string[];
}

export interface Terminal {
  id: string;
  codigo: string;
  nombre: string;
}

export interface CrearTerminalRequest {
  codigo: string;
  nombre: string;
}

export interface CrearPuertaRequest {
  terminal_id: string;
  codigo: string;
  tipo: string;
  envergadura_max_m: number;
  tiene_pasarela: boolean;
}

// Sprint S1.11 (research.md Decision 2, deuda de JWT): ningun metodo
// recibe ya un tokenJwt por parametro -- authInterceptor (S1.10) agrega
// el header Authorization a toda peticion HTTP saliente.
@Injectable({ providedIn: 'root' })
export class PuertasService {
  private readonly http = inject(HttpClient);

  obtenerTablero(): Observable<TableroResponse> {
    return this.http.get<TableroResponse>(`${API_BASE_URL}/puertas/tablero`);
  }

  asignarPuerta(peticion: AsignarPuertaRequest): Observable<AsignarPuertaResponse> {
    return this.http.post<AsignarPuertaResponse>(`${API_BASE_URL}/puertas/asignaciones`, peticion);
  }

  ejecutarAsignacionAutomatica(): Observable<AsignacionAutomaticaResponse> {
    return this.http.post<AsignacionAutomaticaResponse>(
      `${API_BASE_URL}/puertas/asignaciones/automatica`,
      {},
    );
  }

  // Sprint S1.15 -- endpoint huerfano (ya existia en el backend desde
  // S1.4, sin ningun boton que lo invocara).
  cancelarAsignacion(asignacionId: string): Observable<void> {
    return this.http.post<void>(
      `${API_BASE_URL}/puertas/asignaciones/${asignacionId}/cancelar`,
      {},
    );
  }

  // Fase 3/4 de docs/diseno/PLAN_CORRECCION_MODULOS.md -- CRUD de
  // terminal/puerta (backend cerrado en Fase 3, sin ningun consumidor de
  // interfaz hasta Fase 4).
  listarTerminales(): Observable<Terminal[]> {
    return this.http.get<Terminal[]>(`${API_BASE_URL}/puertas/terminales`);
  }

  crearTerminal(peticion: CrearTerminalRequest): Observable<{ terminal_id: string }> {
    return this.http.post<{ terminal_id: string }>(`${API_BASE_URL}/puertas/terminales`, peticion);
  }

  crearPuerta(peticion: CrearPuertaRequest): Observable<{ puerta_id: string }> {
    return this.http.post<{ puerta_id: string }>(`${API_BASE_URL}/puertas`, peticion);
  }

  editarPuerta(puertaId: string, peticion: CrearPuertaRequest): Observable<void> {
    return this.http.patch<void>(`${API_BASE_URL}/puertas/${puertaId}`, peticion);
  }
}
