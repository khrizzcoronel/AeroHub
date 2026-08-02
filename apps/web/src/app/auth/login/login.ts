import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';

interface TiraDeVuelo {
  vuelo: string;
  ruta: string;
  estado: string;
  activa: boolean;
}

// Contenido decorativo del panel izquierdo (motivo visual: tira de
// progreso de vuelo de una torre de control) -- sin significado
// operativo, solo ambientacion de marca.
const TIRAS: TiraDeVuelo[] = [
  { vuelo: 'AH 214', ruta: 'MEC -> UIO', estado: 'ABORDANDO', activa: true },
  { vuelo: 'AH 118', ruta: 'UIO -> MEC', estado: 'EN RUTA', activa: false },
  { vuelo: 'AH 305', ruta: 'MEC -> GYE', estado: 'PROGRAMADO', activa: false },
  { vuelo: 'AH 072', ruta: 'GYE -> MEC', estado: 'ATERRIZADO', activa: false },
  { vuelo: 'AH 441', ruta: 'MEC -> UIO', estado: 'RETRASADO', activa: false },
  { vuelo: 'AH 118', ruta: 'UIO -> MEC', estado: 'EN RUTA', activa: false },
];

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  protected readonly tiras = TIRAS;
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected enviar(): void {
    this.enviando.set(true);
    this.error.set(null);

    this.auth.login(this.email(), this.password()).subscribe({
      next: (respuesta) => {
        this.enviando.set(false);
        if (respuesta.perfil.debe_cambiar_password) {
          this.router.navigate(['/cambiar-password']);
        } else {
          this.router.navigate(['/']);
        }
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.enviando.set(false);
      },
    });
  }
}
