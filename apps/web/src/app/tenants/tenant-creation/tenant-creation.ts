import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { CrearTenantResponse, TenantService } from '../tenant.service';

// Sprint S1.1 no incluye el CU de emision de credenciales de sesion (queda
// para el sprint del login real) -- por eso este formulario pide el JWT de
// role_platform_admin como texto en vez de autenticar al usuario. No es un
// atajo de seguridad: es exactamente el mismo middleware de
// services/gateway validando el mismo token que cualquier otro cliente
// HTTP tendria que enviar.
@Component({
  selector: 'app-tenant-creation',
  imports: [FormsModule],
  templateUrl: './tenant-creation.html',
})
export class TenantCreation {
  protected readonly tokenJwt = signal('');
  protected readonly codigo = signal('');
  protected readonly razonSocial = signal('');
  // string, no number -- ver el comentario en tenant.service.ts sobre
  // Number.MAX_SAFE_INTEGER. El input HTML es type="text" (nunca
  // type="number", que ya redondea el valor en el propio DOM antes de que
  // este codigo lo vea).
  protected readonly aeropuertoId = signal('');
  protected readonly planId = signal('');
  protected readonly emailAdmin = signal('');
  protected readonly nombreAdmin = signal('');

  protected readonly enviando = signal(false);
  protected readonly resultado = signal<CrearTenantResponse | null>(null);
  protected readonly error = signal<string | null>(null);

  private readonly tenantService = inject(TenantService);

  protected enviar(): void {
    const aeropuertoId = this.aeropuertoId();
    const planId = this.planId();
    if (!aeropuertoId || !planId) {
      this.error.set('aeropuerto_id y plan_id son obligatorios');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.tenantService
      .crearTenant(
        {
          codigo: this.codigo(),
          razon_social: this.razonSocial(),
          aeropuerto_id: aeropuertoId,
          plan_id: planId,
          email_admin: this.emailAdmin(),
          nombre_admin: this.nombreAdmin(),
        },
        this.tokenJwt(),
      )
      .subscribe({
        next: (respuesta) => {
          this.resultado.set(respuesta);
          this.enviando.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(
            typeof err.error?.detail === 'string'
              ? err.error.detail
              : `Error ${err.status}: ${err.message}`,
          );
          this.enviando.set(false);
        },
      });
  }
}
