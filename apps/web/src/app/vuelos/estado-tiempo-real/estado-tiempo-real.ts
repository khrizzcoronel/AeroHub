import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import {
  Aerolinea,
  Aeronave,
  Aeropuerto,
  TipoVuelo,
  VueloConsultado,
  VueloService,
} from '../vuelo.service';

// URL del backend compuesto (services/gateway/main.py, Sprint S1.1/S1.2).
// Ver el comentario equivalente en tenants/tenant.service.ts -- se mueve a
// environment.ts cuando exista un build de produccion real.
const WS_BASE_URL = 'ws://localhost:8000';

export interface EventoEstadoVuelo {
  vuelo_id: string;
  vuelo_estado_id: string;
  estado_id: string;
  codigo_estado: string;
  ocurrido_en: string;
}

// Semaforo operacional (DIRECCION_VISUAL.md §2.3) -- mapeo de
// codigo_estado a uno de los 4 tokens de color. Los codigos concretos
// vienen de catalogo.estado_vuelo_catalogo (S1.1); este mapeo es de
// PRESENTACION unicamente, no repite ninguna regla de negocio.
const CLASE_SEMAFORO: Record<string, 'ok' | 'atencion' | 'critico'> = {
  embarcando: 'ok',
  en_vuelo: 'ok',
  aterrizado: 'ok',
  cancelado: 'critico',
  desviado: 'critico',
};

function claseDeEstado(codigoEstado: string): string {
  const clase = CLASE_SEMAFORO[codigoEstado.toLowerCase()];
  return clase ? `ah-pill--${clase}` : '';
}

// Etiqueta legible -- mapeo exhaustivo sobre los 6 valores reales de
// catalogo.estado_vuelo_catalogo (db/seeds/generate.py::ESTADOS_VUELO).
const ETIQUETAS_ESTADO: Record<string, string> = {
  programado: 'Programado',
  embarcando: 'Embarcando',
  en_vuelo: 'En vuelo',
  aterrizado: 'Aterrizado',
  cancelado: 'Cancelado',
  desviado: 'Desviado',
};

function etiquetaEstado(codigoEstado: string): string {
  return ETIQUETAS_ESTADO[codigoEstado.toLowerCase()] ?? codigoEstado;
}

// Opciones del <select> de cambio de estado (research.md Decision 3,
// S1.15): mismo catalogo de 6 codigos que ETIQUETAS_ESTADO -- el backend
// (dominio abierto) sigue siendo quien valida si la transicion puntual es
// legal, aqui solo se ofrecen las opciones conocidas.
const OPCIONES_ESTADO = Object.entries(ETIQUETAS_ESTADO).map(([value, label]) => ({ value, label }));

const TAMANO_PAGINA = 10;

// Sprint S1.11 (research.md Decision 3): el WebSocket nativo no pasa por
// HttpClient, asi que authInterceptor no puede agregarle el token -- se
// lee de AuthService.token() (la misma sesion que ya autentica el resto
// de la aplicacion desde S1.10), en vez de pedirselo a la persona en un
// textarea.
@Component({
  selector: 'app-estado-tiempo-real',
  imports: [CommonModule, FormsModule],
  templateUrl: './estado-tiempo-real.html',
  styleUrl: './estado-tiempo-real.scss',
})
export class EstadoTiempoReal implements OnInit, OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly vueloService = inject(VueloService);
  private readonly toast = inject(ToastService);

  protected readonly conectado = signal(false);
  // Fase 5 de docs/diseno/PLAN_CORRECCION_MODULOS.md (item 14): la
  // conexion ya no se activa/corta a mano -- se abre sola al entrar y se
  // reconecta sola si se cae. `reconectando` distingue "cayo, reintentando"
  // de "nunca se conecto" para el indicador.
  protected readonly reconectando = signal(false);
  protected readonly error = signal<string | null>(null);
  // Mas reciente primero -- historial capado a 20 (RF-O04, glanceability).
  // Post S1.14: se le agrega tabla + filtro + paginacion (pedido directo del
  // usuario, reabre la excepcion que este plan proponia originalmente para
  // esta vista) -- la pagina 1 sigue siendo la mas reciente.
  protected readonly eventos = signal<EventoEstadoVuelo[]>([]);

  // KPI de apertura (Fase 5, item 13): cuantos de los eventos visibles
  // estan en un estado critico (cancelado/desviado) -- no vuelve a pedir
  // nada al backend, es una lectura sobre `eventos` ya cargado.
  protected readonly eventosCriticos = computed(
    () => this.eventos().filter((e) => claseDeEstado(e.codigo_estado) === 'ah-pill--critico').length,
  );

  private socket: WebSocket | null = null;
  private reintentoTimeout: ReturnType<typeof setTimeout> | null = null;
  private destruido = false;

  protected readonly claseDeEstado = claseDeEstado;
  protected readonly etiquetaEstado = etiquetaEstado;

  // Fase 1 de docs/diseno/PLAN_CORRECCION_MODULOS.md (2026-08-06, D1(a)):
  // role_tenant_admin perdio vuelos:escribir (la matriz de roles reserva
  // crear vuelos/cambiar estado a role_operations_controller/
  // role_airline_coordinator) -- ocultar "Nuevo vuelo" y "Cambiar estado"
  // para quien no tiene el scope, en vez de dejar un boton que siempre
  // devuelve 403.
  protected readonly puedeEscribir = computed(() =>
    (this.auth.perfil()?.scopes ?? []).includes('vuelos:escribir'),
  );

  protected readonly filtroVuelo = signal('');
  protected readonly eventosFiltrados = computed(() => {
    const q = this.filtroVuelo().trim().toLowerCase();
    if (!q) return this.eventos();
    return this.eventos().filter((e) => e.vuelo_id.toLowerCase().includes(q));
  });

  protected readonly paginaActual = signal(1);
  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.eventosFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly eventosPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANO_PAGINA;
    return this.eventosFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  protected actualizarFiltroVuelo(valor: string): void {
    this.filtroVuelo.set(valor);
    this.paginaActual.set(1);
  }

  protected paginaAnterior(): void {
    this.paginaActual.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguiente(): void {
    this.paginaActual.update((p) => Math.min(this.totalPaginas(), p + 1));
  }

  // Sprint S1.15 (superficie de M1 AODB) -- catalogos para poblar los
  // <select> del formulario de alta, nunca ids pegados a mano (FR-010).
  protected readonly aerolineas = signal<Aerolinea[]>([]);
  protected readonly aeronaves = signal<Aeronave[]>([]);
  protected readonly tiposVuelo = signal<TipoVuelo[]>([]);
  protected readonly aeropuertos = signal<Aeropuerto[]>([]);
  protected readonly opcionesEstado = OPCIONES_ESTADO;

  protected readonly mostrarModalNuevoVuelo = signal(false);
  protected readonly errorFormulario = signal<string | null>(null);
  protected readonly guardando = signal(false);

  protected readonly aerolineaId = signal('');
  protected readonly aeronaveId = signal('');
  protected readonly numeroVuelo = signal('');
  protected readonly tipoVueloId = signal('');
  protected readonly fechaOperacion = signal('');
  protected readonly sentido = signal('L');
  protected readonly aeropuertoOrigenId = signal('');
  protected readonly aeropuertoDestinoId = signal('');
  protected readonly staUtc = signal('');
  protected readonly stdUtc = signal('');
  protected readonly paxEstimado = signal<number | null>(null);

  // Ver detalles (Fase 4 de docs/diseno/PLAN_CORRECCION_MODULOS.md, item
  // 11): la fila ya no abre "Cambiar estado" directo -- abre el detalle
  // completo del vuelo (GET /vuelos/{id}) y el cambio de estado vive
  // DENTRO de ese modal, como una accion propia del registro.
  protected readonly vueloDetalle = signal<VueloConsultado | null>(null);
  protected readonly cargandoDetalle = signal(false);
  protected readonly estadoNuevo = signal('');

  ngOnInit(): void {
    this.vueloService.listarAerolineas().subscribe({ next: (r) => this.aerolineas.set(r) });
    this.vueloService.listarAeronaves().subscribe({ next: (r) => this.aeronaves.set(r) });
    this.vueloService.listarTiposVuelo().subscribe({ next: (r) => this.tiposVuelo.set(r) });
    this.vueloService.listarAeropuertos().subscribe({ next: (r) => this.aeropuertos.set(r) });
    this.conectar();
  }

  protected abrirModalNuevoVuelo(): void {
    this.errorFormulario.set(null);
    this.mostrarModalNuevoVuelo.set(true);
  }

  protected cerrarModalNuevoVuelo(): void {
    this.mostrarModalNuevoVuelo.set(false);
  }

  // <input type="datetime-local"> no lleva zona horaria -- mismo hallazgo
  // que apps/web/puertas/tablero-puertas.ts (S1.4).
  private aUtcIso(valorLocal: string): string {
    return valorLocal.length === 16 ? `${valorLocal}:00Z` : `${valorLocal}Z`;
  }

  protected crearVuelo(): void {
    this.guardando.set(true);
    this.errorFormulario.set(null);
    this.vueloService
      .altaVuelo({
        aerolinea_id: this.aerolineaId(),
        aeronave_id: this.aeronaveId(),
        numero_vuelo: this.numeroVuelo(),
        tipo_vuelo_id: this.tipoVueloId(),
        fecha_operacion: this.fechaOperacion(),
        sentido: this.sentido(),
        aeropuerto_origen_id: this.aeropuertoOrigenId(),
        aeropuerto_destino_id: this.aeropuertoDestinoId(),
        sta_utc: this.aUtcIso(this.staUtc()),
        std_utc: this.aUtcIso(this.stdUtc()),
        pax_estimado: this.paxEstimado(),
      })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.mostrarModalNuevoVuelo.set(false);
          this.toast.mostrar('Vuelo registrado con éxito', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormulario.set(mensajeDeError(err));
          this.guardando.set(false);
        },
      });
  }

  protected verDetalles(vueloId: string): void {
    this.errorFormulario.set(null);
    this.estadoNuevo.set('');
    this.vueloDetalle.set(null);
    this.cargandoDetalle.set(true);
    this.vueloService.obtenerVuelo(vueloId).subscribe({
      next: (v) => {
        this.vueloDetalle.set(v);
        this.cargandoDetalle.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.errorFormulario.set(mensajeDeError(err));
        this.cargandoDetalle.set(false);
      },
    });
  }

  protected cerrarModalDetalle(): void {
    this.vueloDetalle.set(null);
  }

  protected nombreAerolineaDe(id: string): string {
    const a = this.aerolineas().find((item) => item.id === id);
    return a ? `${a.nombre} (${a.codigo_iata})` : id;
  }

  protected nombreAeronaveDe(id: string): string {
    const a = this.aeronaves().find((item) => item.id === id);
    return a ? `${a.matricula} — ${a.fabricante} ${a.modelo}` : id;
  }

  protected nombreAeropuertoDe(id: string): string {
    const a = this.aeropuertos().find((item) => item.id === id);
    return a ? `${a.nombre} (${a.codigo_iata})` : id;
  }

  protected cambiarEstado(): void {
    const vueloId = this.vueloDetalle()?.id;
    if (!vueloId) return;
    this.guardando.set(true);
    this.errorFormulario.set(null);
    this.vueloService
      .cambiarEstadoVuelo(vueloId, {
        codigo_estado_nuevo: this.estadoNuevo(),
        origen_cambio: 'manual',
      })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.vueloDetalle.set(null);
          // El WS ya conectado recibe el evento en <1s (RNF-P01) y agrega
          // la fila -- no se sintetiza una fila local para no arriesgar
          // una fila duplicada si el evento real llega mientras tanto.
          this.toast.mostrar(`Estado actualizado a: ${etiquetaEstado(this.estadoNuevo())}`, 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormulario.set(mensajeDeError(err));
          this.guardando.set(false);
        },
      });
  }

  // Fase 5 (item 14): conexion automatica con reconexion -- reemplaza los
  // botones "Conectar"/"Desconectar" por un indicador de solo lectura
  // (ver estado-tiempo-real.html). Se llama sola desde ngOnInit y desde
  // si misma tras una caida no autenticada.
  private conectar(): void {
    const token = this.auth.token();
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }

    this.error.set(null);
    const socket = new WebSocket(`${WS_BASE_URL}/vuelos/ws/estado?token=${encodeURIComponent(token)}`);

    socket.onopen = () => {
      this.conectado.set(true);
      this.reconectando.set(false);
    };
    socket.onclose = (evento) => {
      this.conectado.set(false);
      if (evento.code >= 4000) {
        // Sesion invalida/vencida -- mismo criterio que authInterceptor
        // ante un 401 de HTTP (S1.10): no dejar la pantalla en un estado
        // ambiguo, llevar a la persona a iniciar sesion de nuevo. Nunca
        // reintentar un cierre de este tipo -- el token no va a volverse
        // valido solo.
        this.reconectando.set(false);
        this.router.navigate(['/login']);
        return;
      }
      // Corte de red u otro cierre no autenticado -- reintentar en 3s,
      // salvo que el componente ya se haya destruido (ngOnDestroy).
      if (!this.destruido) {
        this.reconectando.set(true);
        this.reintentoTimeout = setTimeout(() => this.conectar(), 3000);
      }
    };
    socket.onerror = () => this.error.set('Error de conexion WebSocket');
    socket.onmessage = (mensaje) => {
      const evento = JSON.parse(mensaje.data) as EventoEstadoVuelo;
      this.eventos.update((actuales) => [evento, ...actuales].slice(0, 20));
    };

    this.socket = socket;
  }

  ngOnDestroy(): void {
    this.destruido = true;
    if (this.reintentoTimeout) clearTimeout(this.reintentoTimeout);
    this.socket?.close();
  }
}
