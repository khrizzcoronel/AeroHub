import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario en tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface TerminalPassenger {
  id: string;
  codigo: string;
  nombre: string;
}

export interface FranjaTiempoEspera {
  franja_inicio: string;
  franja_fin: string;
  minutos_estimados: string;
  // Cantidad de observaciones que respaldan el estimado. El backend nunca
  // publica una franja con muestra_n = 0 (RF-O17: "sin muestras, no se
  // inventa un estimado"), así que siempre es >= 1 -- pero un n bajo sigue
  // siendo evidencia débil y la vista lo muestra tal cual.
  muestra_n: number;
  calculado_en: string;
}

export interface TiemposEsperaResponse {
  terminal_id: string;
  fecha: string;
  franjas: FranjaTiempoEspera[];
}

export interface RecalcularResponse {
  franjas_actualizadas: number;
  franjas_descartadas_por_muestra_insuficiente: number;
}

// M6 Passenger Experience (RF-O17 / CU-O19). El módulo existe en backend
// desde S1.6 pero no tuvo ninguna vista hasta 2026-08-08 -- ver el hallazgo
// 1 de la auditoría de la capa operativa: precisamente por no tener vista,
// nadie ejercitó sus permisos y estuvo inalcanzable para todos los roles.
@Injectable({ providedIn: 'root' })
export class PassengerService {
  private readonly http = inject(HttpClient);

  listarTerminales(): Observable<TerminalPassenger[]> {
    return this.http.get<TerminalPassenger[]>(`${API_BASE_URL}/passenger/catalogo/terminales`);
  }

  obtenerTiemposEspera(terminalId: string, fecha: string): Observable<TiemposEsperaResponse> {
    return this.http.get<TiemposEsperaResponse>(`${API_BASE_URL}/passenger/tiempos-espera`, {
      params: { terminal_id: terminalId, fecha },
    });
  }

  recalcular(
    terminalId: string,
    fecha: string,
    franjaMinutos: number,
  ): Observable<RecalcularResponse> {
    return this.http.post<RecalcularResponse>(
      `${API_BASE_URL}/passenger/tiempos-espera/recalcular`,
      { terminal_id: terminalId, fecha, franja_minutos: franjaMinutos },
    );
  }
}
