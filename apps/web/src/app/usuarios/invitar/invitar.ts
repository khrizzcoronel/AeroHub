import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService, mensajeDeError } from '../../auth/auth.service';

import { ToastService } from '../../shared/toast.service';

@Component({
  selector: 'app-invitar',
  imports: [FormsModule],
  templateUrl: './invitar.html',
  styleUrl: './invitar.scss',
})
export class Invitar {
  @Output() cerrar = new EventEmitter<void>();
  @Output() enviado = new EventEmitter<void>();

  protected readonly email = signal('');
  protected readonly rolCodigo = signal('role_ramp_agent');
  protected readonly enviando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly invitacionId = signal<string | null>(null);

  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);

  protected enviar(): void {
    const emailClean = this.email().trim();
    if (!emailClean) {
      this.error.set('Debe ingresar un correo electrónico válido.');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    this.invitacionId.set(null);

    this.auth.invitarUsuario(emailClean, this.rolCodigo()).subscribe({
      next: (resultado) => {
        this.invitacionId.set(resultado.invitacion_id);
        this.toast.mostrar('Invitación enviada por correo electrónico con éxito', 'exito');
        this.email.set('');
        this.enviando.set(false);
        this.enviado.emit();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.enviando.set(false);
      },
    });
  }
}
