import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';

@Component({
  selector: 'app-cambiar-password',
  imports: [FormsModule],
  templateUrl: './cambiar-password.html',
  styleUrl: './cambiar-password.scss',
})
export class CambiarPassword {
  protected readonly passwordActual = signal('');
  protected readonly passwordNueva = signal('');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected enviar(): void {
    this.enviando.set(true);
    this.error.set(null);

    this.auth.cambiarPassword(this.passwordActual(), this.passwordNueva()).subscribe({
      next: () => {
        this.enviando.set(false);
        this.router.navigate(['/']);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.enviando.set(false);
      },
    });
  }
}
