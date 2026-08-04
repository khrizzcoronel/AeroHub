import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Aeropuerto, CrearTenantResponse, Plan, TenantService } from '../tenant.service';
import { ToastService } from '../../shared/toast.service';
import { mensajeDeError } from '../../auth/auth.service';

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
  protected readonly copiado = signal(false);

  protected readonly errorCodigo = signal<string | null>(null);
  protected readonly errorEmail = signal<string | null>(null);
  protected readonly validandoCodigo = signal(false);
  protected readonly validandoEmail = signal(false);

  private timerCodigo: any;
  private timerEmail: any;

  private readonly tenantService = inject(TenantService);

  protected onCodigoInput(val: string): void {
    this.codigo.set(val);
    this.errorCodigo.set(null);
    clearTimeout(this.timerCodigo);
    const codigoClean = val.trim().toUpperCase();
    if (codigoClean.length >= 2) {
      this.validandoCodigo.set(true);
      this.timerCodigo = setTimeout(() => {
        this.tenantService.validarDisponibilidad(codigoClean, undefined).subscribe({
          next: (r) => {
            this.validandoCodigo.set(false);
            if (!r.codigo_disponible) {
              this.errorCodigo.set(r.codigo_mensaje ?? 'El código ya está en uso');
            }
          },
          error: () => this.validandoCodigo.set(false),
        });
      }, 350);
    }
  }

  protected onEmailInput(val: string): void {
    this.emailAdmin.set(val);
    this.errorEmail.set(null);
    clearTimeout(this.timerEmail);
    const emailClean = val.trim().toLowerCase();
    if (emailClean.includes('@') && emailClean.includes('.')) {
      this.validandoEmail.set(true);
      this.timerEmail = setTimeout(() => {
        this.tenantService.validarDisponibilidad(undefined, emailClean).subscribe({
          next: (r) => {
            this.validandoEmail.set(false);
            if (!r.email_disponible) {
              this.errorEmail.set(r.email_mensaje ?? 'El correo ya se encuentra registrado');
            }
          },
          error: () => this.validandoEmail.set(false),
        });
      }, 350);
    }
  }

  private readonly toast = inject(ToastService);

  protected copiarPassword(): void {
    const pwd = this.resultado()?.password_temporal;
    if (pwd) {
      navigator.clipboard.writeText(pwd);
      this.copiado.set(true);
      this.toast.mostrar('Contraseña temporal copiada al portapapeles', 'info');
      setTimeout(() => this.copiado.set(false), 3000);
    }
  }

  constructor() {
    this.tenantService.listarAeropuertos().subscribe({ next: (r) => this.aeropuertos.set(r) });
    this.tenantService.listarPlanes().subscribe({ next: (r) => this.planes.set(r) });
  }

  protected enviar(): void {
    if (this.errorCodigo() || this.errorEmail()) {
      this.error.set('Por favor corrija los datos duplicados indicados antes de continuar.');
      return;
    }
    const aeropuertoId = this.aeropuertoId();
    const planId = this.planId();
    if (!aeropuertoId || !planId) {
      this.error.set('Debe seleccionar un aeropuerto y un plan válidos de la lista.');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.tenantService
      .crearTenant({
        codigo: this.codigo().trim().toUpperCase(),
        razon_social: this.razonSocial().trim(),
        aeropuerto_id: aeropuertoId,
        plan_id: planId,
        email_admin: this.emailAdmin().trim(),
        nombre_admin: this.nombreAdmin().trim(),
      })
      .subscribe({
        next: (respuesta) => {
          this.resultado.set(respuesta);
          this.enviando.set(false);
          this.toast.mostrar('Organización aprovisionada con éxito', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(mensajeDeError(err));
          this.enviando.set(false);
        },
      });
  }
}
