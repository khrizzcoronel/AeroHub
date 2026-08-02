import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-recuperar',
  imports: [FormsModule, RouterLink],
  templateUrl: './recuperar.html',
  styleUrl: './recuperar.scss',
})
export class Recuperar {
  protected readonly email = signal('');
  protected readonly enviando = signal(false);
  protected readonly enviado = signal(false);

  private readonly auth = inject(AuthService);

  protected enviar(): void {
    this.enviando.set(true);
    // FR-021: la respuesta es siempre la misma, exista o no la cuenta --
    // por eso este componente no distingue exito de fallo, solo "se
    // envio la solicitud".
    this.auth.solicitarRecuperacion(this.email()).subscribe({
      next: () => this.finalizar(),
      error: () => this.finalizar(),
    });
  }

  private finalizar(): void {
    this.enviando.set(false);
    this.enviado.set(true);
  }
}
