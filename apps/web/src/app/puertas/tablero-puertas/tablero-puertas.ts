import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import {
  AsignacionAutomaticaResponse,
  AsignacionTablero,
  PuertaTablero,
  PuertasService,
} from '../puertas.service';
import { ToastService } from '../../shared/toast.service';

// Ocupacion/conflicto de una puerta (Sprint S1.12, research.md
// Decision 1): funcion pura de PRESENTACION sobre las asignaciones ya
// cargadas -- sin pedir nada nuevo al backend. Solapamiento de
// intervalos [inicio_previsto, fin_previsto) entre pares consecutivos
// (ya ordenados por asignacionesPorPuerta) es la senal de conflicto.
export function claseOcupacionPuerta(asignaciones: AsignacionTablero[]): string {
  if (asignaciones.length === 0) {
    return '';
  }
  for (let i = 1; i < asignaciones.length; i++) {
    if (asignaciones[i - 1].fin_previsto > asignaciones[i].inicio_previsto) {
      return 'ah-pill--critico';
    }
  }
  return 'ah-pill--ok';
}

const TAMANO_PAGINA = 10;

// Sprint S1.11: ya no pide el JWT a mano -- authInterceptor (S1.10) lo
// agrega automaticamente a toda peticion HTTP.
@Component({
  selector: 'app-tablero-puertas',
  imports: [CommonModule, FormsModule],
  templateUrl: './tablero-puertas.html',
  styleUrl: './tablero-puertas.scss',
})
export class TableroPuertas {
  protected readonly puertas = signal<PuertaTablero[]>([]);
  protected readonly asignaciones = signal<AsignacionTablero[]>([]);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly resultadoAutomatica = signal<AsignacionAutomaticaResponse | null>(null);

  protected readonly vueloId = signal('');
  protected readonly puertaId = signal('');
  protected readonly inicioPrevisto = signal('');
  protected readonly finPrevisto = signal('');
  protected readonly asignando = signal(false);

  protected readonly claseOcupacionPuerta = claseOcupacionPuerta;

  // Panel de busqueda + paginacion (S1.14, §3.0) -- mismo criterio
  // client-side que tenants/usuarios: sobre la lista ya cargada.
  protected readonly filtroPuerta = signal('');
  protected readonly puertasFiltradas = computed(() => {
    const q = this.filtroPuerta().trim().toLowerCase();
    if (!q) return this.puertas();
    return this.puertas().filter(
      (p) => p.codigo.toLowerCase().includes(q) || p.tipo.toLowerCase().includes(q),
    );
  });
  protected readonly paginaActual = signal(1);
  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.puertasFiltradas().length / TAMANO_PAGINA)),
  );
  protected readonly puertasPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANO_PAGINA;
    return this.puertasFiltradas().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // Modal de asignacion manual -- reemplaza el formulario inline (S1.14,
  // §3.0), mismo criterio que TenantCreation.
  protected readonly mostrarModalAsignar = signal(false);

  // Modal "Ver asignaciones" de una puerta puntual -- reemplaza la tabla
  // anidada dentro de la tira.
  protected readonly puertaViendo = signal<PuertaTablero | null>(null);

  protected readonly asignacionesPorPuerta = computed(() => {
    const mapa = new Map<string, AsignacionTablero[]>();
    for (const asignacion of this.asignaciones()) {
      const lista = mapa.get(asignacion.puerta_id) ?? [];
      lista.push(asignacion);
      mapa.set(asignacion.puerta_id, lista);
    }
    for (const lista of mapa.values()) {
      lista.sort((a, b) => a.inicio_previsto.localeCompare(b.inicio_previsto));
    }
    return mapa;
  });

  private readonly puertasService = inject(PuertasService);
  private readonly toast = inject(ToastService);
  protected readonly cancelando = signal(false);

  protected cargarTablero(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.puertasService.obtenerTablero().subscribe({
      next: (respuesta) => {
        this.puertas.set(respuesta.puertas);
        this.asignaciones.set(respuesta.asignaciones);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected asignar(): void {
    this.asignando.set(true);
    this.error.set(null);
    this.puertasService
      .asignarPuerta({
        vuelo_id: this.vueloId(),
        puerta_id: this.puertaId(),
        inicio_previsto: this.aUtcIso(this.inicioPrevisto()),
        fin_previsto: this.aUtcIso(this.finPrevisto()),
      })
      .subscribe({
        next: () => {
          this.asignando.set(false);
          this.mostrarModalAsignar.set(false);
          this.cargarTablero();
        },
        error: (err: HttpErrorResponse) => {
          // "notificacion de conflicto" (Plan §8.4): el 409 de PN-05 (o
          // cualquier otro rechazo) se muestra tal cual devuelve la API,
          // no un mensaje generico.
          this.error.set(this.mensajeDeError(err));
          this.asignando.set(false);
        },
      });
  }

  protected actualizarFiltroPuerta(valor: string): void {
    this.filtroPuerta.set(valor);
    this.paginaActual.set(1);
  }

  protected paginaAnterior(): void {
    this.paginaActual.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguiente(): void {
    this.paginaActual.update((p) => Math.min(this.totalPaginas(), p + 1));
  }

  protected abrirModalAsignar(): void {
    this.error.set(null);
    this.mostrarModalAsignar.set(true);
  }

  protected cerrarModalAsignar(): void {
    this.mostrarModalAsignar.set(false);
  }

  protected verAsignaciones(p: PuertaTablero): void {
    this.puertaViendo.set(p);
  }

  protected cerrarModalAsignaciones(): void {
    this.puertaViendo.set(null);
  }

  // Sprint S1.15 -- endpoint huerfano de bajo costo (ya existia en el
  // backend desde S1.4).
  protected cancelar(asignacion: AsignacionTablero): void {
    this.cancelando.set(true);
    this.error.set(null);
    this.puertasService.cancelarAsignacion(asignacion.id).subscribe({
      next: () => {
        this.cancelando.set(false);
        this.cerrarModalAsignaciones();
        this.cargarTablero();
        this.toast.mostrar(`Asignación de ${asignacion.puerta_codigo} cancelada`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cancelando.set(false);
      },
    });
  }

  protected ejecutarAutomatica(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.resultadoAutomatica.set(null);
    this.puertasService.ejecutarAsignacionAutomatica().subscribe({
      next: (respuesta) => {
        this.resultadoAutomatica.set(respuesta);
        this.cargando.set(false);
        this.cargarTablero();
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

  // <input type="datetime-local"> devuelve "YYYY-MM-DDTHH:mm" SIN zona --
  // el backend exige tz-aware (aerohub_gates.application.asignar_puerta
  // rechaza un datetime naive con 422; antes de esa validacion, comparar
  // un naive contra los tz-aware que vienen de MonetDB reventaba con
  // TypeError sin siquiera llegar a un error HTTP legible). La etiqueta
  // del campo ya le pide al usuario la hora en UTC -- aqui solo se marca
  // explicitamente como tal.
  private aUtcIso(valorLocal: string): string {
    return valorLocal.length === 16 ? `${valorLocal}:00Z` : `${valorLocal}Z`;
  }
}
