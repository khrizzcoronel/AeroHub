import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import {
  BillingService,
  ConceptoCargo,
  Conciliacion,
  Tarifario,
} from '../billing.service';

// Semaforo de estado de tarifario (Sprint S1.17) -- 3 valores de
// ESTADOS_TARIFARIO (services/billing/aerohub_billing/domain/tarifario.py).
export function claseEstadoTarifario(estado: string): string {
  if (estado === 'vigente') return 'ah-pill--ok';
  if (estado === 'expirado') return 'ah-pill--critico';
  return ''; // 'borrador' -- neutro
}

const ETIQUETAS_ESTADO_TARIFARIO: Record<string, string> = {
  borrador: 'Borrador',
  vigente: 'Vigente',
  expirado: 'Expirado',
};

export function etiquetaEstadoTarifario(estado: string): string {
  return ETIQUETAS_ESTADO_TARIFARIO[estado] ?? estado;
}

@Component({
  selector: 'app-panel-tarifarios',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-tarifarios.html',
  styleUrl: './panel-tarifarios.scss',
})
export class PanelTarifarios {
  private readonly billingService = inject(BillingService);
  private readonly toast = inject(ToastService);
  private readonly auth = inject(AuthService);

  protected readonly claseEstadoTarifario = claseEstadoTarifario;
  protected readonly etiquetaEstadoTarifario = etiquetaEstadoTarifario;

  // Fase 1 de docs/diseno/PLAN_CORRECCION_MODULOS.md (2026-08-06, D1(a)):
  // role_tenant_admin perdio billing:escribir -- ocultar "Nuevo
  // tarifario", "Agregar concepto", "Activar", "Nueva conciliación" y
  // "Conciliar" para quien no tiene el scope.
  protected readonly puedeEscribir = computed(() =>
    (this.auth.perfil()?.scopes ?? []).includes('billing:escribir'),
  );

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  // --- Sección Tarifarios (US1/US2) ---
  protected readonly tarifarios = signal<Tarifario[]>([]);
  protected readonly conceptosCargo = signal<ConceptoCargo[]>([]);
  protected readonly filtroTarifario = signal('');
  protected readonly tarifariosFiltrados = computed(() => {
    const q = this.filtroTarifario().trim().toLowerCase();
    if (!q) return this.tarifarios();
    return this.tarifarios().filter(
      (t) => t.nombre.toLowerCase().includes(q) || t.moneda.toLowerCase().includes(q),
    );
  });

  protected readonly mostrarModalTarifario = signal(false);
  protected readonly nombreTarifario = signal('');
  protected readonly monedaTarifario = signal('');
  protected readonly vigenteDesdeTarifario = signal('');
  protected readonly errorFormularioTarifario = signal<string | null>(null);
  protected readonly guardandoTarifario = signal(false);

  // Ver conceptos de un tarifario (US2) -- expansion vía modal, sin
  // query nueva (los conceptos ya vienen incluidos en el listado).
  protected readonly tarifarioViendoConceptos = signal<Tarifario | null>(null);

  // Agregar concepto (US1) -- modal por tarifario.
  protected readonly tarifarioAgregandoConcepto = signal<Tarifario | null>(null);
  protected readonly conceptoCargoId = signal('');
  protected readonly tarifaUnitaria = signal('');
  protected readonly errorAgregarConcepto = signal<string | null>(null);
  protected readonly agregandoConcepto = signal(false);

  // Activar con aviso de inmutabilidad (US1, FR-003) -- el modal de
  // confirmación se abre ANTES de invocar el endpoint.
  protected readonly tarifarioActivando = signal<Tarifario | null>(null);
  protected readonly errorActivar = signal<string | null>(null);
  protected readonly activando = signal(false);

  // --- Sección Conciliaciones (US3) ---
  protected readonly conciliaciones = signal<Conciliacion[]>([]);
  protected readonly filtroConciliacion = signal('');
  protected readonly conciliacionesFiltradas = computed(() => {
    const q = this.filtroConciliacion().trim().toLowerCase();
    if (!q) return this.conciliaciones();
    return this.conciliaciones().filter(
      (c) => c.vuelo_id.includes(q) || c.periodo.toLowerCase().includes(q),
    );
  });

  protected readonly mostrarModalConciliacion = signal(false);
  protected readonly vueloIdConciliacion = signal('');
  protected readonly periodoConciliacion = signal('');
  protected readonly paxAerolinea = signal<number | null>(null);
  protected readonly paxSistema = signal<number | null>(null);
  protected readonly fuenteReporte = signal('');
  protected readonly errorFormularioConciliacion = signal<string | null>(null);
  protected readonly guardandoConciliacion = signal(false);

  protected readonly conciliando = signal<string | null>(null);
  protected readonly errorConciliar = signal<string | null>(null);

  constructor() {
    this.cargarTodo();
  }

  protected cargarTodo(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.listarTarifarios().subscribe({
      next: (r) => this.tarifarios.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.billingService.listarConceptosCargo().subscribe({
      next: (r) => this.conceptosCargo.set(r),
    });
    this.billingService.listarConciliaciones().subscribe({
      next: (r) => {
        this.conciliaciones.set(r);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected actualizarFiltroTarifario(valor: string): void {
    this.filtroTarifario.set(valor);
  }

  protected actualizarFiltroConciliacion(valor: string): void {
    this.filtroConciliacion.set(valor);
  }

  // --- Tarifarios ---

  protected abrirModalTarifario(): void {
    this.errorFormularioTarifario.set(null);
    this.nombreTarifario.set('');
    this.monedaTarifario.set('');
    this.vigenteDesdeTarifario.set('');
    this.mostrarModalTarifario.set(true);
  }

  protected cerrarModalTarifario(): void {
    this.mostrarModalTarifario.set(false);
  }

  protected crearTarifario(): void {
    this.errorFormularioTarifario.set(null);
    this.guardandoTarifario.set(true);
    this.billingService
      .crearTarifario({
        nombre: this.nombreTarifario(),
        moneda: this.monedaTarifario().toUpperCase(),
        vigente_desde: this.vigenteDesdeTarifario(),
        vigente_hasta: null,
      })
      .subscribe({
        next: () => {
          this.guardandoTarifario.set(false);
          this.mostrarModalTarifario.set(false);
          this.cargarTodo();
          this.toast.mostrar('Tarifario creado como borrador', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioTarifario.set(mensajeDeError(err));
          this.guardandoTarifario.set(false);
        },
      });
  }

  protected verConceptos(t: Tarifario): void {
    this.tarifarioViendoConceptos.set(t);
  }

  protected cerrarModalConceptos(): void {
    this.tarifarioViendoConceptos.set(null);
  }

  protected nombreConceptoDe(conceptoCargoId: string): string {
    const c = this.conceptosCargo().find((item) => item.id === conceptoCargoId);
    return c ? c.nombre : conceptoCargoId;
  }

  protected abrirModalAgregarConcepto(t: Tarifario): void {
    // Cierra el modal de detalles antes de abrir este (mismo criterio que
    // tenant-list: nunca dos modales superpuestos a la vez).
    this.tarifarioViendoConceptos.set(null);
    this.errorAgregarConcepto.set(null);
    this.conceptoCargoId.set('');
    this.tarifaUnitaria.set('');
    this.tarifarioAgregandoConcepto.set(t);
  }

  protected cerrarModalAgregarConcepto(): void {
    this.tarifarioAgregandoConcepto.set(null);
  }

  protected agregarConcepto(): void {
    const t = this.tarifarioAgregandoConcepto();
    if (!t) return;
    this.errorAgregarConcepto.set(null);
    this.agregandoConcepto.set(true);
    this.billingService
      .agregarConcepto(t.id, {
        concepto_cargo_id: this.conceptoCargoId(),
        tarifa_unitaria: this.tarifaUnitaria(),
        monto_minimo: null,
        monto_maximo: null,
      })
      .subscribe({
        next: () => {
          this.agregandoConcepto.set(false);
          this.tarifarioAgregandoConcepto.set(null);
          this.cargarTodo();
          this.toast.mostrar(`Concepto agregado a ${t.nombre}`, 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorAgregarConcepto.set(mensajeDeError(err));
          this.agregandoConcepto.set(false);
        },
      });
  }

  // Activar (US1, FR-003) -- el modal muestra el aviso de inmutabilidad
  // ANTES de invocar el endpoint, nunca activa directo desde la fila.
  protected abrirModalActivar(t: Tarifario): void {
    this.tarifarioViendoConceptos.set(null);
    this.errorActivar.set(null);
    this.tarifarioActivando.set(t);
  }

  protected cerrarModalActivar(): void {
    this.tarifarioActivando.set(null);
  }

  protected confirmarActivacion(): void {
    const t = this.tarifarioActivando();
    if (!t) return;
    this.activando.set(true);
    this.errorActivar.set(null);
    this.billingService.activarTarifario(t.id).subscribe({
      next: () => {
        this.activando.set(false);
        this.tarifarioActivando.set(null);
        this.cargarTodo();
        this.toast.mostrar(`${t.nombre} activado como tarifario vigente`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.errorActivar.set(mensajeDeError(err));
        this.activando.set(false);
      },
    });
  }

  // --- Conciliaciones ---

  protected abrirModalConciliacion(): void {
    this.errorFormularioConciliacion.set(null);
    this.vueloIdConciliacion.set('');
    this.periodoConciliacion.set('');
    this.paxAerolinea.set(null);
    this.paxSistema.set(null);
    this.fuenteReporte.set('');
    this.mostrarModalConciliacion.set(true);
  }

  protected cerrarModalConciliacion(): void {
    this.mostrarModalConciliacion.set(false);
  }

  protected registrarConciliacion(): void {
    this.errorFormularioConciliacion.set(null);
    this.guardandoConciliacion.set(true);
    this.billingService
      .registrarConciliacion({
        vuelo_id: this.vueloIdConciliacion(),
        periodo: this.periodoConciliacion(),
        pax_reportado_aerolinea: this.paxAerolinea() ?? 0,
        pax_registrado_sistema: this.paxSistema() ?? 0,
        fuente_reporte: this.fuenteReporte(),
      })
      .subscribe({
        next: () => {
          this.guardandoConciliacion.set(false);
          this.mostrarModalConciliacion.set(false);
          this.cargarTodo();
          this.toast.mostrar('Conciliación registrada', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioConciliacion.set(mensajeDeError(err));
          this.guardandoConciliacion.set(false);
        },
      });
  }

  // Conciliar (US3) -- el backend re-valida diferencia == 0
  // (DiferenciaNoNula -> 409); la UI solo deshabilita el botón como
  // ayuda visual, research.md Decision 2.
  protected conciliar(c: Conciliacion): void {
    this.conciliando.set(c.id);
    this.errorConciliar.set(null);
    this.billingService.conciliar(c.id).subscribe({
      next: () => {
        this.conciliando.set(null);
        this.cargarTodo();
        this.toast.mostrar(`Conciliación de vuelo ${c.vuelo_id} cerrada`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.errorConciliar.set(mensajeDeError(err));
        this.conciliando.set(null);
      },
    });
  }
}
