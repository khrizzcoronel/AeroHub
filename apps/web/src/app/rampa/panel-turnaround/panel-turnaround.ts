import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Incidencia, RampaService, Tarea, Turnaround } from '../rampa.service';

// Semaforo de turnaround (Sprint S1.12, research.md Decision 2): mapeo
// de presentacion sobre el 'estado' que el backend ya expone --
// 'interrumpido' es la unica senal de desviacion real; un turnaround
// 'en_curso' cuyo fin_previsto ya paso se reclasifica a 'atencion' (el
// refinamiento mas simple calculable sin pedir tiempos reales al
// backend, que hoy no expone esa granularidad).
export function claseEstadoTurnaround(t: Turnaround, ahora: Date): string {
  if (t.estado === 'interrumpido') {
    return 'ah-pill--critico';
  }
  if (t.estado === 'en_curso') {
    return new Date(t.fin_previsto) < ahora ? 'ah-pill--atencion' : 'ah-pill--ok';
  }
  if (t.estado === 'completado') {
    return 'ah-pill--ok';
  }
  return ''; // 'planificado' -- neutro
}

const TAMANO_PAGINA = 10;

// Severidad de incidencia (research.md Decision 3) -- mapeo exhaustivo
// de los 4 valores de chk_incidencia_rampa_severidad. Devuelve la clase
// de ".ah-punto" (celda de tabla), no de ".ah-tira" (la incidencia no es
// la unidad "tira" de esta vista, ver research.md Decision 4).
export function puntoSeveridadIncidencia(severidad: string): string {
  if (severidad === 'alta' || severidad === 'critica') {
    return 'ah-punto--critico';
  }
  if (severidad === 'media') {
    return 'ah-punto--atencion';
  }
  return 'ah-punto'; // 'baja' -- neutro
}

// Estado de una tarea del turnaround -- mismo criterio de ".ah-punto"
// que la severidad, dentro de la tabla de tareas.
export function puntoEstadoTarea(estado: string): string {
  if (estado === 'en_curso' || estado === 'completada') {
    return 'ah-punto--ok';
  }
  if (estado === 'omitida') {
    return 'ah-punto--atencion';
  }
  return 'ah-punto'; // 'pendiente' -- neutro
}

// Sprint S1.11: ya no pide el JWT a mano -- authInterceptor (S1.10) lo
// agrega automaticamente a toda peticion HTTP.
@Component({
  selector: 'app-panel-turnaround',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-turnaround.html',
  styleUrl: './panel-turnaround.scss',
})
export class PanelTurnaround {
  protected readonly error = signal<string | null>(null);
  protected readonly cargando = signal(false);

  protected readonly turnarounds = signal<Turnaround[]>([]);
  protected readonly turnaroundSeleccionadoId = signal<string | null>(null);
  protected readonly tareas = signal<Tarea[]>([]);
  protected readonly incidencias = signal<Incidencia[]>([]);

  protected readonly vueloLlegadaId = signal('');
  protected readonly vueloSalidaId = signal('');
  protected readonly inicioPrevisto = signal('');
  protected readonly finPrevisto = signal('');

  protected readonly tipoTareaId = signal('');
  protected readonly finReal = signal('');

  protected readonly claseEstadoTurnaround = claseEstadoTurnaround;
  protected readonly puntoSeveridadIncidencia = puntoSeveridadIncidencia;
  protected readonly puntoEstadoTarea = puntoEstadoTarea;
  protected readonly ahora = new Date();

  // Panel de busqueda + paginacion (S1.14, §3.0) -- filtra por numero de
  // vuelo de llegada o salida, sobre la lista ya cargada.
  protected readonly filtroTurnaround = signal('');
  protected readonly turnaroundsFiltrados = computed(() => {
    const q = this.filtroTurnaround().trim().toLowerCase();
    if (!q) return this.turnarounds();
    return this.turnarounds().filter(
      (t) =>
        t.numero_vuelo_llegada.toLowerCase().includes(q) ||
        t.numero_vuelo_salida.toLowerCase().includes(q),
    );
  });
  protected readonly paginaActual = signal(1);
  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.turnaroundsFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly turnaroundsPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANO_PAGINA;
    return this.turnaroundsFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // Modal de creacion -- reemplaza el formulario inline (S1.14, §3.0).
  protected readonly mostrarModalCrear = signal(false);

  // Modal "Ver detalles" de un turnaround puntual -- tareas + acciones,
  // reemplaza la seccion que se desplegaba debajo de la tira.
  protected readonly turnaroundViendo = signal<Turnaround | null>(null);

  private readonly rampaService = inject(RampaService);

  protected cargarTurnarounds(): void {
    this.error.set(null);
    this.rampaService.listarTurnarounds().subscribe({
      next: (respuesta) => this.turnarounds.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected crearTurnaround(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.rampaService
      .crearTurnaround({
        vuelo_llegada_id: this.vueloLlegadaId(),
        vuelo_salida_id: this.vueloSalidaId(),
        inicio_previsto: this.aUtcIso(this.inicioPrevisto()),
        fin_previsto: this.aUtcIso(this.finPrevisto()),
      })
      .subscribe({
        next: () => {
          this.cargando.set(false);
          this.mostrarModalCrear.set(false);
          this.cargarTurnarounds();
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(this.mensajeDeError(err));
          this.cargando.set(false);
        },
      });
  }

  protected actualizarFiltroTurnaround(valor: string): void {
    this.filtroTurnaround.set(valor);
    this.paginaActual.set(1);
  }

  protected paginaAnterior(): void {
    this.paginaActual.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguiente(): void {
    this.paginaActual.update((p) => Math.min(this.totalPaginas(), p + 1));
  }

  protected abrirModalCrear(): void {
    this.error.set(null);
    this.mostrarModalCrear.set(true);
  }

  protected cerrarModalCrear(): void {
    this.mostrarModalCrear.set(false);
  }

  protected verDetalles(t: Turnaround): void {
    this.turnaroundViendo.set(t);
    this.seleccionarTurnaround(t.id);
  }

  protected cerrarModalDetalles(): void {
    this.turnaroundViendo.set(null);
    this.turnaroundSeleccionadoId.set(null);
    this.tareas.set([]);
  }

  protected seleccionarTurnaround(turnaroundId: string): void {
    this.turnaroundSeleccionadoId.set(turnaroundId);
    this.cargarTareas();
  }

  private cargarTareas(): void {
    const turnaroundId = this.turnaroundSeleccionadoId();
    if (!turnaroundId) {
      return;
    }
    this.error.set(null);
    this.rampaService.listarTareas(turnaroundId).subscribe({
      next: (respuesta) => this.tareas.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected iniciarTarea(): void {
    const turnaroundId = this.turnaroundSeleccionadoId();
    if (!turnaroundId) {
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    this.rampaService.iniciarTarea(turnaroundId, this.tipoTareaId()).subscribe({
      next: () => {
        this.cargando.set(false);
        this.cargarTareas();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected finalizarTarea(tareaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.rampaService.finalizarTarea(tareaId, this.aUtcIso(this.finReal())).subscribe({
      next: (respuesta) => {
        this.cargando.set(false);
        this.cargarTareas();
        if (respuesta.incidencia_generada) {
          this.cargarIncidencias();
        }
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected cargarIncidencias(): void {
    this.error.set(null);
    this.rampaService.listarIncidencias().subscribe({
      next: (respuesta) => this.incidencias.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  private mensajeDeError(err: HttpErrorResponse): string {
    return typeof err.error?.detail === 'string'
      ? err.error.detail
      : `Error ${err.status}: ${err.message}`;
  }

  // Mismo hallazgo que apps/web/puertas/tablero-puertas.ts: <input
  // type="datetime-local"> no lleva zona horaria y el backend exige
  // tz-aware.
  private aUtcIso(valorLocal: string): string {
    return valorLocal.length === 16 ? `${valorLocal}:00Z` : `${valorLocal}Z`;
  }
}
