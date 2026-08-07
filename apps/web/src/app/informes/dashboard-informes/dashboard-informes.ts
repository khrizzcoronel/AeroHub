import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { COLOR_DEFAULT, ConfigInforme, DASHBOARDS_POR_ROL, DashboardRolConfig } from '../informes-config';
import { InformeService, InformeSimple } from '../informe.service';

// docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md (implementado 2026-08-07,
// reemplaza el dashboard modulo-centrico de la iteracion de S1.18 del
// 2026-08-05). La config ya no se resuelve barriendo scopes por modulo
// -- se resuelve por `rol_codigo` del perfil (DASHBOARDS_POR_ROL en
// informes-config.ts), porque un dashboard operativo responde una
// pregunta de jornada concreta por ROL, no "todo lo que ese scope
// alcanza a ver". Sin llamadas a GET /analytics/tactico/* -- esa capa
// (ClickHouse, aerohub_analytics_api) queda intacta y sin consumidor
// aqui, reservada para el dashboard TACTICO real de la Fase 2/S2.4
// (decision D4(a) del plan).

// Estado de una seccion (un informe simple) -- signals propios para no
// colisionar entre secciones de un mismo dashboard.
class EstadoSeccion {
  readonly config: ConfigInforme;
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly resultado = signal<InformeSimple<Record<string, unknown>> | null>(null);
  readonly valoresFiltro = signal<Record<string, string>>({});
  readonly usaPeriodo: boolean;
  // Grafico por defecto, tabla cruda oculta detras de "Ver detalle"
  // (feedback directo del usuario 2026-08-07: las tablas "estorban").
  readonly mostrarDetalle = signal(false);

  constructor(config: ConfigInforme) {
    this.config = config;
    this.usaPeriodo = config.filtros.some((f) => f.id === 'periodo_inicio');
  }
}

export interface BarraDashboard {
  valor: string;
  etiqueta: string;
  cantidad: number;
  anchoPct: number;
  color: string;
}

type AtajoPeriodo = 'hoy' | '24h' | 'semana';

@Component({
  selector: 'app-dashboard-informes',
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard-informes.html',
  styleUrl: './dashboard-informes.scss',
})
export class DashboardInformes {
  private readonly informeService = inject(InformeService);
  private readonly authService = inject(AuthService);

  protected readonly dashboard: DashboardRolConfig | null =
    DASHBOARDS_POR_ROL[this.authService.perfil()?.rol_codigo ?? ''] ?? null;

  protected readonly secciones: EstadoSeccion[] = (this.dashboard?.secciones ?? []).map(
    (config) => new EstadoSeccion(config),
  );

  // Horizonte corto por defecto (plan §2, punto 2): "hoy", no "ultimos
  // 30 dias" -- un controlador de operaciones no abre esta pantalla para
  // ver el mes pasado.
  protected readonly periodoInicio = signal(this.hoy());
  protected readonly periodoFin = signal(this.hoy());
  protected readonly atajoActivo = signal<AtajoPeriodo>('hoy');

  constructor() {
    this.aplicarValoresPeriodo();
    this.cargarSecuencial(0);
  }

  private hoy(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private haceDias(dias: number): string {
    return new Date(Date.now() - dias * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  }

  private aplicarValoresPeriodo(): void {
    for (const seccion of this.secciones) {
      if (seccion.usaPeriodo) {
        seccion.valoresFiltro.set({
          ...seccion.valoresFiltro(),
          periodo_inicio: this.periodoInicio(),
          periodo_fin: this.periodoFin(),
        });
      }
    }
  }

  // Atajos Hoy / 24 h / Esta semana (plan §2, punto 2) -- 24h y "esta
  // semana" usan la MISMA fecha de hoy como "hasta" (el informe simple
  // filtra por fecha_operacion, no por hora, asi que 24h y hoy son
  // equivalentes para ese filtro; se ofrecen igual porque el rol piensa
  // en esos terminos, no en el detalle de implementacion del filtro).
  protected aplicarAtajo(atajo: AtajoPeriodo): void {
    this.atajoActivo.set(atajo);
    if (atajo === 'hoy' || atajo === '24h') {
      this.periodoInicio.set(this.hoy());
      this.periodoFin.set(this.hoy());
    } else {
      this.periodoInicio.set(this.haceDias(7));
      this.periodoFin.set(this.hoy());
    }
    this.aplicarPeriodoGlobal();
  }

  protected aplicarPeriodoGlobal(): void {
    this.aplicarValoresPeriodo();
    this.cargarSecuencial(0);
  }

  // Una seccion a la vez -- evita el pico de peticiones simultaneas que
  // rompia la conexion a MonetDB bajo concurrencia real (hallazgo del
  // dashboard modulo-centrico anterior, sigue aplicando aqui).
  private cargarSecuencial(indice: number): void {
    if (indice >= this.secciones.length) return;
    const seccion = this.secciones[indice];
    this.cargarSeccion(seccion, () => this.cargarSecuencial(indice + 1));
  }

  private cargarSeccion(seccion: EstadoSeccion, alTerminar: () => void): void {
    seccion.cargando.set(true);
    seccion.error.set(null);
    this.informeService
      .obtenerInformeSimple<Record<string, unknown>>(seccion.config.endpointSimple, seccion.valoresFiltro())
      .subscribe({
        next: (resultado) => {
          seccion.resultado.set(resultado);
          seccion.cargando.set(false);
          alTerminar();
        },
        error: (err: HttpErrorResponse) => {
          seccion.error.set(mensajeDeError(err));
          seccion.cargando.set(false);
          alTerminar();
        },
      });
  }

  protected recargarSeccion(seccion: EstadoSeccion): void {
    this.cargarSeccion(seccion, () => {
      /* recarga puntual, no dispara el resto de la cadena */
    });
  }

  // KPI derivados (plan §2, punto 3): un conteo en el cliente sobre
  // filas YA CARGADAS -- nunca una llamada nueva al backend, nunca una
  // agregacion en el servidor. Devuelve null (se muestra "—") mientras
  // la seccion de origen todavia no cargo.
  protected valorKpi(seccionIndice: number, calculo: (filas: Record<string, unknown>[]) => number): number | null {
    const seccion = this.secciones[seccionIndice];
    if (!seccion || seccion.resultado() === null) return null;
    return calculo(seccion.resultado()!.filas);
  }

  protected alternarDetalle(seccion: EstadoSeccion): void {
    seccion.mostrarDetalle.set(!seccion.mostrarDetalle());
  }

  // Grafico de barras: agrupa client-side las filas YA CARGADAS por
  // config.campoAgrupacion -- mismo principio que valorKpi (un conteo en
  // el cliente no es un informe compuesto, plan §2 punto 3). Ordenado por
  // cantidad descendente; ancho relativo al grupo mas grande.
  protected barrasDeSeccion(seccion: EstadoSeccion): BarraDashboard[] {
    const campo = seccion.config.campoAgrupacion;
    const filas = seccion.resultado()?.filas;
    if (!campo || !filas || filas.length === 0) return [];

    const conteos = new Map<string, number>();
    for (const fila of filas) {
      const valor = String(fila[campo] ?? '—');
      conteos.set(valor, (conteos.get(valor) ?? 0) + 1);
    }

    const maximo = Math.max(...conteos.values());
    return Array.from(conteos.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([valor, cantidad]) => ({
        valor,
        etiqueta: seccion.config.etiquetasCategoria?.[valor] ?? valor.replace(/_/g, ' '),
        cantidad,
        anchoPct: Math.round((cantidad / maximo) * 100),
        color: seccion.config.colorPorValor?.[valor] ?? COLOR_DEFAULT,
      }));
  }

  protected valorCelda(fila: Record<string, unknown>, campo: string): string {
    const valor = fila[campo];
    return valor === null || valor === undefined ? '—' : String(valor);
  }

  protected exportarCsv(seccion: EstadoSeccion): void {
    this.informeService.descargarCsv(seccion.config.endpointSimple, seccion.valoresFiltro()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `${seccion.config.titulo.replace(/\s+/g, '_').toLowerCase()}_simple.csv`;
        enlace.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => seccion.error.set(mensajeDeError(err)),
    });
  }
}
