import { Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly perfil = this.auth.perfil;
  // Solo modulos con vista propia en apps/web -- el resto (M2/M7/M8/M9)
  // se opera desde otros paneles (contracts/perfil-acceso.md, FR-028: el
  // shell no decide permisos, solo filtra lo que no tiene ruta aqui).
  protected readonly modulosConVista = computed(
    () => this.perfil()?.modulos_visibles.filter((m) => m.ruta !== null) ?? [],
  );

  protected cerrarSesion(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
