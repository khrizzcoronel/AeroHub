import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PantallaConsultada, PantallaService } from '../pantalla.service';

// URL del backend compuesto -- ver el comentario en pantalla.service.ts.
const WS_BASE_URL = 'ws://localhost:8000';

// Cadencia de heartbeat del reproductor (RF-O07). Bien por debajo del
// umbral de deteccion de sin-senal (RNF-R04, 60s) para dejar margen ante
// cortes de red intermitentes.
const INTERVALO_HEARTBEAT_MS = 15_000;

interface EventoPlantillaPantalla {
  pantalla_id: string;
  plantilla_id: string;
  definicion_json: Record<string, unknown>;
  ocurrido_en: string;
}

// No hay login real todavia (mismo estado que apps/web, S1.1/S1.2) -- el
// token JWT se pega a mano. El middleware del gateway es el mismo que
// valida cualquier otro cliente HTTP.
@Component({
  selector: 'app-pantalla-player',
  imports: [CommonModule, FormsModule],
  templateUrl: './pantalla-player.html',
})
export class PantallaPlayer implements OnDestroy {
  protected readonly codigo = signal('');
  protected readonly tokenJwt = signal('');
  protected readonly conectado = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly pantalla = signal<PantallaConsultada | null>(null);
  protected readonly definicionJson = signal<Record<string, unknown> | null>(null);
  protected readonly ultimaActualizacion = signal<string | null>(null);

  private readonly pantallaService = inject(PantallaService);
  private socket: WebSocket | null = null;
  private idIntervaloHeartbeat: ReturnType<typeof setInterval> | null = null;

  protected conectar(): void {
    this.error.set(null);
    this.pantallaService.obtenerPorCodigo(this.codigo(), this.tokenJwt()).subscribe({
      next: (resultado) => {
        this.pantalla.set(resultado);
        this.definicionJson.set(resultado.definicion_json);
        this.abrirSocket(resultado);
        this.iniciarHeartbeat(resultado.id);
      },
      error: () => this.error.set('No se pudo cargar la pantalla (codigo o token invalido)'),
    });
  }

  private abrirSocket(resultado: PantallaConsultada): void {
    const socket = new WebSocket(
      `${WS_BASE_URL}/fids/ws/pantalla/${resultado.codigo}?token=${encodeURIComponent(this.tokenJwt())}`,
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
      const evento = JSON.parse(mensaje.data) as EventoPlantillaPantalla;
      this.definicionJson.set(evento.definicion_json);
      this.ultimaActualizacion.set(evento.ocurrido_en);
    };

    this.socket = socket;
  }

  private iniciarHeartbeat(pantallaId: string): void {
    const enviar = () =>
      this.pantallaService
        .enviarHeartbeat(pantallaId, this.tokenJwt())
        .subscribe({ error: () => this.error.set('Fallo el heartbeat') });
    enviar();
    this.idIntervaloHeartbeat = setInterval(enviar, INTERVALO_HEARTBEAT_MS);
  }

  protected desconectar(): void {
    this.socket?.close();
    this.socket = null;
    if (this.idIntervaloHeartbeat !== null) {
      clearInterval(this.idIntervaloHeartbeat);
      this.idIntervaloHeartbeat = null;
    }
    this.conectado.set(false);
  }

  // El layout de definicion_json es un objeto JSON libre (domain solo
  // exige ausencia de PII, ver aerohub_fids/domain/plantilla.py) -- la
  // convencion "filas: [{texto}]" usada aqui es la que producen las
  // plantillas de ejemplo, no una restriccion del backend. Cualquier otra
  // forma cae al respaldo de JSON crudo.
  protected filasDeTexto(): string[] | null {
    const definicion = this.definicionJson();
    const filas = definicion?.['filas'];
    if (!Array.isArray(filas)) {
      return null;
    }
    const textos = filas
      .filter((fila): fila is { texto: unknown } => typeof fila === 'object' && fila !== null && 'texto' in fila)
      .map((fila) => String((fila as { texto: unknown }).texto));
    return textos.length === filas.length ? textos : null;
  }

  ngOnDestroy(): void {
    this.desconectar();
  }
}
