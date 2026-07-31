import { Component, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

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

// Sprint S1.2 no incluye login real (igual que la creacion de tenant de
// S1.1) -- el token JWT se pega a mano. El middleware de services/gateway
// es el MISMO que valida cualquier otro cliente HTTP; esto no es un atajo
// de seguridad, es la ausencia (documentada) del CU de emision de sesion.
@Component({
  selector: 'app-estado-tiempo-real',
  imports: [FormsModule],
  templateUrl: './estado-tiempo-real.html',
})
export class EstadoTiempoReal implements OnDestroy {
  protected readonly tokenJwt = signal('');
  protected readonly conectado = signal(false);
  protected readonly error = signal<string | null>(null);
  // Posicion fija, mas reciente primero -- glanceability (RF-O04): no hace
  // falta desplazarse para ver el ultimo cambio, que es el dato relevante
  // de un vistazo. Se limita el historial visible, no es un log completo.
  protected readonly eventos = signal<EventoEstadoVuelo[]>([]);

  private socket: WebSocket | null = null;

  protected conectar(): void {
    this.error.set(null);
    this.eventos.set([]);
    const socket = new WebSocket(
      `${WS_BASE_URL}/vuelos/ws/estado?token=${encodeURIComponent(this.tokenJwt())}`,
    );

    socket.onopen = () => this.conectado.set(true);
    socket.onclose = (evento) => {
      this.conectado.set(false);
      if (evento.code >= 4000) {
        this.error.set(`Conexion rechazada (codigo ${evento.code})`);
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
