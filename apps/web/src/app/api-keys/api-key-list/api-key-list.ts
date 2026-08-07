import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiKeyResumen, ApiKeyService } from '../api-key.service';
import { ToastService } from '../../shared/toast.service';
import { mensajeDeError } from '../../auth/auth.service';

@Component({
  selector: 'app-api-key-list',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './api-key-list.html',
  styleUrl: './api-key-list.scss',
})
export class ApiKeyList implements OnInit {
  private readonly apiKeyService = inject(ApiKeyService);
  private readonly toast = inject(ToastService);

  protected readonly apiKeys = signal<ApiKeyResumen[]>([]);
  protected readonly cargando = signal(false);
  protected readonly procesando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly filtroPrefijo = signal('');

  // Modal para mostrar el secreto recién generado (una sola vez)
  protected readonly secretoGenerado = signal<string | null>(null);

  // Ver detalles (Fase 4 de docs/diseno/PLAN_CORRECCION_MODULOS.md, item
  // 12): rotar/revocar viven dentro del detalle, nunca como botones de
  // fila -- sin edición de información (una llave no se edita).
  protected readonly apiKeyViendoDetalle = signal<ApiKeyResumen | null>(null);

  // Paginación
  protected readonly paginaActual = signal(1);
  protected readonly registrosPorPagina = 10;

  protected readonly apiKeysFiltradas = computed(() => {
    const p = this.filtroPrefijo().trim().toLowerCase();
    if (!p) return this.apiKeys();
    return this.apiKeys().filter((k) => k.prefijo.toLowerCase().includes(p));
  });

  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.apiKeysFiltradas().length / this.registrosPorPagina)),
  );

  protected readonly apiKeysPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * this.registrosPorPagina;
    return this.apiKeysFiltradas().slice(inicio, inicio + this.registrosPorPagina);
  });

  ngOnInit(): void {
    this.cargarApiKeys();
  }

  protected cargarApiKeys(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.apiKeyService.listarApiKeys().subscribe({
      next: (lista) => {
        this.apiKeys.set(lista);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected crearNuevaApiKey(): void {
    this.procesando.set(true);
    this.error.set(null);
    this.apiKeyService.crearApiKey().subscribe({
      next: (res) => {
        this.procesando.set(false);
        this.secretoGenerado.set(res.api_key_en_claro);
        this.cargarApiKeys();
        this.toast.mostrar('Nueva API Key generada con éxito', 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.procesando.set(false);
      },
    });
  }

  protected rotar(key: ApiKeyResumen): void {
    this.procesando.set(true);
    this.error.set(null);
    this.apiKeyService.rotarApiKey(key.id).subscribe({
      next: (res) => {
        this.procesando.set(false);
        this.apiKeyViendoDetalle.set(null);
        this.secretoGenerado.set(res.api_key_en_claro);
        this.cargarApiKeys();
        this.toast.mostrar(`API Key con prefijo ${key.prefijo} rotada con éxito`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.procesando.set(false);
      },
    });
  }

  protected revocar(key: ApiKeyResumen): void {
    this.procesando.set(true);
    this.error.set(null);
    this.apiKeyService.revocarApiKey(key.id).subscribe({
      next: () => {
        this.procesando.set(false);
        this.apiKeyViendoDetalle.set(null);
        this.cargarApiKeys();
        this.toast.mostrar(`API Key ${key.prefijo} revocada de inmediato`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.procesando.set(false);
      },
    });
  }

  protected copiarAlPortapapeles(texto: string): void {
    navigator.clipboard.writeText(texto).then(() => {
      this.toast.mostrar('Copiado al portapapeles', 'info');
    });
  }

  protected cerrarModalSecreto(): void {
    this.secretoGenerado.set(null);
  }

  protected verDetalle(key: ApiKeyResumen): void {
    this.apiKeyViendoDetalle.set(key);
  }

  protected cerrarDetalle(): void {
    this.apiKeyViendoDetalle.set(null);
  }

  protected claseEstado(estado: string): string {
    switch (estado) {
      case 'activa':
        return 'ah-pill--ok';
      case 'revocada':
        return 'ah-pill--critico';
      default:
        return 'ah-pill--atencion';
    }
  }

  protected paginaAnterior(): void {
    if (this.paginaActual() > 1) {
      this.paginaActual.update((p) => p - 1);
    }
  }

  protected paginaSiguiente(): void {
    if (this.paginaActual() < this.totalPaginas()) {
      this.paginaActual.update((p) => p + 1);
    }
  }
}
