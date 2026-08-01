import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto (services/gateway/main.py). Ver el comentario
// equivalente en apps/web/src/app/tenants/tenant.service.ts -- se mueve a
// environment.ts cuando exista un build de produccion real.
const API_BASE_URL = 'http://localhost:8000';

export interface PantallaConsultada {
  // string, no number: id Snowflake de 64 bits -- ver el comentario en
  // apps/web/src/app/tenants/tenant.service.ts (hallazgo de S1.1).
  id: string;
  codigo: string;
  plantilla_id: string;
  definicion_json: Record<string, unknown>;
  estado: string;
}

@Injectable({ providedIn: 'root' })
export class PantallaService {
  private readonly http = inject(HttpClient);

  obtenerPorCodigo(codigo: string, tokenJwt: string): Observable<PantallaConsultada> {
    return this.http.get<PantallaConsultada>(`${API_BASE_URL}/fids/pantallas/${codigo}`, {
      headers: { Authorization: `Bearer ${tokenJwt}` },
    });
  }

  enviarHeartbeat(pantallaId: string, tokenJwt: string): Observable<void> {
    return this.http.post<void>(
      `${API_BASE_URL}/fids/pantallas/${pantallaId}/heartbeat`,
      {},
      { headers: { Authorization: `Bearer ${tokenJwt}` } },
    );
  }
}
