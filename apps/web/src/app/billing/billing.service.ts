import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario en tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface Factura {
  id: string;
  aerolinea_id: string;
  periodo_inicio: string;
  periodo_fin: string;
  moneda: string;
  estado: string;
  total: string;
  emitida_en: string | null;
  vence_en: string | null;
}

export interface FacturaLinea {
  id: string;
  cargo_aeronautico_id: string;
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  monto: string;
}

export interface FacturaDetalle {
  factura: Factura;
  lineas: FacturaLinea[];
}

export interface CalcularFacturacionRequest {
  aerolinea_id: string;
  periodo_inicio: string;
  periodo_fin: string;
}

export interface CalcularFacturacionResponse {
  factura_id: string | null;
  cargos_calculados: number;
  cargos_ya_existentes: number;
}

@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly http = inject(HttpClient);

  private auth(tokenJwt: string): { headers: { Authorization: string } } {
    return { headers: { Authorization: `Bearer ${tokenJwt}` } };
  }

  listarFacturas(tokenJwt: string): Observable<Factura[]> {
    return this.http.get<Factura[]>(`${API_BASE_URL}/billing/facturas`, this.auth(tokenJwt));
  }

  obtenerFactura(facturaId: string, tokenJwt: string): Observable<FacturaDetalle> {
    return this.http.get<FacturaDetalle>(
      `${API_BASE_URL}/billing/facturas/${facturaId}`,
      this.auth(tokenJwt),
    );
  }

  calcularFacturacion(
    peticion: CalcularFacturacionRequest,
    tokenJwt: string,
  ): Observable<CalcularFacturacionResponse> {
    return this.http.post<CalcularFacturacionResponse>(
      `${API_BASE_URL}/billing/facturacion/calcular`,
      peticion,
      this.auth(tokenJwt),
    );
  }

  emitirFactura(facturaId: string, tokenJwt: string): Observable<void> {
    return this.http.post<void>(
      `${API_BASE_URL}/billing/facturas/${facturaId}/emitir`,
      {},
      this.auth(tokenJwt),
    );
  }

  disputarFactura(facturaId: string, motivo: string, tokenJwt: string): Observable<void> {
    return this.http.post<void>(
      `${API_BASE_URL}/billing/facturas/${facturaId}/disputar`,
      { motivo },
      this.auth(tokenJwt),
    );
  }
}
