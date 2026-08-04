import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';
import { ToastService } from '../../shared/toast.service';

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
  private readonly toast = inject(ToastService);

  protected enviar(): void {
    const pwdActual = this.passwordActual().trim();
    const pwdNueva = this.passwordNueva().trim();

    if (!pwdActual || !pwdNueva) {
      this.error.set('Debe ingresar la contraseña actual y la nueva contraseña.');
      return;
    }

    if (pwdActual === pwdNueva) {
      this.error.set('La nueva contraseña debe ser diferente a la contraseña temporal.');
      return;
    }

    this.enviando.set(true);
    this.error.set(null);

    this.auth.cambiarPassword(pwdActual, pwdNueva).subscribe({
      next: () => {
        this.enviando.set(false);
        this.toast.mostrar('Contraseña actualizada con éxito', 'exito');
        this.router.navigate(['/']);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.enviando.set(false);
      },
    });
  }
}
