import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import {
  FranjaTiempoEspera,
  PassengerService,
  TerminalPassenger,
} from '../passenger.service';

// Anchos de franja que ofrece el selector. El backend acepta cualquier
// valor en (0, 1440] (domain/tiempo_espera.py::franja_de), pero una lista
// curada evita que alguien pida franjas de 7 minutos y obtenga un perfil
// ilegible -- mismo criterio que MONEDAS_COMUNES en panel-tarifarios.
const ANCHOS_FRANJA = [15, 30, 60] as const;

function hoyIso(): string {
  return new Date().toISOString().slice(0, 10);
}

@Component({
  selector: 'app-panel-tiempos-espera',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-tiempos-espera.html',
  styleUrl: './panel-tiempos-espera.scss',
})
export class PanelTiemposEspera {
  private readonly passengerService = inject(PassengerService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);

  protected readonly anchosFranja = ANCHOS_FRANJA;

  protected readonly cargando = signal(false);
  protected readonly recalculando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly terminales = signal<TerminalPassenger[]>([]);
  protected readonly terminalId = signal('');
  protected readonly fecha = signal(hoyIso());
  protected readonly franjaMinutos = signal<number>(30);

  protected readonly franjas = signal<FranjaTiempoEspera[]>([]);
  // Distingue "todavía no consultaste" de "consultaste y no hay datos":
  // son dos estados vacíos con mensajes distintos.
  protected readonly consultado = signal(false);

  // CU-O19 lo ejecuta el "Sistema", que corre bajo role_operations_controller
  // (98_grants_billing.sql:19,54 le da S,I,Up sobre tiempo_espera_agregado).
  // El resto de roles con passenger:leer solo consulta.
  protected readonly puedeRecalcular = computed(() =>
    (this.auth.perfil()?.scopes ?? []).includes('passenger:escribir'),
  );

  protected readonly minutosDe = (f: FranjaTiempoEspera): number => Number(f.minutos_estimados);

  /** El backend devuelve la hora como 'HH:MM:SS'; los segundos siempre son
   * 00 (las franjas se bucketizan a minutos) y solo agregan ruido visual. */
  protected hhmm(hora: string): string {
    return hora.slice(0, 5);
  }

  protected readonly textoMuestraTotal = computed(() => {
    const n = this.muestraTotal();
    return n === 1 ? '1 observación' : `${n} observaciones`;
  });

  // Máximo del día -- referencia para el ancho de barra. Es una lectura
  // relativa al propio día, no una escala absoluta: no existe ningún umbral
  // de "espera aceptable" en el dominio (domain/tiempo_espera.py solo define
  // que una franja sin muestras no se publica), así que la vista no inventa
  // uno ni pinta semáforo evaluativo.
  protected readonly maximoDelDia = computed(() => {
    const valores = this.franjas().map(this.minutosDe);
    return valores.length ? Math.max(...valores) : 0;
  });

  protected readonly franjaPico = computed(() => {
    const maximo = this.maximoDelDia();
    if (!maximo) return null;
    return this.franjas().find((f) => this.minutosDe(f) === maximo) ?? null;
  });

  protected readonly promedioDelDia = computed(() => {
    const valores = this.franjas().map(this.minutosDe);
    if (!valores.length) return 0;
    return valores.reduce((a, b) => a + b, 0) / valores.length;
  });

  // Total de observaciones que respaldan el perfil completo. Se muestra
  // porque el estimado es un promedio: sin saber sobre cuántas
  // observaciones se calculó, un "12 min" no dice lo mismo.
  protected readonly muestraTotal = computed(() =>
    this.franjas().reduce((total, f) => total + f.muestra_n, 0),
  );

  protected readonly franjasOrdenadas = computed(() =>
    [...this.franjas()].sort((a, b) => a.franja_inicio.localeCompare(b.franja_inicio)),
  );

  constructor() {
    this.passengerService.listarTerminales().subscribe({
      next: (lista) => {
        this.terminales.set(lista);
        // Con una sola terminal no tiene sentido obligar a elegirla.
        if (lista.length === 1) {
          this.terminalId.set(lista[0].id);
          this.consultar();
        }
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  /** Ancho de barra en % del máximo del día, mínimo visible 2%. */
  protected anchoBarra(f: FranjaTiempoEspera): number {
    const maximo = this.maximoDelDia();
    if (!maximo) return 0;
    return Math.max(2, (this.minutosDe(f) / maximo) * 100);
  }

  protected esPico(f: FranjaTiempoEspera): boolean {
    return this.franjaPico()?.franja_inicio === f.franja_inicio;
  }

  protected nombreTerminal(id: string): string {
    const t = this.terminales().find((x) => x.id === id);
    return t ? `${t.codigo} — ${t.nombre}` : id;
  }

  protected consultar(): void {
    if (!this.terminalId() || !this.fecha()) return;
    this.cargando.set(true);
    this.error.set(null);
    this.passengerService.obtenerTiemposEspera(this.terminalId(), this.fecha()).subscribe({
      next: (r) => {
        this.franjas.set(r.franjas);
        this.consultado.set(true);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.franjas.set([]);
        this.consultado.set(true);
        this.cargando.set(false);
      },
    });
  }

  protected recalcular(): void {
    if (!this.terminalId() || !this.fecha()) return;
    this.recalculando.set(true);
    this.error.set(null);
    this.passengerService
      .recalcular(this.terminalId(), this.fecha(), this.franjaMinutos())
      .subscribe({
        next: (r) => {
          this.recalculando.set(false);
          // El backend descarta las franjas sin muestras en vez de publicar
          // un estimado inventado -- se dice explícitamente, es información
          // real sobre la calidad del resultado, no un detalle interno.
          const descartadas = r.franjas_descartadas_por_muestra_insuficiente;
          const actualizadas =
            r.franjas_actualizadas === 1
              ? '1 franja actualizada'
              : `${r.franjas_actualizadas} franjas actualizadas`;
          this.toast.mostrar(
            descartadas > 0
              ? `${actualizadas} · ${descartadas} sin observaciones suficientes`
              : actualizadas,
            'exito',
          );
          this.consultar();
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(mensajeDeError(err));
          this.recalculando.set(false);
        },
      });
  }
}
