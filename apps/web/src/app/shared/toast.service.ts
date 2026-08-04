import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  mensaje: string;
  tipo: 'exito' | 'error' | 'aviso' | 'info';
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private contador = 0;

  mostrar(mensaje: string, tipo: 'exito' | 'error' | 'aviso' | 'info' = 'exito', duracionMs = 4000): void {
    const id = ++this.contador;
    const nuevoToast: Toast = { id, mensaje, tipo };
    this.toasts.update((lista) => [...lista, nuevoToast]);

    setTimeout(() => {
      this.quitar(id);
    }, duracionMs);
  }

  quitar(id: number): void {
    this.toasts.update((lista) => lista.filter((t) => t.id !== id));
  }
}
