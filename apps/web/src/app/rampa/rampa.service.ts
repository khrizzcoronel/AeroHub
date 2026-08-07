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

export interface TipoTarea {
  id: string;
  codigo: string;
  nombre: string;
  duracion_estandar_min: number;
}

// Sprint S1.11 (research.md Decision 2, deuda de JWT): ningun metodo
// recibe ya un tokenJwt por parametro -- authInterceptor (S1.10) agrega
// el header Authorization a toda peticion HTTP saliente.
@Injectable({ providedIn: 'root' })
export class RampaService {
  private readonly http = inject(HttpClient);

  listarTurnarounds(): Observable<Turnaround[]> {
    return this.http.get<Turnaround[]>(`${API_BASE_URL}/rampa/turnarounds`);
  }

  crearTurnaround(peticion: CrearTurnaroundRequest): Observable<CrearTurnaroundResponse> {
    return this.http.post<CrearTurnaroundResponse>(`${API_BASE_URL}/rampa/turnarounds`, peticion);
  }

  listarTareas(turnaroundId: string): Observable<Tarea[]> {
    return this.http.get<Tarea[]>(`${API_BASE_URL}/rampa/turnarounds/${turnaroundId}/tareas`);
  }

  iniciarTarea(turnaroundId: string, tipoTareaId: string): Observable<IniciarTareaResponse> {
    return this.http.post<IniciarTareaResponse>(
      `${API_BASE_URL}/rampa/turnarounds/${turnaroundId}/tareas`,
      { tipo_tarea_id: tipoTareaId },
    );
  }

  finalizarTarea(tareaId: string, finReal: string): Observable<FinalizarTareaResponse> {
    return this.http.post<FinalizarTareaResponse>(`${API_BASE_URL}/rampa/tareas/${tareaId}/finalizar`, {
      fin_real: finReal,
    });
  }

  listarIncidencias(): Observable<Incidencia[]> {
    return this.http.get<Incidencia[]>(`${API_BASE_URL}/rampa/incidencias`);
  }

  listarTiposTarea(): Observable<TipoTarea[]> {
    return this.http.get<TipoTarea[]>(`${API_BASE_URL}/rampa/catalogo/tipos-tarea`);
  }
}
