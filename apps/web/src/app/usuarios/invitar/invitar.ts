import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService, mensajeDeError } from '../../auth/auth.service';

@Component({
  selector: 'app-invitar',
  imports: [FormsModule],
  templateUrl: './invitar.html',
  styleUrl: './invitar.scss',
})
export class Invitar {
  protected readonly email = signal('');
  protected readonly rolCodigo = signal('role_ramp_agent');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly invitacionId = signal<string | null>(null);

  private readonly auth = inject(AuthService);

  protected enviar(): void {
    this.enviando.set(true);
    this.error.set(null);
    this.invitacionId.set(null);

    this.auth.invitarUsuario(this.email(), this.rolCodigo()).subscribe({
      next: (resultado) => {
        this.invitacionId.set(resultado.invitacion_id);
        this.email.set('');
        this.enviando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.enviando.set(false);
      },
    });
  }
}
