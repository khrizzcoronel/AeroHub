import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';

@Component({
  selector: 'app-aceptar-invitacion',
  imports: [FormsModule, RouterLink],
  templateUrl: './aceptar-invitacion.html',
  styleUrl: './aceptar-invitacion.scss',
})
export class AceptarInvitacion {
  protected readonly nombre = signal('');
  protected readonly password = signal('');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);

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

    this.auth.aceptarInvitacion(this.token, this.nombre(), this.password()).subscribe({
      next: () => {
        this.enviando.set(false);
        this.router.navigate(['/login']);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(
          err.status === 410
            ? 'Esta invitacion ya vencio o ya se uso. Pedile a tu administrador que envie una nueva.'
            : mensajeDeError(err),
        );
        this.enviando.set(false);
      },
    });
  }
}
