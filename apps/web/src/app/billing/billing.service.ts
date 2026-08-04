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

// Sprint S1.17 -- tarifarios y conciliacion de pax (RF-T10, RF-O15).
export interface ConceptoCargo {
  id: string;
  codigo: string;
  nombre: string;
  unidad_medida: string;
  base_calculo: string;
}

export interface ConceptoTarifario {
  id: string;
  concepto_cargo_id: string;
  tarifa_unitaria: string;
  monto_minimo: string | null;
  monto_maximo: string | null;
}

export interface Tarifario {
  id: string;
  nombre: string;
  moneda: string;
  vigente_desde: string;
  vigente_hasta: string | null;
  estado: string;
  conceptos: ConceptoTarifario[];
}

export interface CrearTarifarioRequest {
  nombre: string;
  moneda: string;
  vigente_desde: string;
  vigente_hasta: string | null;
}

export interface AgregarConceptoRequest {
  concepto_cargo_id: string;
  tarifa_unitaria: string;
  monto_minimo: string | null;
  monto_maximo: string | null;
}

export interface Conciliacion {
  id: string;
  vuelo_id: string;
  periodo: string;
  pax_reportado_aerolinea: number;
  pax_registrado_sistema: number;
  diferencia: number;
  fuente_reporte: string;
  conciliado_en: string | null;
}

export interface RegistrarConciliacionRequest {
  vuelo_id: string;
  periodo: string;
  pax_reportado_aerolinea: number;
  pax_registrado_sistema: number;
  fuente_reporte: string;
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

  listarConceptosCargo(): Observable<ConceptoCargo[]> {
    return this.http.get<ConceptoCargo[]>(`${API_BASE_URL}/billing/catalogo/conceptos-cargo`);
  }

  listarTarifarios(): Observable<Tarifario[]> {
    return this.http.get<Tarifario[]>(`${API_BASE_URL}/billing/tarifarios`);
  }

  crearTarifario(peticion: CrearTarifarioRequest): Observable<{ tarifario_id: string }> {
    return this.http.post<{ tarifario_id: string }>(`${API_BASE_URL}/billing/tarifarios`, peticion);
  }

  agregarConcepto(
    tarifarioId: string,
    peticion: AgregarConceptoRequest,
  ): Observable<{ tarifario_concepto_id: string }> {
    return this.http.post<{ tarifario_concepto_id: string }>(
      `${API_BASE_URL}/billing/tarifarios/${tarifarioId}/conceptos`,
      peticion,
    );
  }

  activarTarifario(tarifarioId: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/billing/tarifarios/${tarifarioId}/activar`, {});
  }

  listarConciliaciones(): Observable<Conciliacion[]> {
    return this.http.get<Conciliacion[]>(`${API_BASE_URL}/billing/conciliaciones`);
  }

  registrarConciliacion(
    peticion: RegistrarConciliacionRequest,
  ): Observable<{ conciliacion_id: string; diferencia: number }> {
    return this.http.post<{ conciliacion_id: string; diferencia: number }>(
      `${API_BASE_URL}/billing/conciliaciones`,
      peticion,
    );
  }

  conciliar(conciliacionId: string): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/billing/conciliaciones/${conciliacionId}/conciliar`, {});
  }
}
