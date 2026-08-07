import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import {
  ArticuloKB,
  CategoriaTicket,
  Changelog,
  ItemChangelogRequest,
  SoporteService,
  Ticket,
  TicketDetalle,
  Transicion,
} from '../soporte.service';

// Sprint S1.20 -- catalogo.modulo (M1-M9) es fijo y ya conocido en todo
// el proyecto (packages/contracts/aerohub_contracts/roles_modulos.py);
// no hay endpoint de catalogo en aerohub_support para esto, y agregar
// uno solo para nombrar 9 valores estaticos seria sobre-ingenieria.
const MODULOS_CHANGELOG: { codigo: string; nombre: string }[] = [
  { codigo: 'M1', nombre: 'AODB' },
  { codigo: 'M2', nombre: 'FIDS Management' },
  { codigo: 'M3', nombre: 'Terminal & Gate Manager' },
  { codigo: 'M4', nombre: 'Ground Operations' },
  { codigo: 'M5', nombre: 'Revenue & Billing' },
  { codigo: 'M6', nombre: 'Passenger Experience' },
  { codigo: 'M7', nombre: 'ETL & Analytics' },
  { codigo: 'M8', nombre: 'Observability' },
  { codigo: 'M9', nombre: 'Compliance Hub' },
];

const TAMANO_PAGINA = 10;

const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  abierto: ['en_progreso'],
  en_progreso: ['esperando_cliente', 'resuelto'],
  esperando_cliente: ['en_progreso'],
  resuelto: ['cerrado'],
  cerrado: [],
};

// Estados reales de la maquina de estados de ticket
// (services/support/aerohub_support/domain/ticket.py::ESTADOS_TICKET).
const ETIQUETAS_ESTADO_TICKET: Record<string, string> = {
  abierto: 'Abierto',
  en_progreso: 'En progreso',
  esperando_cliente: 'Esperando cliente',
  resuelto: 'Resuelto',
  cerrado: 'Cerrado',
};

export function claseEstadoTicket(estado: string): string {
  if (estado === 'cerrado') return 'ah-pill--ok';
  if (estado === 'resuelto') return 'ah-pill--ok';
  if (estado === 'esperando_cliente') return 'ah-pill--atencion';
  if (estado === 'abierto') return 'ah-pill--atencion';
  return ''; // en_progreso: neutro
}

export function etiquetaEstadoTicket(estado: string): string {
  return ETIQUETAS_ESTADO_TICKET[estado] ?? estado;
}

// research.md Decision 3 -- calculado en el cliente a partir de datos
// que ya viajan en TicketResponse, sin campo derivado nuevo en backend.
export function indicadorSla(t: Ticket): { texto: string; vencido: boolean } {
  const inicio = t.primera_respuesta_en ? null : new Date(t.creado_en).getTime();
  if (inicio === null) {
    return { texto: 'Primera respuesta registrada', vencido: false };
  }
  const limiteMs = inicio + t.sla_objetivo_min * 60_000;
  const restanteMin = Math.round((limiteMs - Date.now()) / 60_000);
  if (restanteMin < 0) {
    return { texto: `Vencido hace ${Math.abs(restanteMin)} min`, vencido: true };
  }
  return { texto: `${restanteMin} min restantes`, vencido: false };
}

@Component({
  selector: 'app-panel-soporte',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-soporte.html',
  styleUrl: './panel-soporte.scss',
})
export class PanelSoporte {
  private readonly soporteService = inject(SoporteService);
  private readonly toast = inject(ToastService);
  private readonly authService = inject(AuthService);

  protected readonly indicadorSla = indicadorSla;
  protected readonly claseEstadoTicket = claseEstadoTicket;
  protected readonly etiquetaEstadoTicket = etiquetaEstadoTicket;
  protected readonly modulosChangelog = MODULOS_CHANGELOG;

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly puedeEscribir = computed(() =>
    (this.authService.perfil()?.scopes ?? []).includes('support:escribir'),
  );
  protected readonly esRoleSupport = computed(
    () => this.authService.perfil()?.rol_codigo === 'role_support',
  );
  // research.md Decision 1-bis -- role_platform_admin no tiene tenant,
  // listar_tickets_de_tenant() lanza ContextoTenantAusente/500 para ese
  // rol; se oculta la seccion en vez de llamarla.
  protected readonly esPlatformAdmin = computed(
    () => this.authService.perfil()?.rol_codigo === 'role_platform_admin',
  );

  // --- Tickets ---
  protected readonly categorias = signal<CategoriaTicket[]>([]);
  protected readonly tickets = signal<Ticket[]>([]);
  protected readonly filtroEstado = signal('');
  protected readonly filtroSeveridad = signal('');

  protected readonly mostrarModalTicket = signal(false);
  protected readonly categoriaIdTicket = signal('');
  protected readonly severidadTicket = signal<'baja' | 'media' | 'alta' | 'critica'>('media');
  protected readonly asuntoTicket = signal('');
  protected readonly cuerpoInicialTicket = signal('');
  protected readonly errorFormularioTicket = signal<string | null>(null);
  protected readonly guardandoTicket = signal(false);

  protected readonly detalleTicket = signal<TicketDetalle | null>(null);
  protected readonly cuerpoRespuesta = signal('');
  protected readonly esInternoRespuesta = signal(false);
  protected readonly errorDetalle = signal<string | null>(null);
  protected readonly respondiendo = signal(false);
  protected readonly cambiandoEstado = signal(false);

  // Fase 3/4 de docs/diseno/PLAN_CORRECCION_MODULOS.md (item 8 + item
  // 11): historial de cambios de estado del ticket, junto al hilo de
  // mensajes -- antes de esto el dato existia (auditoria) pero no se
  // exponia en ningun lado.
  protected readonly transiciones = signal<Transicion[]>([]);

  protected readonly transicionesDisponibles = computed(() => {
    const d = this.detalleTicket();
    if (!d) return [];
    return TRANSICIONES_VALIDAS[d.ticket.estado] ?? [];
  });

  protected readonly paginaActualTickets = signal(1);
  protected readonly totalPaginasTickets = computed(() =>
    Math.max(1, Math.ceil(this.tickets().length / TAMANO_PAGINA)),
  );
  protected readonly ticketsPagina = computed(() => {
    const inicio = (this.paginaActualTickets() - 1) * TAMANO_PAGINA;
    return this.tickets().slice(inicio, inicio + TAMANO_PAGINA);
  });
  protected paginaAnteriorTickets(): void {
    this.paginaActualTickets.update((p) => Math.max(1, p - 1));
  }
  protected paginaSiguienteTickets(): void {
    this.paginaActualTickets.update((p) => Math.min(this.totalPaginasTickets(), p + 1));
  }

  // --- Base de conocimientos ---
  protected readonly articulos = signal<ArticuloKB[]>([]);
  protected readonly busquedaTexto = signal('');
  protected readonly busquedaEtiqueta = signal('');

  protected readonly puedeEscribirKB = computed(() => {
    const rol = this.authService.perfil()?.rol_codigo;
    return (
      this.puedeEscribir() && (rol === 'role_support' || rol === 'role_platform_admin')
    );
  });

  protected readonly mostrarModalArticulo = signal(false);
  protected readonly tituloArticulo = signal('');
  protected readonly cuerpoArticulo = signal('');
  protected readonly etiquetasArticulo = signal('');
  protected readonly errorFormularioArticulo = signal<string | null>(null);
  protected readonly guardandoArticulo = signal(false);

  protected readonly paginaActualArticulos = signal(1);
  protected readonly totalPaginasArticulos = computed(() =>
    Math.max(1, Math.ceil(this.articulos().length / TAMANO_PAGINA)),
  );
  protected readonly articulosPagina = computed(() => {
    const inicio = (this.paginaActualArticulos() - 1) * TAMANO_PAGINA;
    return this.articulos().slice(inicio, inicio + TAMANO_PAGINA);
  });
  protected paginaAnteriorArticulos(): void {
    this.paginaActualArticulos.update((p) => Math.max(1, p - 1));
  }
  protected paginaSiguienteArticulos(): void {
    this.paginaActualArticulos.update((p) => Math.min(this.totalPaginasArticulos(), p + 1));
  }

  // --- Changelog ---
  protected readonly changelog = signal<Changelog[]>([]);
  protected readonly puedeEscribirChangelog = computed(
    () => this.puedeEscribir() && this.authService.perfil()?.rol_codigo === 'role_platform_admin',
  );

  protected readonly busquedaChangelog = signal('');
  protected readonly changelogFiltrado = computed(() => {
    const q = this.busquedaChangelog().trim().toLowerCase();
    if (!q) return this.changelog();
    return this.changelog().filter(
      (c) =>
        c.version_producto.toLowerCase().includes(q) ||
        c.resumen.toLowerCase().includes(q) ||
        c.items.some((i) => i.descripcion.toLowerCase().includes(q)),
    );
  });

  protected readonly paginaActualChangelog = signal(1);
  protected readonly totalPaginasChangelog = computed(() =>
    Math.max(1, Math.ceil(this.changelogFiltrado().length / TAMANO_PAGINA)),
  );
  protected readonly changelogPagina = computed(() => {
    const inicio = (this.paginaActualChangelog() - 1) * TAMANO_PAGINA;
    return this.changelogFiltrado().slice(inicio, inicio + TAMANO_PAGINA);
  });
  protected paginaAnteriorChangelog(): void {
    this.paginaActualChangelog.update((p) => Math.max(1, p - 1));
  }
  protected paginaSiguienteChangelog(): void {
    this.paginaActualChangelog.update((p) => Math.min(this.totalPaginasChangelog(), p + 1));
  }
  protected actualizarBusquedaChangelog(valor: string): void {
    this.busquedaChangelog.set(valor);
    this.paginaActualChangelog.set(1);
  }

  protected readonly mostrarModalChangelog = signal(false);
  protected readonly versionProducto = signal('');
  protected readonly resumenChangelog = signal('');
  protected readonly itemsChangelog = signal<ItemChangelogRequest[]>([]);
  protected readonly moduloItemNuevo = signal('M1');
  protected readonly tipoItemNuevo = signal<'nuevo' | 'mejora' | 'correccion' | 'obsolescencia'>(
    'mejora',
  );
  protected readonly descripcionItemNuevo = signal('');
  protected readonly errorFormularioChangelog = signal<string | null>(null);
  protected readonly guardandoChangelog = signal(false);

  constructor() {
    this.cargarTodo();
  }

  protected cargarTodo(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.soporteService.listarCategoriasTicket().subscribe({ next: (r) => this.categorias.set(r) });

    if (!this.esPlatformAdmin()) {
      this.soporteService.listarTickets(this.filtroEstado() || undefined, this.filtroSeveridad() || undefined).subscribe({
        next: (r) => this.tickets.set(r),
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
    }

    this.soporteService.buscarArticulos().subscribe({
      next: (r) => this.articulos.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });

    this.soporteService.listarChangelog().subscribe({
      next: (r) => {
        this.changelog.set(r);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  // --- Tickets ---

  protected recargarTickets(): void {
    this.soporteService
      .listarTickets(this.filtroEstado() || undefined, this.filtroSeveridad() || undefined)
      .subscribe({
        next: (r) => {
          this.tickets.set(r);
          this.paginaActualTickets.set(1);
        },
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
  }

  protected actualizarFiltroEstado(valor: string): void {
    this.filtroEstado.set(valor);
    this.recargarTickets();
  }

  protected actualizarFiltroSeveridad(valor: string): void {
    this.filtroSeveridad.set(valor);
    this.recargarTickets();
  }

  protected nombreCategoriaDe(categoriaId: string): string {
    return this.categorias().find((c) => c.id === categoriaId)?.nombre ?? categoriaId;
  }

  protected abrirModalTicket(): void {
    this.errorFormularioTicket.set(null);
    this.categoriaIdTicket.set('');
    this.severidadTicket.set('media');
    this.asuntoTicket.set('');
    this.cuerpoInicialTicket.set('');
    this.mostrarModalTicket.set(true);
  }

  protected cerrarModalTicket(): void {
    this.mostrarModalTicket.set(false);
  }

  protected crearTicket(): void {
    this.errorFormularioTicket.set(null);
    this.guardandoTicket.set(true);
    this.soporteService
      .crearTicket({
        categoria_id: this.categoriaIdTicket(),
        severidad: this.severidadTicket(),
        asunto: this.asuntoTicket(),
        cuerpo_inicial: this.cuerpoInicialTicket(),
      })
      .subscribe({
        next: () => {
          this.guardandoTicket.set(false);
          this.mostrarModalTicket.set(false);
          this.recargarTickets();
          this.toast.mostrar('Ticket creado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioTicket.set(mensajeDeError(err));
          this.guardandoTicket.set(false);
        },
      });
  }

  protected abrirDetalle(t: Ticket): void {
    this.errorDetalle.set(null);
    this.cuerpoRespuesta.set('');
    this.esInternoRespuesta.set(false);
    this.transiciones.set([]);
    this.soporteService.obtenerTicket(t.id).subscribe({
      next: (r) => this.detalleTicket.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.soporteService.listarTransicionesTicket(t.id).subscribe({
      next: (r) => this.transiciones.set(r),
      // Sin error visible aqui -- el historial es un complemento del
      // hilo, no el dato principal del modal (el mismo criterio que
      // errores silenciosos de catalogos secundarios en otras vistas).
      error: () => this.transiciones.set([]),
    });
  }

  protected cerrarDetalle(): void {
    this.detalleTicket.set(null);
    this.transiciones.set([]);
  }

  protected responder(): void {
    const d = this.detalleTicket();
    if (!d) return;
    this.errorDetalle.set(null);
    this.respondiendo.set(true);
    this.soporteService
      .responderTicket(d.ticket.id, {
        cuerpo: this.cuerpoRespuesta(),
        es_interno: this.esInternoRespuesta(),
      })
      .subscribe({
        next: () => {
          this.respondiendo.set(false);
          this.cuerpoRespuesta.set('');
          this.esInternoRespuesta.set(false);
          this.abrirDetalle(d.ticket);
          this.recargarTickets();
          this.toast.mostrar('Mensaje enviado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorDetalle.set(mensajeDeError(err));
          this.respondiendo.set(false);
        },
      });
  }

  protected cambiarEstado(estadoNuevo: string): void {
    const d = this.detalleTicket();
    if (!d) return;
    this.errorDetalle.set(null);
    this.cambiandoEstado.set(true);
    this.soporteService.cambiarEstadoTicket(d.ticket.id, estadoNuevo).subscribe({
      next: () => {
        this.cambiandoEstado.set(false);
        this.cerrarDetalle();
        this.recargarTickets();
        this.toast.mostrar(`Ticket cambiado a ${estadoNuevo}`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.errorDetalle.set(mensajeDeError(err));
        this.cambiandoEstado.set(false);
      },
    });
  }

  // --- Base de conocimientos ---

  protected buscarArticulos(): void {
    this.soporteService
      .buscarArticulos(this.busquedaTexto() || undefined, this.busquedaEtiqueta() || undefined)
      .subscribe({
        next: (r) => {
          this.articulos.set(r);
          this.paginaActualArticulos.set(1);
        },
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
  }

  protected actualizarBusquedaTexto(valor: string): void {
    this.busquedaTexto.set(valor);
    this.buscarArticulos();
  }

  protected actualizarBusquedaEtiqueta(valor: string): void {
    this.busquedaEtiqueta.set(valor);
    this.buscarArticulos();
  }

  protected abrirModalArticulo(): void {
    this.errorFormularioArticulo.set(null);
    this.tituloArticulo.set('');
    this.cuerpoArticulo.set('');
    this.etiquetasArticulo.set('');
    this.mostrarModalArticulo.set(true);
  }

  protected cerrarModalArticulo(): void {
    this.mostrarModalArticulo.set(false);
  }

  protected publicarArticulo(): void {
    this.errorFormularioArticulo.set(null);
    this.guardandoArticulo.set(true);
    const etiquetas = this.etiquetasArticulo()
      .split(',')
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
    this.soporteService
      .publicarArticulo({
        titulo: this.tituloArticulo(),
        cuerpo: this.cuerpoArticulo(),
        etiquetas,
      })
      .subscribe({
        next: () => {
          this.guardandoArticulo.set(false);
          this.mostrarModalArticulo.set(false);
          this.buscarArticulos();
          this.toast.mostrar('Artículo publicado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioArticulo.set(mensajeDeError(err));
          this.guardandoArticulo.set(false);
        },
      });
  }

  // --- Changelog ---

  protected abrirModalChangelog(): void {
    this.errorFormularioChangelog.set(null);
    this.versionProducto.set('');
    this.resumenChangelog.set('');
    this.itemsChangelog.set([]);
    this.moduloItemNuevo.set('M1');
    this.tipoItemNuevo.set('mejora');
    this.descripcionItemNuevo.set('');
    this.mostrarModalChangelog.set(true);
  }

  protected cerrarModalChangelog(): void {
    this.mostrarModalChangelog.set(false);
  }

  protected agregarItemChangelog(): void {
    if (!this.descripcionItemNuevo().trim()) return;
    this.itemsChangelog.update((items) => [
      ...items,
      {
        modulo_codigo: this.moduloItemNuevo(),
        tipo_cambio: this.tipoItemNuevo(),
        descripcion: this.descripcionItemNuevo(),
      },
    ]);
    this.descripcionItemNuevo.set('');
  }

  protected quitarItemChangelog(indice: number): void {
    this.itemsChangelog.update((items) => items.filter((_, i) => i !== indice));
  }

  protected publicarChangelog(): void {
    this.errorFormularioChangelog.set(null);
    this.guardandoChangelog.set(true);
    this.soporteService
      .publicarChangelog({
        version_producto: this.versionProducto(),
        resumen: this.resumenChangelog(),
        items: this.itemsChangelog(),
      })
      .subscribe({
        next: () => {
          this.guardandoChangelog.set(false);
          this.mostrarModalChangelog.set(false);
          this.soporteService.listarChangelog().subscribe({ next: (r) => this.changelog.set(r) });
          this.toast.mostrar('Changelog publicado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioChangelog.set(mensajeDeError(err));
          this.guardandoChangelog.set(false);
        },
      });
  }
}
