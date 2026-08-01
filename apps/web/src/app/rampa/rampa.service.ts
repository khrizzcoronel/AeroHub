import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario en tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface Turnaround {
  id: string;
  vuelo_llegada_id: string;
  numero_vuelo_llegada: string;
  vuelo_salida_id: string;
  numero_vuelo_salida: string;
  aeronave_id: string;
  inicio_previsto: string;
  fin_previsto: string;
  estado: string;
}

export interface CrearTurnaroundRequest {
  vuelo_llegada_id: string;
  vuelo_salida_id: string;
  inicio_previsto: string;
  fin_previsto: string;
}

export interface CrearTurnaroundResponse {
  turnaround_id: string;
}

export interface Tarea {
  id: string;
  turnaround_id: string;
  tipo_tarea_id: string;
  agente_usuario_id: string;
  inicio_real: string | null;
  fin_real: string | null;
  estado: string;
}

export interface IniciarTareaResponse {
  tarea_id: string;
}

export interface FinalizarTareaResponse {
  tarea_id: string;
  duracion_minutos: number;
  incidencia_generada: boolean;
}

export interface Incidencia {
  id: string;
  tarea_turnaround_id: string;
  tipo_incidencia_codigo: string;
  descripcion: string;
  severidad: string;
  detectada_en: string;
}

@Injectable({ providedIn: 'root' })
export class RampaService {
  private readonly http = inject(HttpClient);

  private auth(tokenJwt: string): { headers: { Authorization: string } } {
    return { headers: { Authorization: `Bearer ${tokenJwt}` } };
  }

  listarTurnarounds(tokenJwt: string): Observable<Turnaround[]> {
    return this.http.get<Turnaround[]>(`${API_BASE_URL}/rampa/turnarounds`, this.auth(tokenJwt));
  }

  crearTurnaround(
    peticion: CrearTurnaroundRequest,
    tokenJwt: string,
  ): Observable<CrearTurnaroundResponse> {
    return this.http.post<CrearTurnaroundResponse>(
      `${API_BASE_URL}/rampa/turnarounds`,
      peticion,
      this.auth(tokenJwt),
    );
  }

  listarTareas(turnaroundId: string, tokenJwt: string): Observable<Tarea[]> {
    return this.http.get<Tarea[]>(
      `${API_BASE_URL}/rampa/turnarounds/${turnaroundId}/tareas`,
      this.auth(tokenJwt),
    );
  }

  iniciarTarea(
    turnaroundId: string,
    tipoTareaId: string,
    tokenJwt: string,
  ): Observable<IniciarTareaResponse> {
    return this.http.post<IniciarTareaResponse>(
      `${API_BASE_URL}/rampa/turnarounds/${turnaroundId}/tareas`,
      { tipo_tarea_id: tipoTareaId },
      this.auth(tokenJwt),
    );
  }

  finalizarTarea(
    tareaId: string,
    finReal: string,
    tokenJwt: string,
  ): Observable<FinalizarTareaResponse> {
    return this.http.post<FinalizarTareaResponse>(
      `${API_BASE_URL}/rampa/tareas/${tareaId}/finalizar`,
      { fin_real: finReal },
      this.auth(tokenJwt),
    );
  }

  listarIncidencias(tokenJwt: string): Observable<Incidencia[]> {
    return this.http.get<Incidencia[]>(`${API_BASE_URL}/rampa/incidencias`, this.auth(tokenJwt));
  }
}
