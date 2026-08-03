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

// Sprint S1.11 (research.md Decision 2, deuda de JWT): ningun metodo
// recibe ya un tokenJwt por parametro -- authInterceptor (S1.10) agrega
// el header Authorization a toda peticion HTTP saliente.
@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly http = inject(HttpClient);

  listarFacturas(): Observable<Factura[]> {
    return this.http.get<Factura[]>(`${API_BASE_URL}/billing/facturas`);
  }

  obtenerFactura(facturaId: string): Observable<FacturaDetalle> {
    return this.http.get<FacturaDetalle>(`${API_BASE_URL}/billing/facturas/${facturaId}`);
  }

  calcularFacturacion(
    peticion: CalcularFacturacionRequest,
  ): Observable<CalcularFacturacionResponse> {
    return this.http.post<CalcularFacturacionResponse>(
      `${API_BASE_URL}/billing/facturacion/calcular`,
      peticion,
    );
  }

  emitirFactura(facturaId: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/billing/facturas/${facturaId}/emitir`, {});
  }

  disputarFactura(facturaId: string, motivo: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/billing/facturas/${facturaId}/disputar`, {
      motivo,
    });
  }
}
