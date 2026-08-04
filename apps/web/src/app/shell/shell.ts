import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ActivatedRoute,
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { filter } from 'rxjs';
import { AuthService, mensajeDeError } from '../auth/auth.service';
import { ToastService } from '../shared/toast.service';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly toastService = inject(ToastService);

  protected readonly toasts = this.toastService.toasts;
  protected readonly perfil = this.auth.perfil;
  // Solo modulos con vista propia en apps/web -- el resto (M2/M7/M8/M9)
  // se opera desde otros paneles (contracts/perfil-acceso.md, FR-028: el
  // shell no decide permisos, solo filtra lo que no tiene ruta aqui).
  // Sprint S1.19 -- role_support tiene M9 en modulos_visibles (soporte
  // opera tickets, no compliance) pero ningun scope compliance:* --
  // sin este filtro veria el enlace y cada llamada del panel devolveria
  // 403 al cargar. Mismo tipo de exclusion que role_platform_admin en
  // S1.11, aplicada aqui por modulo en vez de por rol completo.
  protected readonly modulosConVista = computed(() => {
    const scopes = this.perfil()?.scopes ?? [];
    return (
      this.perfil()?.modulos_visibles.filter(
        (m) => m.ruta !== null && (m.codigo !== 'M9' || scopes.includes('compliance:leer')),
      ) ?? []
    );
  });

  // Tenants no es un modulo M1-M9 (no aparece en modulos_visibles) --
  // se muestra segun el scope real del rol, igual criterio que el resto
  // del menu: si no puede crear ni administrar tenants, no ve el enlace.
  protected readonly puedeVerTenants = computed(() => {
    const scopes = this.perfil()?.scopes ?? [];
    return scopes.includes('tenants:crear') || scopes.includes('tenants:administrar');
  });

  // role_platform_admin tiene los scopes usuarios:administrar/api-keys:administrar
  // pero para SU rol -- no tiene tenant propio (tenant_id NULL), asi que
  // /usuarios y /api-keys (ambos filtrados por contexto_tenant_id()) le
  // devuelven 500 (ContextoTenantAusente sin capturar). Excluido explicitamente.
  protected readonly puedeVerUsuarios = computed(() => {
    const rol = this.perfil()?.rol_codigo;
    return rol === 'role_tenant_admin';
  });

  protected readonly puedeVerApiKeys = computed(() => {
    const rol = this.perfil()?.rol_codigo;
    const scopes = this.perfil()?.scopes ?? [];
    return rol !== 'role_platform_admin' && scopes.includes('api-keys:administrar');
  });

  protected readonly puedeVerLicencias = computed(() => {
    const tenantId = this.perfil()?.tenant_id;
    return !!tenantId;
  });

  // Sprint S1.17 -- tarifarios/conciliación no es un modulo M1-M9 propio
  // (vive dentro de M5, cuya unica ruta ya esta ocupada por
  // /billing/facturas -- modulosConVista solo admite una ruta por
  // modulo), mismo mecanismo que usuarios/api-keys/licencias.
  protected readonly puedeVerTarifarios = computed(() => {
    const scopes = this.perfil()?.scopes ?? [];
    return scopes.includes('billing:escribir');
  });

  // Sprint S1.18 -- informes operativos (RF-I01-04): un enlace auxiliar
  // por modulo, mismo mecanismo que puedeVerTarifarios (M1/M3/M4/M5 ya
  // tienen su ruta principal ocupada por modulosConVista).
  protected readonly puedeVerInformesVuelos = computed(() =>
    (this.perfil()?.scopes ?? []).includes('vuelos:leer'),
  );
  protected readonly puedeVerInformesPuertas = computed(() =>
    (this.perfil()?.scopes ?? []).includes('puertas:leer'),
  );
  protected readonly puedeVerInformesRampa = computed(() =>
    (this.perfil()?.scopes ?? []).includes('rampa:leer'),
  );
  protected readonly puedeVerInformesBilling = computed(() =>
    (this.perfil()?.scopes ?? []).includes('billing:leer'),
  );
  protected readonly puedeVerInformesTenants = computed(() =>
    (this.perfil()?.scopes ?? []).includes('tenants:administrar'),
  );
  protected readonly puedeVerInformesCompliance = computed(() =>
    (this.perfil()?.scopes ?? []).includes('compliance:leer'),
  );

  // Sprint S1.15 -- endpoint huerfano POST /auth/solicitar-verificacion
  // (ya existia desde S1.10, sin ningun boton que lo invocara). Vive en
  // el shell, no en la vista publica /verificar-correo, porque el
  // endpoint opera sobre la sesion ya autenticada (research.md Decision
  // 4 de specs/017-contrato-api-superficie-aodb).
  protected readonly mostrarBannerVerificacion = computed(
    () => this.perfil()?.email_verificado === false,
  );
  protected readonly enviandoVerificacion = signal(false);

  // Titulo de la vista actual (post S1.13): antes la barra lateral no
  // indicaba en que pantalla estaba la persona -- notorio en roles como
  // role_platform_admin, cuyo menu de modulos queda vacio (no opera
  // ningun M1-M9) y no tenia ninguna otra senal de ubicacion. Se lee de
  // `data.title` de la ruta activa (mas profunda), poblado en
  // app.routes.ts -- no depende de modulos_visibles porque cubre tambien
  // vistas de identidad/tenancy que no son un modulo M1-M9.
  protected readonly tituloVistaActual = signal<string>('');

  constructor() {
    this.router.events
      .pipe(
        filter((evento): evento is NavigationEnd => evento instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(() => {
        let ruta = this.activatedRoute;
        while (ruta.firstChild) {
          ruta = ruta.firstChild;
        }
        this.tituloVistaActual.set((ruta.snapshot.data['title'] as string) ?? '');
      });
  }

  protected cerrarSesion(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }

  protected reenviarVerificacion(): void {
    this.enviandoVerificacion.set(true);
    this.auth.solicitarVerificacion().subscribe({
      next: () => {
        this.enviandoVerificacion.set(false);
        this.toastService.mostrar('Correo de verificación reenviado', 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.enviandoVerificacion.set(false);
        this.toastService.mostrar(mensajeDeError(err), 'error');
      },
    });
  }
}
