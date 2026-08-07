import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { BillingService, Factura, FacturaDetalle } from '../billing.service';
import { AuthService } from '../../auth/auth.service';

// Semaforo de estado de factura (Sprint S1.13, research.md Decision 1):
// mapeo exhaustivo de los 5 valores de chk_factura_estado.
export function claseEstadoFactura(estado: string): string {
  if (estado === 'vencida' || estado === 'disputada') {
    return 'ah-pill--critico';
  }
  if (estado === 'emitida') {
    return 'ah-pill--atencion';
  }
  if (estado === 'pagada') {
    return 'ah-pill--ok';
  }
  return ''; // 'borrador' -- neutro
}

const ETIQUETAS_ESTADO_FACTURA: Record<string, string> = {
  borrador: 'Borrador',
  emitida: 'Emitida',
  pagada: 'Pagada',
  vencida: 'Vencida',
  disputada: 'Disputada',
};

export function etiquetaEstadoFactura(estado: string): string {
  return ETIQUETAS_ESTADO_FACTURA[estado] ?? estado;
}

const ESTADOS_FACTURA = ['borrador', 'emitida', 'pagada', 'vencida', 'disputada'] as const;
const TAMANO_PAGINA = 10;

@Component({
  selector: 'app-panel-facturas',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-facturas.html',
  styleUrl: './panel-facturas.scss',
})
export class PanelFacturas {
  protected readonly error = signal<string | null>(null);
  protected readonly cargando = signal(false);

  protected readonly facturas = signal<Factura[]>([]);
  protected readonly detalle = signal<FacturaDetalle | null>(null);

  protected readonly aerolineaId = signal('');
  protected readonly periodoInicio = signal('');
  protected readonly periodoFin = signal('');
  protected readonly ultimoCalculo = signal<string | null>(null);

  protected readonly motivoDisputa = signal('');

  protected readonly claseEstadoFactura = claseEstadoFactura;
  protected readonly etiquetaEstadoFactura = etiquetaEstadoFactura;
  protected readonly ESTADOS_FACTURA = ESTADOS_FACTURA;

  // Panel de busqueda + paginacion (S1.14, §3.0) -- sobre la lista ya
  // cargada, mismo criterio que tenants/usuarios.
  protected readonly filtroAerolinea = signal('');
  protected readonly filtroEstado = signal('');
  protected readonly facturasFiltradas = computed(() => {
    const q = this.filtroAerolinea().trim().toLowerCase();
    const estado = this.filtroEstado();
    return this.facturas().filter((f) => {
      const coincideAerolinea = !q || f.aerolinea_id.toLowerCase().includes(q);
      const coincideEstado = !estado || f.estado === estado;
      return coincideAerolinea && coincideEstado;
    });
  });
  protected readonly paginaActual = signal(1);
  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.facturasFiltradas().length / TAMANO_PAGINA)),
  );
  protected readonly facturasPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANO_PAGINA;
    return this.facturasFiltradas().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // Modal de calculo de facturacion -- reemplaza el formulario inline
  // (S1.14, §3.0).
  protected readonly mostrarModalCalcular = signal(false);

  private readonly billingService = inject(BillingService);
  private readonly auth = inject(AuthService);

  // Fase 1 de docs/diseno/PLAN_CORRECCION_MODULOS.md (2026-08-06, D1(a)):
  // role_tenant_admin perdio billing:escribir (la matriz reserva billing
  // a role_billing_officer) -- ocultar "Calcular facturacion", "Emitir
  // factura" y "Disputar factura" para quien no tiene el scope.
  protected readonly puedeEscribir = computed(() =>
    (this.auth.perfil()?.scopes ?? []).includes('billing:escribir'),
  );

  // Hallazgo de UX (pedido directo del usuario, 2026-08-05): la vista no
  // mostraba nada hasta presionar "Cargar facturas" -- listarFacturas()
  // no recibe parametros (el filtro es 100% client-side), asi que no hay
  // motivo para no cargar de entrada, mismo criterio que el resto de
  // paneles (tarifarios, compliance, soporte) desde su propio sprint.
  constructor() {
    this.cargarFacturas();
  }

  protected cargarFacturas(): void {
    this.error.set(null);
    this.billingService.listarFacturas().subscribe({
      next: (respuesta) => this.facturas.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected calcularFacturacion(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.ultimoCalculo.set(null);
    this.billingService
      .calcularFacturacion(
        {
          aerolinea_id: this.aerolineaId(),
          periodo_inicio: this.periodoInicio(),
          periodo_fin: this.periodoFin(),
        },
      )
      .subscribe({
        next: (respuesta) => {
          this.cargando.set(false);
          if (respuesta.factura_id === null) {
            this.ultimoCalculo.set('Sin vuelos en el periodo -- ningun cargo que facturar.');
          } else {
            this.ultimoCalculo.set(
              `Factura ${respuesta.factura_id}: ${respuesta.cargos_calculados} cargo(s) nuevo(s), ` +
                `${respuesta.cargos_ya_existentes} ya facturado(s) antes.`,
            );
            this.mostrarModalCalcular.set(false);
          }
          this.cargarFacturas();
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(this.mensajeDeError(err));
          this.cargando.set(false);
        },
      });
  }

  protected actualizarFiltroAerolinea(valor: string): void {
    this.filtroAerolinea.set(valor);
    this.paginaActual.set(1);
  }

  protected actualizarFiltroEstado(valor: string): void {
    this.filtroEstado.set(valor);
    this.paginaActual.set(1);
  }

  protected paginaAnterior(): void {
    this.paginaActual.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguiente(): void {
    this.paginaActual.update((p) => Math.min(this.totalPaginas(), p + 1));
  }

  protected abrirModalCalcular(): void {
    this.error.set(null);
    this.ultimoCalculo.set(null);
    this.mostrarModalCalcular.set(true);
  }

  protected cerrarModalCalcular(): void {
    this.mostrarModalCalcular.set(false);
  }

  protected verDetalle(facturaId: string): void {
    this.error.set(null);
    this.billingService.obtenerFactura(facturaId).subscribe({
      next: (respuesta) => this.detalle.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected cerrarModalDetalle(): void {
    this.detalle.set(null);
    this.motivoDisputa.set('');
  }

  protected emitirFactura(facturaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.emitirFactura(facturaId).subscribe({
      next: () => {
        this.cargando.set(false);
        this.verDetalle(facturaId);
        this.cargarFacturas();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected disputarFactura(facturaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.disputarFactura(facturaId, this.motivoDisputa()).subscribe({
      next: () => {
        this.cargando.set(false);
        this.motivoDisputa.set('');
        this.verDetalle(facturaId);
        this.cargarFacturas();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  private mensajeDeError(err: HttpErrorResponse): string {
    return typeof err.error?.detail === 'string'
      ? err.error.detail
      : `Error ${err.status}: ${err.message}`;
  }
}
