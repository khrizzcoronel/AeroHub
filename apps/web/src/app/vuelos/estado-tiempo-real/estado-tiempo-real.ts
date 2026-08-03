import { Component, OnDestroy, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';

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
  return clase ? `ah-tira--${clase}` : '';
}

// Sprint S1.11 (research.md Decision 3): el WebSocket nativo no pasa por
// HttpClient, asi que authInterceptor no puede agregarle el token -- se
// lee de AuthService.token() (la misma sesion que ya autentica el resto
// de la aplicacion desde S1.10), en vez de pedirselo a la persona en un
// textarea.
@Component({
  selector: 'app-estado-tiempo-real',
  imports: [],
  templateUrl: './estado-tiempo-real.html',
  styleUrl: './estado-tiempo-real.scss',
})
export class EstadoTiempoReal implements OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly conectado = signal(false);
  protected readonly error = signal<string | null>(null);
  // Posicion fija, mas reciente primero -- glanceability (RF-O04): no hace
  // falta desplazarse para ver el ultimo cambio, que es el dato relevante
  // de un vistazo. Se limita el historial visible, no es un log completo.
  protected readonly eventos = signal<EventoEstadoVuelo[]>([]);

  private socket: WebSocket | null = null;

  protected readonly claseDeEstado = claseDeEstado;

  protected conectar(): void {
    const token = this.auth.token();
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }

    this.error.set(null);
    this.eventos.set([]);
    const socket = new WebSocket(`${WS_BASE_URL}/vuelos/ws/estado?token=${encodeURIComponent(token)}`);

    socket.onopen = () => this.conectado.set(true);
    socket.onclose = (evento) => {
      this.conectado.set(false);
      if (evento.code >= 4000) {
        // Sesion invalida/vencida -- mismo criterio que authInterceptor
        // ante un 401 de HTTP (S1.10): no dejar la pantalla en un estado
        // ambiguo, llevar a la persona a iniciar sesion de nuevo.
        this.router.navigate(['/login']);
      }
    };
    socket.onerror = () => this.error.set('Error de conexion WebSocket');
    socket.onmessage = (mensaje) => {
      const evento = JSON.parse(mensaje.data) as EventoEstadoVuelo;
      this.eventos.update((actuales) => [evento, ...actuales].slice(0, 20));
    };

    this.socket = socket;
  }

  protected desconectar(): void {
    this.socket?.close();
    this.socket = null;
    this.conectado.set(false);
  }

  ngOnDestroy(): void {
    this.socket?.close();
  }
}
