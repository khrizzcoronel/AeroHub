import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './auth/auth.service';

@Component({
  selector: 'app-inicio',
  standalone: true,
  template: '',
})
export class InicioComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    const perfil = this.auth.perfil();
    if (!perfil) {
      this.router.navigate(['/login']);
      return;
    }

    if (perfil.debe_cambiar_password) {
      this.router.navigate(['/cambiar-password']);
      return;
    }

    const scopes = perfil.scopes ?? [];
    if (scopes.includes('tenants:administrar') || scopes.includes('tenants:crear')) {
      this.router.navigate(['/tenants']);
      return;
    }

    if (perfil.rol_codigo === 'role_tenant_admin') {
      this.router.navigate(['/usuarios']);
      return;
    }

    const modulosConRuta = perfil.modulos_visibles.filter((m) => m.ruta !== null);
    if (modulosConRuta.length > 0 && modulosConRuta[0].ruta) {
      this.router.navigate([modulosConRuta[0].ruta]);
      return;
    }

    this.router.navigate(['/licencias']);
  }
}
