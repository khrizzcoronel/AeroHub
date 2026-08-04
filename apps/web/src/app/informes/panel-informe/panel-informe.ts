import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { mensajeDeError } from '../../auth/auth.service';
import { GrupoInforme, InformeCompuesto, InformeService, InformeSimple } from '../informe.service';

export interface ColumnaInforme {
  campo: string;
  etiqueta: string;
}

export interface FiltroInforme {
  id: string;
  etiqueta: string;
  tipo: 'fecha' | 'texto' | 'select';
  opciones?: { valor: string; etiqueta: string }[];
}

// Sprint S1.18 -- research.md Decision 1: componente UNICO reutilizado
// por los 6 modulos, configurado via @Input(). Cada modulo lo instancia
// con su propia config (titulo, rutas de endpoint, filtros, columnas) en
// vez de tener 6 componentes casi identicos.
export interface ConfigInforme {
  titulo: string;
  endpointSimple: string;
  endpointCompuesto: string;
  filtros: FiltroInforme[];
  columnasSimple: ColumnaInforme[];
  columnaGrupo: string;
  columnasMetricas: ColumnaInforme[];
}

@Component({
  selector: 'app-panel-informe',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-informe.html',
  styleUrl: './panel-informe.scss',
})
export class PanelInforme implements OnInit {
  @Input({ required: true }) config!: ConfigInforme;

  private readonly informeService = inject(InformeService);

  protected readonly modo = signal<'simple' | 'compuesto'>('simple');
  protected readonly valoresFiltro = signal<Record<string, string>>({});

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly resultadoSimple = signal<InformeSimple<Record<string, unknown>> | null>(null);
  protected readonly resultadoCompuesto = signal<InformeCompuesto | null>(null);

  ngOnInit(): void {
    this.consultar();
  }

  protected cambiarModo(modo: 'simple' | 'compuesto'): void {
    this.modo.set(modo);
    this.consultar();
  }

  protected actualizarFiltro(id: string, valor: string): void {
    this.valoresFiltro.update((actual) => ({ ...actual, [id]: valor }));
  }

  protected consultar(): void {
    this.error.set(null);
    this.cargando.set(true);
    const ruta = this.modo() === 'simple' ? this.config.endpointSimple : this.config.endpointCompuesto;
    if (this.modo() === 'simple') {
      this.informeService.obtenerInformeSimple<Record<string, unknown>>(ruta, this.valoresFiltro()).subscribe({
        next: (r) => {
          this.resultadoSimple.set(r);
          this.cargando.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(mensajeDeError(err));
          this.cargando.set(false);
        },
      });
    } else {
      this.informeService.obtenerInformeCompuesto(ruta, this.valoresFiltro()).subscribe({
        next: (r) => {
          this.resultadoCompuesto.set(r);
          this.cargando.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(mensajeDeError(err));
          this.cargando.set(false);
        },
      });
    }
  }

  protected exportarCsv(): void {
    const ruta = this.modo() === 'simple' ? this.config.endpointSimple : this.config.endpointCompuesto;
    this.informeService.descargarCsv(ruta, this.valoresFiltro()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `${this.config.titulo.replace(/\s+/g, '_').toLowerCase()}_${this.modo()}.csv`;
        enlace.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected valorCelda(fila: Record<string, unknown>, campo: string): string {
    const valor = fila[campo];
    return valor === null || valor === undefined ? '—' : String(valor);
  }

  protected valorMetrica(grupo: GrupoInforme, campo: string): string {
    const valor = grupo.metricas[campo];
    return valor === null || valor === undefined ? '—' : String(valor);
  }
}
