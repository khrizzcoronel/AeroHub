import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// Sprint S1.18 -- RF-I01/RF-I02: forma de respuesta COMUN a los 6
// informes (research.md Decision 2 de specs/020-informes-operativos --
// no hay contrato compartido en el backend, cada modulo repite la misma
// FORMA en su propio Pydantic model; el frontend si comparte un unico
// tipo generico porque aqui no aplica la independencia de modulos de
// negocio de ADR-017).
const API_BASE_URL = 'http://localhost:8000';

export interface InformeSimple<TFila> {
  parametros: Record<string, string>;
  generado_en: string;
  filas: TFila[];
}

export interface GrupoInforme {
  clave: string;
  metricas: Record<string, string | number>;
  subtotal: number;
}

export interface InformeCompuesto {
  parametros: Record<string, string>;
  generado_en: string;
  grupos: GrupoInforme[];
  total: number;
}

// Sprint S1.18-iteracion (2026-08-05) -- panel tactico sobre ClickHouse
// (M7, aerohub_analytics_api), forma distinta a InformeCompuesto porque
// no tiene "parametros"/"generado_en" (esos existen del lado de MonetDB,
// que SI recibe filtros de periodo por request; el snapshot tactico se
// sincroniza aparte, ver tools/sincronizar_analytics_demo.py).
export interface GrupoTactico {
  clave: string;
  subtotal: number;
  metrica_principal: string | null;
}

export interface InformeTactico {
  modulo_codigo: string;
  grupos: GrupoTactico[];
  total_general: number;
  calculado_en: string | null;
}

@Injectable({ providedIn: 'root' })
export class InformeService {
  private readonly http = inject(HttpClient);

  // Metodo generico -- cada modulo pasa su propia ruta de endpoint
  // (`/vuelos/informes/simple`, `/billing/informes/compuesto`, etc.),
  // evitando 12 metodos casi identicos.
  obtenerInformeSimple<TFila>(
    ruta: string,
    filtros: Record<string, string>,
  ): Observable<InformeSimple<TFila>> {
    return this.http.get<InformeSimple<TFila>>(`${API_BASE_URL}${ruta}`, {
      params: this.aParams(filtros),
    });
  }

  obtenerInformeCompuesto(ruta: string, filtros: Record<string, string>): Observable<InformeCompuesto> {
    return this.http.get<InformeCompuesto>(`${API_BASE_URL}${ruta}`, {
      params: this.aParams(filtros),
    });
  }

  obtenerInformeTactico(moduloCodigo: string): Observable<InformeTactico> {
    return this.http.get<InformeTactico>(`${API_BASE_URL}/analytics/tactico/${moduloCodigo}`);
  }

  // Sprint S1.18, research.md Decision 3 -- el CSV se pide al MISMO
  // endpoint con ?formato=csv, nunca un endpoint paralelo. Se navega
  // directo a la URL (con el token via query no aplica -- el usuario ya
  // esta autenticado y el navegador maneja la descarga); para mantener
  // el header Authorization en la descarga se abre en la misma pestaña
  // via un <a> con target _blank no sirve sin el JWT, asi que se arma
  // aqui un blob descargable usando HttpClient (que si agrega el header
  // via authInterceptor).
  descargarCsv(ruta: string, filtros: Record<string, string>): Observable<Blob> {
    return this.http.get(`${API_BASE_URL}${ruta}`, {
      params: this.aParams({ ...filtros, formato: 'csv' }),
      responseType: 'blob',
    });
  }

  private aParams(filtros: Record<string, string>): HttpParams {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== '' && valor !== null && valor !== undefined) {
        params = params.set(clave, valor);
      }
    }
    return params;
  }
}
