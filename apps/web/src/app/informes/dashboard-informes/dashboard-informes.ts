import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { COLOR_DEFAULT, ConfigInforme, DASHBOARDS_POR_ROL, DashboardRolConfig, KpiOperativo } from '../informes-config';
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

  // Distribución en tarjetas (pedido directo del usuario 2026-08-08, con
  // referencia visual externa de un dashboard de KPIs). Eyebrow real (el
  // período efectivamente aplicado, no un texto fijo tipo "Month to
  // date"): la referencia trae sparkline + variación % por integración
  // externa (Stripe/HubSpot/Google Analytics...) que AeroHub no tiene por
  // KPI -- se adapta el layout de tarjetas sin inventar series históricas
  // ni porcentajes que no existen; el pie de tarjeta muestra el informe
  // real del que se deriva el número en su lugar (procedencia real).
  protected readonly etiquetaPeriodoActivo = () => {
    switch (this.atajoActivo()) {
      case 'hoy':
        return 'Hoy';
      case '24h':
        return 'Últimas 24 h';
      case 'semana':
        return 'Esta semana';
    }
  };

  // Heuristica de semaforo por texto de la etiqueta (mismo criterio ya
  // usado en toda la app para mapear un estado crudo a un tono): un KPI
  // que nombra una condicion negativa (vencidas, no completados, etc.) se
  // resalta en critico: el resto queda en el tono neutro por defecto.
  private static readonly PALABRAS_CRITICO = [
    'no completad',
    'vencid',
    'disputad',
    'suspendid',
    'interrumpid',
    'con conflicto',
    'con incidencia',
  ];

  protected claseValorKpi(kpi: KpiOperativo): string {
    const etiqueta = kpi.etiqueta.toLowerCase();
    const esCritico = DashboardInformes.PALABRAS_CRITICO.some((palabra) => etiqueta.includes(palabra));
    return esCritico ? 'kpi-card__valor--critico' : '';
  }

  protected fuenteKpi(kpi: KpiOperativo): string {
    return this.secciones[kpi.seccionIndice]?.config.titulo ?? '';
  }

  // Mini-tendencia real (2026-08-08, pedido explicito del usuario de
  // replicar el layout completo de la referencia -- sparkline + variacion
  // %). En vez de fabricar una serie/porcentaje decorativos, se agrupan
  // las filas YA CARGADAS de la seccion por dia (config.campoFecha) y se
  // le aplica el MISMO `kpi.calculo` de la tarjeta a cada dia -- la
  // tendencia que se muestra es el valor real de ese KPI puntual, dia por
  // dia, dentro del periodo ya consultado. Sin campoFecha (Tenants, sin
  // eje temporal en su informe) o con un solo dia de datos, la tarjeta
  // simplemente no ofrece sparkline/variacion -- nunca se inventa un
  // punto de comparacion que no existe.
  protected serieKpi(kpi: KpiOperativo): number[] {
    const seccion = this.secciones[kpi.seccionIndice];
    const campoFecha = seccion?.config.campoFecha;
    const filas = seccion?.resultado()?.filas;
    if (!seccion || !campoFecha || !filas || filas.length === 0) return [];

    const porDia = new Map<string, Record<string, unknown>[]>();
    for (const fila of filas) {
      const crudo = fila[campoFecha];
      if (crudo === null || crudo === undefined) continue;
      const dia = String(crudo).slice(0, 10);
      const grupo = porDia.get(dia);
      if (grupo) grupo.push(fila);
      else porDia.set(dia, [fila]);
    }
    return Array.from(porDia.keys())
      .sort()
      .map((dia) => kpi.calculo(porDia.get(dia)!));
  }

  // Puntos de un sparkline SVG (viewBox 0 0 100 30) normalizado al rango
  // real de la serie -- sin libreria de graficos, mismo criterio "thin
  // marks" del skill dataviz para una serie unica sin eje visible.
  protected puntosSparkline(serie: number[]): string {
    if (serie.length < 2) return '';
    const max = Math.max(...serie);
    const min = Math.min(...serie);
    const rango = max - min || 1;
    const pasoX = 100 / (serie.length - 1);
    return serie.map((valor, i) => `${i * pasoX},${28 - ((valor - min) / rango) * 26}`).join(' ');
  }

  // Variacion real entre la primera y la segunda mitad de la serie diaria
  // (promedio a promedio) -- honesto dentro de lo que hay: no es una
  // comparacion contra el periodo anterior (eso pediria una consulta
  // nueva al backend), es la tendencia dentro del propio periodo ya
  // cargado. null cuando no hay base de comparacion valida.
  protected tendenciaPct(serie: number[]): number | null {
    if (serie.length < 2) return null;
    const mitad = Math.max(1, Math.floor(serie.length / 2));
    const promedio = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const antes = promedio(serie.slice(0, mitad));
    const despues = promedio(serie.slice(mitad));
    if (antes === 0) return despues === 0 ? 0 : null;
    return Math.round(((despues - antes) / antes) * 100);
  }

  // Polaridad: para un KPI "critico" (vencidas, interrumpidos...) subir es
  // malo -- se invierte el color respecto a un KPI neutro, donde subir es
  // bueno. Mismo criterio semantico que claseValorKpi.
  protected claseTendencia(kpi: KpiOperativo, pct: number | null): string {
    if (pct === null || pct === 0) return 'kpi-card__tendencia--neutro';
    const esCritico = DashboardInformes.PALABRAS_CRITICO.some((p) => kpi.etiqueta.toLowerCase().includes(p));
    const sube = pct > 0;
    const esBueno = esCritico ? !sube : sube;
    return esBueno ? 'kpi-card__tendencia--ok' : 'kpi-card__tendencia--critico';
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
