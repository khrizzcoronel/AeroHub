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

@Injectable({ providedIn: 'root' })
export class PuertasService {
  private readonly http = inject(HttpClient);

  obtenerTablero(tokenJwt: string): Observable<TableroResponse> {
    return this.http.get<TableroResponse>(`${API_BASE_URL}/puertas/tablero`, {
      headers: { Authorization: `Bearer ${tokenJwt}` },
    });
  }

  asignarPuerta(
    peticion: AsignarPuertaRequest,
    tokenJwt: string,
  ): Observable<AsignarPuertaResponse> {
    return this.http.post<AsignarPuertaResponse>(
      `${API_BASE_URL}/puertas/asignaciones`,
      peticion,
      { headers: { Authorization: `Bearer ${tokenJwt}` } },
    );
  }

  ejecutarAsignacionAutomatica(tokenJwt: string): Observable<AsignacionAutomaticaResponse> {
    return this.http.post<AsignacionAutomaticaResponse>(
      `${API_BASE_URL}/puertas/asignaciones/automatica`,
      {},
      { headers: { Authorization: `Bearer ${tokenJwt}` } },
    );
  }
}
