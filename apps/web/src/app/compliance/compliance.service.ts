import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// Sprint S1.19 -- Compliance Hub (M9). Ningun metodo recibe tokenJwt --
// authInterceptor agrega el header Authorization (S1.10/S1.11).
const API_BASE_URL = 'http://localhost:8000';

export interface TipoIncidente {
  id: string;
  codigo: string;
  descripcion: string;
  categoria: string;
}

export interface Incidente {
  id: string;
  tipo_incidente_id: string;
  descripcion: string;
  severidad: string;
  detectado_en: string;
  estado: string;
}

export interface CrearIncidenteRequest {
  tipo_incidente_id: string;
  descripcion: string;
  severidad: string;
  detectado_en: string;
}

export interface PostMortemResumen {
  id: string;
  incidente_ref: string;
  severidad: string;
  estado: string;
  iniciado_en: string;
  publicado_en: string | null;
}

export interface Accion {
  id: string;
  descripcion: string;
  responsable_usuario_id: string;
  estado: string;
  vence_en: string;
  ticket_ref: string | null;
  completada_en: string | null;
}

export interface PostMortemDetalle {
  post_mortem: {
    id: string;
    incidente_ref: string;
    severidad: string;
    estado: string;
    iniciado_en: string;
    causa_raiz: string | null;
    publicado_en: string | null;
    tiempo_resolucion_min: number | null;
  };
  acciones: Accion[];
}

export interface CrearPostMortemRequest {
  incidente_ref: string;
  severidad: string;
  iniciado_en: string;
}

export interface AgregarAccionRequest {
  descripcion: string;
  responsable_usuario_id: string;
  vence_en: string;
  ticket_ref?: string | null;
}

export interface TipoReporteRegulatorio {
  id: string;
  codigo: string;
  nombre: string;
  periodicidad: string;
  autoridad: string;
}

export interface ReporteDgac {
  id: string;
  tipo_reporte_id: string;
  periodo_inicio: string;
  periodo_fin: string;
  contenido_ref: string;
  hash_contenido: string;
  emitido_en: string;
}

export interface RegistrarReporteRequest {
  tipo_reporte_id: string;
  periodo_inicio: string;
  periodo_fin: string;
  contenido_ref: string;
  hash_contenido: string;
}

export interface AccesoAuditor {
  id: string;
  auditor_usuario_id: string;
  inicio: string;
  fin: string;
  motivo: string;
}

export interface OtorgarAccesoRequest {
  auditor_usuario_id: string;
  inicio: string;
  fin: string;
  alcance_json: Record<string, unknown>;
  motivo: string;
}

export interface ControlSoc2 {
  id: string;
  codigo_control: string;
  nombre: string;
  categoria: string;
}

export interface EvidenciaSoc2 {
  id: string;
  control_soc2_id: string;
  periodo_inicio: string;
  periodo_fin: string;
  ruta_artefacto: string;
  hash_artefacto: string;
  generado_en: string;
}

export interface RegistrarEvidenciaRequest {
  control_soc2_id: string;
  periodo_inicio: string;
  periodo_fin: string;
  ruta_artefacto: string;
  hash_artefacto: string;
}

@Injectable({ providedIn: 'root' })
export class ComplianceService {
  private readonly http = inject(HttpClient);

  listarTiposIncidente(): Observable<TipoIncidente[]> {
    return this.http.get<TipoIncidente[]>(`${API_BASE_URL}/compliance/catalogo/tipos-incidente`);
  }

  listarIncidentes(): Observable<Incidente[]> {
    return this.http.get<Incidente[]>(`${API_BASE_URL}/compliance/incidentes`);
  }

  crearIncidente(peticion: CrearIncidenteRequest): Observable<{ incidente_id: string }> {
    return this.http.post<{ incidente_id: string }>(`${API_BASE_URL}/compliance/incidentes`, peticion);
  }

  listarPostMortems(): Observable<PostMortemResumen[]> {
    return this.http.get<PostMortemResumen[]>(`${API_BASE_URL}/compliance/post-mortems`);
  }

  obtenerPostMortem(id: string): Observable<PostMortemDetalle> {
    return this.http.get<PostMortemDetalle>(`${API_BASE_URL}/compliance/post-mortems/${id}`);
  }

  crearPostMortem(peticion: CrearPostMortemRequest): Observable<{ post_mortem_id: string }> {
    return this.http.post<{ post_mortem_id: string }>(`${API_BASE_URL}/compliance/post-mortems`, peticion);
  }

  editarCausaRaiz(id: string, causaRaiz: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE_URL}/compliance/post-mortems/${id}`, {
      causa_raiz: causaRaiz,
    });
  }

  agregarAccion(postMortemId: string, peticion: AgregarAccionRequest): Observable<{ accion_id: string }> {
    return this.http.post<{ accion_id: string }>(
      `${API_BASE_URL}/compliance/post-mortems/${postMortemId}/acciones`,
      peticion,
    );
  }

  completarAccion(postMortemId: string, accionId: string): Observable<void> {
    return this.http.post<void>(
      `${API_BASE_URL}/compliance/post-mortems/${postMortemId}/acciones/${accionId}/completar`,
      {},
    );
  }

  publicarPostMortem(id: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/compliance/post-mortems/${id}/publicar`, {});
  }

  listarTiposReporte(): Observable<TipoReporteRegulatorio[]> {
    return this.http.get<TipoReporteRegulatorio[]>(`${API_BASE_URL}/compliance/catalogo/tipos-reporte`);
  }

  listarReportesDgac(): Observable<ReporteDgac[]> {
    return this.http.get<ReporteDgac[]>(`${API_BASE_URL}/compliance/reportes-dgac`);
  }

  registrarReporte(peticion: RegistrarReporteRequest): Observable<{ reporte_id: string }> {
    return this.http.post<{ reporte_id: string }>(`${API_BASE_URL}/compliance/reportes-dgac`, peticion);
  }

  listarAccesosAuditor(): Observable<AccesoAuditor[]> {
    return this.http.get<AccesoAuditor[]>(`${API_BASE_URL}/compliance/accesos-auditor`);
  }

  otorgarAcceso(peticion: OtorgarAccesoRequest): Observable<{ acceso_id: string }> {
    return this.http.post<{ acceso_id: string }>(`${API_BASE_URL}/compliance/accesos-auditor`, peticion);
  }

  listarControlesSoc2(): Observable<ControlSoc2[]> {
    return this.http.get<ControlSoc2[]>(`${API_BASE_URL}/compliance/catalogo/controles-soc2`);
  }

  listarEvidenciaSoc2(): Observable<EvidenciaSoc2[]> {
    return this.http.get<EvidenciaSoc2[]>(`${API_BASE_URL}/compliance/evidencia-soc2`);
  }

  registrarEvidencia(peticion: RegistrarEvidenciaRequest): Observable<{ evidencia_id: string }> {
    return this.http.post<{ evidencia_id: string }>(`${API_BASE_URL}/compliance/evidencia-soc2`, peticion);
  }
}
