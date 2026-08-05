import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// Sprint S1.20 -- Soporte D6. Ningun metodo recibe tokenJwt --
// authInterceptor agrega el header Authorization (S1.10/S1.11).
const API_BASE_URL = 'http://localhost:8000';

export interface CategoriaTicket {
  id: string;
  codigo: string;
  nombre: string;
}

export interface Ticket {
  id: string;
  tenant_id: string;
  categoria_id: string;
  creado_por_usuario_id: string;
  asignado_a_usuario_id: string | null;
  severidad: string;
  estado: string;
  asunto: string;
  creado_en: string;
  primera_respuesta_en: string | null;
  resuelto_en: string | null;
  sla_objetivo_min: number;
}

export interface Mensaje {
  id: string;
  autor_usuario_id: string;
  cuerpo: string;
  enviado_en: string;
  es_interno: boolean;
}

export interface TicketDetalle {
  ticket: Ticket;
  mensajes: Mensaje[];
}

export interface CrearTicketRequest {
  categoria_id: string;
  severidad: 'baja' | 'media' | 'alta' | 'critica';
  asunto: string;
  cuerpo_inicial: string;
}

export interface ResponderTicketRequest {
  cuerpo: string;
  es_interno?: boolean;
}

export interface ArticuloKB {
  id: string;
  titulo: string;
  cuerpo: string;
  version: number;
  publicado_en: string | null;
  etiquetas: string[];
}

export interface PublicarArticuloRequest {
  titulo: string;
  cuerpo: string;
  etiquetas: string[];
}

export interface ItemChangelog {
  id: string;
  modulo_id: string;
  tipo_cambio: string;
  descripcion: string;
}

export interface Changelog {
  id: string;
  version_producto: string;
  resumen: string;
  publicado_en: string;
  items: ItemChangelog[];
}

export interface ItemChangelogRequest {
  modulo_codigo: string;
  tipo_cambio: 'nuevo' | 'mejora' | 'correccion' | 'obsolescencia';
  descripcion: string;
}

export interface PublicarChangelogRequest {
  version_producto: string;
  resumen: string;
  items: ItemChangelogRequest[];
}

@Injectable({ providedIn: 'root' })
export class SoporteService {
  private readonly http = inject(HttpClient);

  listarCategoriasTicket(): Observable<CategoriaTicket[]> {
    return this.http.get<CategoriaTicket[]>(`${API_BASE_URL}/support/catalogo/categorias-ticket`);
  }

  crearTicket(peticion: CrearTicketRequest): Observable<{ ticket_id: string; sla_objetivo_min: number }> {
    return this.http.post<{ ticket_id: string; sla_objetivo_min: number }>(
      `${API_BASE_URL}/support/tickets`,
      peticion,
    );
  }

  listarTickets(estado?: string, severidad?: string): Observable<Ticket[]> {
    const params: Record<string, string> = {};
    if (estado) params['estado'] = estado;
    if (severidad) params['severidad'] = severidad;
    return this.http.get<Ticket[]>(`${API_BASE_URL}/support/tickets`, { params });
  }

  obtenerTicket(id: string): Observable<TicketDetalle> {
    return this.http.get<TicketDetalle>(`${API_BASE_URL}/support/tickets/${id}`);
  }

  responderTicket(
    id: string,
    peticion: ResponderTicketRequest,
  ): Observable<{ mensaje_id: string }> {
    return this.http.post<{ mensaje_id: string }>(
      `${API_BASE_URL}/support/tickets/${id}/mensajes`,
      peticion,
    );
  }

  cambiarEstadoTicket(id: string, estado: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE_URL}/support/tickets/${id}/estado`, { estado });
  }

  publicarArticulo(peticion: PublicarArticuloRequest): Observable<{ articulo_id: string; version: number }> {
    return this.http.post<{ articulo_id: string; version: number }>(
      `${API_BASE_URL}/support/kb/articulos`,
      peticion,
    );
  }

  buscarArticulos(q?: string, etiqueta?: string): Observable<ArticuloKB[]> {
    const params: Record<string, string> = {};
    if (q) params['q'] = q;
    if (etiqueta) params['etiqueta'] = etiqueta;
    return this.http.get<ArticuloKB[]>(`${API_BASE_URL}/support/kb/articulos`, { params });
  }

  publicarChangelog(peticion: PublicarChangelogRequest): Observable<{ changelog_id: string }> {
    return this.http.post<{ changelog_id: string }>(`${API_BASE_URL}/support/changelog`, peticion);
  }

  listarChangelog(): Observable<Changelog[]> {
    return this.http.get<Changelog[]>(`${API_BASE_URL}/support/changelog`);
  }
}
