import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';

@Component({
  selector: 'app-restablecer',
  imports: [FormsModule],
  templateUrl: './restablecer.html',
  styleUrl: './restablecer.scss',
})
export class Restablecer {
  protected readonly passwordNueva = signal('');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly listo = signal(false);

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly token = inject(ActivatedRoute).snapshot.queryParamMap.get('token') ?? '';

  protected enviar(): void {
    if (!this.token) {
      this.error.set('El enlace no incluye un token valido.');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);

    this.auth.restablecerPassword(this.token, this.passwordNueva()).subscribe({
      next: () => {
        this.enviando.set(false);
        this.listo.set(true);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(
          err.status === 410
            ? 'Este enlace ya vencio o ya se uso. Solicita uno nuevo.'
            : mensajeDeError(err),
        );
        this.enviando.set(false);
      },
    });
  }

  protected irAlLogin(): void {
    this.router.navigate(['/login']);
  }
}
