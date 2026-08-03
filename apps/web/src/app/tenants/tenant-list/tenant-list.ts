import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { TenantCreation } from '../tenant-creation/tenant-creation';
import {
  ESTADOS_VALIDOS,
  Plan,
  TenantResumen,
  TenantService,
  etiquetaEstadoTenant,
} from '../tenant.service';

// Transiciones validas -- espejo de domain/tenant.py::_TRANSICIONES_VALIDAS
// (services/tenancy/aerohub_tenancy/domain/tenant.py). Se repite aqui
// SOLO para no ofrecer en el UI un boton que el backend va a rechazar
// con 422 -- el backend sigue siendo la unica fuente de verdad que
// valida de verdad (domain/tenant.py::validar_transicion_estado).
const TRANSICIONES: Record<string, string[]> = {
  en_onboarding: ['activo', 'dado_de_baja'],
  activo: ['suspendido', 'dado_de_baja'],
  suspendido: ['activo', 'dado_de_baja'],
  dado_de_baja: [],
};

const TAMANO_PAGINA = 10;

// Semaforo de estado de tenant -- mismo criterio que factura/turnaround
// (S1.12/S1.13): mapeo de presentacion puro sobre un catalogo cerrado.
// Devuelve la clase de .ah-pill (insignia solida de columna de tabla),
// no de .ah-tira -- esta vista pasa a ser una tabla de columnas, no una
// lista de tiras (pedido explicito: distribucion tipo tabla con estado
// como insignia de color).
// Se combina con el `class="ah-pill"` estatico del template -- este
// mapeo solo agrega el modificador de color, igual patron que
// [class]="claseOcupacionPuerta(...)" ya usa sobre class="ah-tira".
export function claseEstadoTenant(estado: string): string {
  if (estado === 'activo') return 'ah-pill--ok';
  if (estado === 'suspendido') return 'ah-pill--atencion';
  if (estado === 'dado_de_baja') return 'ah-pill--critico';
  return ''; // 'en_onboarding' -- neutro (color base de .ah-pill)
}

@Component({
  selector: 'app-tenant-list',
  imports: [CommonModule, FormsModule, TenantCreation],
  templateUrl: './tenant-list.html',
  styleUrl: './tenant-list.scss',
})
export class TenantList {
  protected readonly ESTADOS_VALIDOS = ESTADOS_VALIDOS;
  protected readonly claseEstadoTenant = claseEstadoTenant;
  protected readonly etiquetaEstadoTenant = etiquetaEstadoTenant;

  protected readonly tenants = signal<TenantResumen[]>([]);
  protected readonly planes = signal<Plan[]>([]);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  // Panel de busqueda -- filtro en vivo sobre la lista ya cargada (mismo
  // criterio que la paginacion: sin pedir nada nuevo al backend). Codigo
  // se compara sin distinguir mayusculas/minusculas, "Todas" en estado
  // no filtra.
  protected readonly filtroCodigo = signal('');
  protected readonly filtroEstado = signal('');
  protected readonly tenantsFiltrados = computed(() => {
    const codigo = this.filtroCodigo().trim().toLowerCase();
    const estado = this.filtroEstado();
    return this.tenants().filter((t) => {
      const coincideCodigo = !codigo || t.codigo.toLowerCase().includes(codigo);
      const coincideEstado = !estado || t.estado === estado;
      return coincideCodigo && coincideEstado;
    });
  });

  // Paginacion (10 en 10) -- puramente de presentacion sobre la lista ya
  // filtrada: GET /tenants no pagina todavia del lado del backend, no hay
  // tantos tenants hoy como para que importe el costo de traerlos todos
  // de una vez; si la cantidad real crece, esto se mueve a query params
  // page/page_size en el backend sin cambiar la interaccion del usuario.
  protected readonly paginaActual = signal(1);
  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.tenantsFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly tenantsPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANO_PAGINA;
    return this.tenantsFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // Modal de creacion -- reemplaza la navegacion a /tenants/nuevo
  // (pedido explicito del usuario).
  protected readonly mostrarModalCrear = signal(false);

  // Modal de edicion -- reemplaza la expansion inline dentro de la tira.
  protected readonly tenantEditando = signal<TenantResumen | null>(null);
  protected readonly razonSocialEdit = signal('');
  protected readonly planIdEdit = signal('');
  protected readonly esSandboxEdit = signal(false);

  private readonly tenantService = inject(TenantService);

  constructor() {
    this.cargarTenants();
    this.tenantService.listarPlanes().subscribe({ next: (r) => this.planes.set(r) });
  }

  protected cargarTenants(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.tenantService.listarTenants().subscribe({
      next: (respuesta) => {
        this.tenants.set(respuesta);
        this.paginaActual.set(1);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected actualizarFiltroCodigo(valor: string): void {
    this.filtroCodigo.set(valor);
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

  protected abrirModalCrear(): void {
    this.mostrarModalCrear.set(true);
  }

  protected cerrarModalCrear(): void {
    this.mostrarModalCrear.set(false);
    this.cargarTenants();
  }

  protected transicionesDisponibles(estado: string): string[] {
    return TRANSICIONES[estado] ?? [];
  }

  protected editar(t: TenantResumen): void {
    this.tenantEditando.set(t);
    this.razonSocialEdit.set(t.razon_social);
    this.planIdEdit.set(t.plan_id);
    this.esSandboxEdit.set(t.es_sandbox);
  }

  protected cerrarModalEditar(): void {
    this.tenantEditando.set(null);
  }

  protected guardarEdicion(): void {
    const tenantId = this.tenantEditando()?.id;
    if (!tenantId) return;
    this.error.set(null);
    this.tenantService
      .actualizarTenant(tenantId, {
        razon_social: this.razonSocialEdit(),
        plan_id: this.planIdEdit(),
        es_sandbox: this.esSandboxEdit(),
      })
      .subscribe({
        next: () => {
          this.tenantEditando.set(null);
          this.cargarTenants();
        },
        error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
      });
  }

  // Se llama desde dentro del modal de "Ver detalles" -- unico lugar
  // desde donde ahora se cambia el estado (pedido explicito: un solo
  // boton por fila, todo lo demas vive en el modal). Cierra el modal
  // porque `t` (el snapshot con el que se abrio) queda desactualizado en
  // cuanto el estado cambia.
  protected cambiarEstadoDesdeModal(tenantId: string, estadoNuevo: string): void {
    this.error.set(null);
    this.tenantService.cambiarEstadoTenant(tenantId, estadoNuevo).subscribe({
      next: () => {
        this.tenantEditando.set(null);
        this.cargarTenants();
      },
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected nombrePlan(planId: string): string {
    return this.planes().find((p) => p.id === planId)?.nombre ?? planId;
  }

  private mensajeDeError(err: HttpErrorResponse): string {
    return typeof err.error?.detail === 'string'
      ? err.error.detail
      : `Error ${err.status}: ${err.message}`;
  }
}
