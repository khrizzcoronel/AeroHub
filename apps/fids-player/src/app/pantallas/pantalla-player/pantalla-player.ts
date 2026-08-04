import { CommonModule } from '@angular/common';
import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PantallaConsultada, PantallaService } from '../pantalla.service';

// URL del backend compuesto -- ver el comentario en pantalla.service.ts.
const WS_BASE_URL = 'ws://localhost:8000';

// Cadencia de heartbeat del reproductor (RF-O07). Bien por debajo del
// umbral de deteccion de sin-senal (RNF-R04, 60s) para dejar margen ante
// cortes de red intermitentes.
const INTERVALO_HEARTBEAT_MS = 15_000;

// Sprint S1.14, research.md Decision 2: dos heartbeats fallidos
// consecutivos (30s en el peor caso) antes de declarar "sin senal" --
// un solo fallo no dispara el modo, evita el parpadeo ante un corte de
// red intermitente muy breve (spec.md Edge Cases).
const FALLOS_HEARTBEAT_PARA_SIN_SENAL = 2;

interface EventoPlantillaPantalla {
  pantalla_id: string;
  plantilla_id: string;
  definicion_json: Record<string, unknown>;
  ocurrido_en: string;
}

type ModoPantalla = 'configuracion' | 'reproduccion' | 'sin_senal';

// No hay login real todavia (mismo estado que apps/web, S1.1/S1.2) -- el
// token JWT se pega a mano. El middleware del gateway es el mismo que
// valida cualquier otro cliente HTTP. Sprint S1.14 (research.md Decision
// 6): esto NO es deuda tecnica aqui -- esta app no tiene AuthService ni
// login humano, es el mecanismo real de configuracion de una pantalla
// fisica, se mantiene funcionalmente igual, solo se le da una
// composicion visual propia (modo 'configuracion').
@Component({
  selector: 'app-pantalla-player',
  imports: [CommonModule, FormsModule],
  templateUrl: './pantalla-player.html',
  styleUrl: './pantalla-player.scss',
})
export class PantallaPlayer implements OnDestroy {
  protected readonly codigo = signal('');
  protected readonly tokenJwt = signal('');
  protected readonly conectado = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly pantalla = signal<PantallaConsultada | null>(null);
  protected readonly definicionJson = signal<Record<string, unknown> | null>(null);
  protected readonly ultimaActualizacion = signal<string | null>(null);

  // Sprint S1.14 (research.md Decision 2) -- verdadero cuando el WS
  // cerro con un codigo de rechazo explicito, o cuando el heartbeat
  // acumulo FALLOS_HEARTBEAT_PARA_SIN_SENAL fallos consecutivos.
  protected readonly senalPerdida = signal(false);

  // Sprint S1.14 (research.md Decision 1) -- un solo signal derivado
  // para los 3 modos mutuamente excluyentes; senalPerdida se evalua
  // primero porque solo puede volverse verdadero DESPUES de conectar
  // (conectado ya esta en false en ese momento, ver abrirSocket/onclose).
  protected readonly modoActual = computed<ModoPantalla>(() => {
    if (this.senalPerdida()) return 'sin_senal';
    return this.conectado() ? 'reproduccion' : 'configuracion';
  });

  private readonly pantallaService = inject(PantallaService);
  private socket: WebSocket | null = null;
  private idIntervaloHeartbeat: ReturnType<typeof setInterval> | null = null;
  private fallosHeartbeatConsecutivos = 0;
  private cerrandoManualmente = false;

  protected conectar(): void {
    this.error.set(null);
    this.cerrandoManualmente = false;
    this.pantallaService.obtenerPorCodigo(this.codigo(), this.tokenJwt()).subscribe({
      next: (resultado) => {
        this.pantalla.set(resultado);
        this.definicionJson.set(resultado.definicion_json);
        this.senalPerdida.set(false);
        this.fallosHeartbeatConsecutivos = 0;
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
      if (this.cerrandoManualmente) {
        return;
      }
      if (evento.code >= 4000) {
        // Codigo de rechazo explicito (sesion invalida/vencida) --
        // senal de "sin senal" inmediata, sin esperar al heartbeat
        // (research.md Decision 2, parte (a)).
        this.senalPerdida.set(true);
      }
    };
    socket.onerror = () => this.error.set('Error de conexion WebSocket');
    socket.onmessage = (mensaje) => {
      const evento = JSON.parse(mensaje.data) as EventoPlantillaPantalla;
      this.definicionJson.set(evento.definicion_json);
      this.ultimaActualizacion.set(evento.ocurrido_en);
      // Recuperacion automatica (research.md Decision 3): un mensaje
      // real solo puede llegar si la conexion esta viva otra vez.
      this.senalPerdida.set(false);
      this.fallosHeartbeatConsecutivos = 0;
    };

    this.socket = socket;
  }

  private iniciarHeartbeat(pantallaId: string): void {
    const enviar = () =>
      this.pantallaService.enviarHeartbeat(pantallaId, this.tokenJwt()).subscribe({
        next: () => {
          // Heartbeat exitoso: recuperacion automatica (research.md
          // Decision 3) si estabamos en "sin senal".
          this.fallosHeartbeatConsecutivos = 0;
          this.senalPerdida.set(false);
        },
        error: () => {
          this.error.set('Fallo el heartbeat');
          this.fallosHeartbeatConsecutivos += 1;
          if (this.fallosHeartbeatConsecutivos >= FALLOS_HEARTBEAT_PARA_SIN_SENAL) {
            // research.md Decision 2, parte (b).
            this.senalPerdida.set(true);
          }
        },
      });
    enviar();
    this.idIntervaloHeartbeat = setInterval(enviar, INTERVALO_HEARTBEAT_MS);
  }

  protected desconectar(): void {
    this.cerrandoManualmente = true;
    this.socket?.close();
    this.socket = null;
    if (this.idIntervaloHeartbeat !== null) {
      clearInterval(this.idIntervaloHeartbeat);
      this.idIntervaloHeartbeat = null;
    }
    this.conectado.set(false);
    this.senalPerdida.set(false);
    this.fallosHeartbeatConsecutivos = 0;
  }

  // El layout de definicion_json es un objeto JSON libre (domain solo
  // exige ausencia de PII, ver aerohub_fids/domain/plantilla.py) -- la
  // convencion "filas: [{texto}]" usada aqui es la que producen las
  // plantillas de ejemplo, no una restriccion del backend. Cualquier otra
  // forma cae al respaldo legible (research.md Decision 7) -- ya no al
  // JSON crudo.
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
