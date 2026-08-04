import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario equivalente en
// tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface Aerolinea {
  id: string;
  codigo_iata: string;
  codigo_icao: string;
  nombre: string;
}

export interface Aeronave {
  id: string;
  matricula: string;
  aerolinea_id: string;
  fabricante: string;
  modelo: string;
}

export interface TipoVuelo {
  id: string;
  codigo: string;
  descripcion: string;
}

// Reexportado de tenant.service.ts -- el select de aeropuerto de
// origen/destino reusa GET /catalogo/aeropuertos ya existente (research.md
// Decision 2: es una llamada HTTP del frontend, no un import de backend
// entre modulos).
export interface Aeropuerto {
  id: string;
  codigo_iata: string;
  codigo_icao: string;
  nombre: string;
  ciudad: string;
}

export interface AltaVueloRequest {
  aerolinea_id: string;
  aeronave_id: string;
  numero_vuelo: string;
  tipo_vuelo_id: string;
  fecha_operacion: string;
  sentido: string;
  aeropuerto_origen_id: string;
  aeropuerto_destino_id: string;
  sta_utc: string;
  std_utc: string;
  pax_estimado: number | null;
}

export interface AltaVueloResponse {
  vuelo_id: string;
}

export interface VueloConsultado {
  id: string;
  aerolinea_id: string;
  aeronave_id: string;
  numero_vuelo: string;
  tipo_vuelo_id: string;
  fecha_operacion: string;
  sentido: string;
  aeropuerto_origen_id: string;
  aeropuerto_destino_id: string;
  sta_utc: string;
  std_utc: string;
  pax_estimado: number | null;
}

export interface CambiarEstadoRequest {
  codigo_estado_nuevo: string;
  origen_cambio: string;
}

export interface CambiarEstadoResponse {
  vuelo_estado_id: string;
}

@Injectable({ providedIn: 'root' })
export class VueloService {
  private readonly http = inject(HttpClient);

  altaVuelo(peticion: AltaVueloRequest): Observable<AltaVueloResponse> {
    return this.http.post<AltaVueloResponse>(`${API_BASE_URL}/vuelos`, peticion);
  }

  obtenerVuelo(vueloId: string): Observable<VueloConsultado> {
    return this.http.get<VueloConsultado>(`${API_BASE_URL}/vuelos/${vueloId}`);
  }

  cambiarEstadoVuelo(
    vueloId: string,
    peticion: CambiarEstadoRequest,
  ): Observable<CambiarEstadoResponse> {
    return this.http.post<CambiarEstadoResponse>(
      `${API_BASE_URL}/vuelos/${vueloId}/estados`,
      peticion,
    );
  }

  listarAerolineas(): Observable<Aerolinea[]> {
    return this.http.get<Aerolinea[]>(`${API_BASE_URL}/vuelos/catalogo/aerolineas`);
  }

  listarAeronaves(): Observable<Aeronave[]> {
    return this.http.get<Aeronave[]>(`${API_BASE_URL}/vuelos/catalogo/aeronaves`);
  }

  listarTiposVuelo(): Observable<TipoVuelo[]> {
    return this.http.get<TipoVuelo[]>(`${API_BASE_URL}/vuelos/catalogo/tipos-vuelo`);
  }

  // Hallazgo empirico (verificacion en navegador real, S1.15): GET
  // /catalogo/aeropuertos de tenancy exige el scope "tenants:crear" (solo
  // role_platform_admin) -- un rol operativo recibia 403, traducido en
  // logout forzado por el interceptor. Redeclarado en aodb bajo
  // "vuelos:leer".
  listarAeropuertos(): Observable<Aeropuerto[]> {
    return this.http.get<Aeropuerto[]>(`${API_BASE_URL}/vuelos/catalogo/aeropuertos`);
  }
}
