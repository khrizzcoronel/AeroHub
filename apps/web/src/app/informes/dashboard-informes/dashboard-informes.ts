import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import {
  CONFIG_INFORME_ASIGNACIONES,
  CONFIG_INFORME_COMPLIANCE,
  CONFIG_INFORME_FACTURACION,
  CONFIG_INFORME_TENANTS,
  CONFIG_INFORME_TURNAROUNDS,
  CONFIG_INFORME_VUELOS,
  ConfigInforme,
} from '../informes-config';
import { InformeService, InformeSimple, InformeTactico } from '../informe.service';

// Sprint S1.18-iteracion (rediseno del 2026-08-05, TERCER pase --
// referencia visual concreta aportada por el usuario). Estructura por
// modulo, calcada de la referencia:
//   1. Fila de 4 tarjetas KPI.
//   2. Fila de 2 columnas: tarjeta de grafico (COMPUESTO) a la
//      izquierda con badge "Compuesto · ClickHouse", tarjeta de tabla
//      (SIMPLE) a la derecha con badge "Simple · MonetDB".
//
// Separacion real de origen de dato, no solo un badge decorativo:
//   - Compuesto -> GET /analytics/tactico/{modulo} (M7, ClickHouse).
//     Ninguna consulta en vivo contra MonetDB; es un snapshot
//     sincronizado aparte (`tools/sincronizar_analytics_demo.py`), por
//     eso la tarjeta muestra "Última sincronización" en vez de
//     reaccionar al filtro de periodo -- ES una demo minima (research.md
//     de fondo: ClickHouse/ah_tactico real recien llega en la Fase
//     2/S2.4; esto NO es esa tabla, se retira cuando esa fase exista).
//   - Simple -> GET /X/informes/simple (MonetDB, consulta en vivo,
//     reacciona al filtro de periodo global).

interface ModuloInforme {
  scope: string;
  config: ConfigInforme;
}

const MODULOS: ModuloInforme[] = [
  { scope: 'vuelos:leer', config: CONFIG_INFORME_VUELOS },
  { scope: 'puertas:leer', config: CONFIG_INFORME_ASIGNACIONES },
  { scope: 'rampa:leer', config: CONFIG_INFORME_TURNAROUNDS },
  { scope: 'billing:leer', config: CONFIG_INFORME_FACTURACION },
  { scope: 'tenants:administrar', config: CONFIG_INFORME_TENANTS },
  { scope: 'compliance:leer', config: CONFIG_INFORME_COMPLIANCE },
];

const CANTIDAD_GRUPOS_DESTACADOS = 6;

interface BarraGrupo {
  clave: string;
  subtotal: number;
  metricaPrincipal: string | null;
  anchoPct: number;
}

// Estado independiente por modulo -- una clase (no un objeto plano) para
// que cada instancia tenga sus propios signals sin colisionar entre si.
class EstadoModulo {
  readonly config: ConfigInforme;

  readonly cargando = signal(false);
  readonly tacticoError = signal<string | null>(null);
  readonly tactico = signal<InformeTactico | null>(null);

  readonly simpleError = signal<string | null>(null);
  readonly resultadoSimple = signal<InformeSimple<Record<string, unknown>> | null>(null);

  readonly valoresFiltro = signal<Record<string, string>>({});

  readonly usaPeriodo: boolean;

  constructor(config: ConfigInforme) {
    this.config = config;
    this.usaPeriodo = config.filtros.some((f) => f.id === 'periodo_inicio');
  }
}

@Component({
  selector: 'app-dashboard-informes',
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard-informes.html',
  styleUrl: './dashboard-informes.scss',
})
export class DashboardInformes {
  private readonly informeService = inject(InformeService);
  private readonly authService = inject(AuthService);

  protected readonly modulosVisibles: EstadoModulo[] = MODULOS.filter((m) =>
    (this.authService.perfil()?.scopes ?? []).includes(m.scope),
  ).map((m) => new EstadoModulo(m.config));

  // Filtro de periodo GLOBAL -- afecta el lado SIMPLE (MonetDB, consulta
  // en vivo) de los 5 modulos que lo soportan (Tenants no tiene
  // periodo). El lado COMPUESTO (ClickHouse) no reacciona a esto: es un
  // snapshot sincronizado aparte, ver comentario de cabecera.
  protected readonly periodoInicio = signal(this.hace30dias());
  protected readonly periodoFin = signal(this.hoy());

  constructor() {
    for (const modulo of this.modulosVisibles) {
      if (modulo.usaPeriodo) {
        modulo.valoresFiltro.set({
          periodo_inicio: this.periodoInicio(),
          periodo_fin: this.periodoFin(),
        });
      }
    }
    this.cargarSecuencial(0);
  }

  private hoy(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private hace30dias(): string {
    return new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  }

  protected aplicarPeriodoGlobal(): void {
    for (const modulo of this.modulosVisibles) {
      if (modulo.usaPeriodo) {
        modulo.valoresFiltro.set({
          periodo_inicio: this.periodoInicio(),
          periodo_fin: this.periodoFin(),
        });
      }
    }
    this.cargarSecuencial(0);
  }

  // Un modulo a la vez: dispara tactico+simple EN PARALELO entre si (2
  // peticiones, no problematico), pero solo avanza al siguiente modulo
  // cuando ambas terminan -- evita el pico de peticiones simultaneas que
  // rompia la conexion a MonetDB bajo concurrencia real (hallazgo del
  // primer pase de este rediseno).
  private cargarSecuencial(indice: number): void {
    if (indice >= this.modulosVisibles.length) return;
    const modulo = this.modulosVisibles[indice];
    this.cargarModulo(modulo, () => this.cargarSecuencial(indice + 1));
  }

  private cargarModulo(modulo: EstadoModulo, alTerminar: () => void): void {
    modulo.cargando.set(true);
    modulo.tacticoError.set(null);
    modulo.simpleError.set(null);

    const tactico$ = this.informeService.obtenerInformeTactico(modulo.config.moduloCodigo).pipe(
      catchError((err: HttpErrorResponse) => {
        modulo.tacticoError.set(mensajeDeError(err));
        return of(null);
      }),
    );
    const simple$ = this.informeService
      .obtenerInformeSimple<Record<string, unknown>>(modulo.config.endpointSimple, modulo.valoresFiltro())
      .pipe(
        catchError((err: HttpErrorResponse) => {
          modulo.simpleError.set(mensajeDeError(err));
          return of(null);
        }),
      );

    forkJoin([tactico$, simple$]).subscribe(([tactico, simple]) => {
      if (tactico) modulo.tactico.set(tactico);
      if (simple) modulo.resultadoSimple.set(simple);
      modulo.cargando.set(false);
      alTerminar();
    });
  }

  protected recargarModulo(modulo: EstadoModulo): void {
    this.cargarModulo(modulo, () => {
      /* recarga puntual, no dispara el resto de la cadena */
    });
  }

  // Grafico de barras horizontales (dataviz skill, choosing-a-form:
  // "magnitud por grupo" -> barras). Un solo color: una unica serie no
  // necesita mas de un hue ni leyenda (dataviz skill, check 6).
  protected barrasDestacadas(modulo: EstadoModulo): BarraGrupo[] {
    const grupos = (modulo.tactico()?.grupos ?? [])
      .slice()
      .sort((a, b) => b.subtotal - a.subtotal)
      .slice(0, CANTIDAD_GRUPOS_DESTACADOS);
    const maximo = Math.max(1, ...grupos.map((g) => g.subtotal));
    return grupos.map((g) => ({
      clave: g.clave,
      subtotal: g.subtotal,
      metricaPrincipal: g.metrica_principal,
      anchoPct: g.subtotal === 0 ? 0 : Math.max(4, (g.subtotal / maximo) * 100),
    }));
  }

  protected cantidadGruposRestantes(modulo: EstadoModulo): number {
    return Math.max(0, (modulo.tactico()?.grupos.length ?? 0) - CANTIDAD_GRUPOS_DESTACADOS);
  }

  protected valorCelda(fila: Record<string, unknown>, campo: string): string {
    const valor = fila[campo];
    return valor === null || valor === undefined ? '—' : String(valor);
  }

  protected exportarCsv(modulo: EstadoModulo): void {
    this.informeService.descargarCsv(modulo.config.endpointSimple, modulo.valoresFiltro()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = `${modulo.config.titulo.replace(/\s+/g, '_').toLowerCase()}_simple.csv`;
        enlace.click();
        URL.revokeObjectURL(url);
      },
      error: (err: HttpErrorResponse) => modulo.simpleError.set(mensajeDeError(err)),
    });
  }
}
