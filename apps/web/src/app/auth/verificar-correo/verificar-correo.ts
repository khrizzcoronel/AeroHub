import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService, mensajeDeError } from '../auth.service';

type Estado = 'verificando' | 'exito' | 'error';

@Component({
  selector: 'app-verificar-correo',
  imports: [RouterLink],
  templateUrl: './verificar-correo.html',
  styleUrl: './verificar-correo.scss',
})
export class VerificarCorreo implements OnInit {
  protected readonly estado = signal<Estado>('verificando');
  protected readonly mensaje = signal('');

  private readonly auth = inject(AuthService);
  private readonly token = inject(ActivatedRoute).snapshot.queryParamMap.get('token') ?? '';

  ngOnInit(): void {
    if (!this.token) {
      this.estado.set('error');
      this.mensaje.set('El enlace no incluye un token valido.');
      return;
    }
    this.auth.verificarCorreo(this.token).subscribe({
      next: () => this.estado.set('exito'),
      error: (err: HttpErrorResponse) => {
        this.estado.set('error');
        this.mensaje.set(
          err.status === 410
            ? 'Este enlace ya vencio o ya se uso. Pedi uno nuevo desde tu cuenta.'
            : mensajeDeError(err),
        );
      },
    });
  }
}
