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

// Sin login real todavia (mismo estado que el resto de apps/web) -- el
// token JWT se pega a mano.
@Component({
  selector: 'app-tablero-puertas',
  imports: [CommonModule, FormsModule],
  templateUrl: './tablero-puertas.html',
})
export class TableroPuertas {
  protected readonly tokenJwt = signal('');
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

  protected cargarTablero(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.puertasService.obtenerTablero(this.tokenJwt()).subscribe({
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
      .asignarPuerta(
        {
          vuelo_id: this.vueloId(),
          puerta_id: this.puertaId(),
          inicio_previsto: this.aUtcIso(this.inicioPrevisto()),
          fin_previsto: this.aUtcIso(this.finPrevisto()),
        },
        this.tokenJwt(),
      )
      .subscribe({
        next: () => {
          this.asignando.set(false);
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

  protected ejecutarAutomatica(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.resultadoAutomatica.set(null);
    this.puertasService.ejecutarAsignacionAutomatica(this.tokenJwt()).subscribe({
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
