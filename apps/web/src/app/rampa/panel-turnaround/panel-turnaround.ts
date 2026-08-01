import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Incidencia, RampaService, Tarea, Turnaround } from '../rampa.service';

// Sin login real todavia (mismo estado que el resto de apps/web) -- el
// token JWT se pega a mano.
@Component({
  selector: 'app-panel-turnaround',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-turnaround.html',
})
export class PanelTurnaround {
  protected readonly tokenJwt = signal('');
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

  private readonly rampaService = inject(RampaService);

  protected cargarTurnarounds(): void {
    this.error.set(null);
    this.rampaService.listarTurnarounds(this.tokenJwt()).subscribe({
      next: (respuesta) => this.turnarounds.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected crearTurnaround(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.rampaService
      .crearTurnaround(
        {
          vuelo_llegada_id: this.vueloLlegadaId(),
          vuelo_salida_id: this.vueloSalidaId(),
          inicio_previsto: this.aUtcIso(this.inicioPrevisto()),
          fin_previsto: this.aUtcIso(this.finPrevisto()),
        },
        this.tokenJwt(),
      )
      .subscribe({
        next: () => {
          this.cargando.set(false);
          this.cargarTurnarounds();
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(this.mensajeDeError(err));
          this.cargando.set(false);
        },
      });
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
    this.rampaService.listarTareas(turnaroundId, this.tokenJwt()).subscribe({
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
    this.rampaService.iniciarTarea(turnaroundId, this.tipoTareaId(), this.tokenJwt()).subscribe({
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
    this.rampaService
      .finalizarTarea(tareaId, this.aUtcIso(this.finReal()), this.tokenJwt())
      .subscribe({
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
    this.rampaService.listarIncidencias(this.tokenJwt()).subscribe({
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
