import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Aeropuerto, CrearTenantResponse, Plan, TenantService } from '../tenant.service';

// Sprint S1.10: el token ya no se pega a mano -- sale del interceptor de
// AuthService a partir de la sesion real de quien esta autenticado
// (FR-029). Antes de S1.10 este formulario pedia el JWT como texto; ver
// historial de este archivo para ese estado transitorio de S1.1.
//
// Post S1.13: aeropuerto_id/plan_id dejan de ser campos de texto libre --
// se seleccionan de las listas reales de GET /catalogo/aeropuertos y
// GET /catalogo/planes.
//
// Post-workpanel: dejo de ser una vista con ruta propia -- se embebe
// dentro del modal de tenant-list (pedido explicito del usuario: crear
// tenant no debe navegar a otra pagina). `cerrar` se emite tanto al
// cancelar como despues de ver el resultado exitoso; tenant-list decide
// si recarga la lista.
@Component({
  selector: 'app-tenant-creation',
  imports: [FormsModule],
  templateUrl: './tenant-creation.html',
  styleUrl: './tenant-creation.scss',
})
export class TenantCreation {
  @Output() cerrar = new EventEmitter<void>();

  protected readonly codigo = signal('');
  protected readonly razonSocial = signal('');
  protected readonly aeropuertoId = signal('');
  protected readonly planId = signal('');
  protected readonly emailAdmin = signal('');
  protected readonly nombreAdmin = signal('');

  protected readonly aeropuertos = signal<Aeropuerto[]>([]);
  protected readonly planes = signal<Plan[]>([]);

  protected readonly enviando = signal(false);
  protected readonly resultado = signal<CrearTenantResponse | null>(null);
  protected readonly error = signal<string | null>(null);

  private readonly tenantService = inject(TenantService);

  constructor() {
    this.tenantService.listarAeropuertos().subscribe({ next: (r) => this.aeropuertos.set(r) });
    this.tenantService.listarPlanes().subscribe({ next: (r) => this.planes.set(r) });
  }

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
      .crearTenant({
        codigo: this.codigo(),
        razon_social: this.razonSocial(),
        aeropuerto_id: aeropuertoId,
        plan_id: planId,
        email_admin: this.emailAdmin(),
        nombre_admin: this.nombreAdmin(),
      })
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
