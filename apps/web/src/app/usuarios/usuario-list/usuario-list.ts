import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { UsuarioResumen, UsuarioService } from '../usuario.service';
import { Invitar } from '../invitar/invitar';
import { ToastService } from '../../shared/toast.service';
import { mensajeDeError } from '../../auth/auth.service';

const ROLES_ETIQUETAS: Record<string, string> = {
  role_tenant_admin: 'Administrador de Tenant',
  role_operations_controller: 'Controlador de Operaciones',
  role_airline_coordinator: 'Coordinador de Aerolínea',
  role_ramp_agent: 'Agente de Rampa',
  role_billing_officer: 'Oficial de Facturación',
  role_tenant_analyst: 'Analista de Datos',
  role_regulatory_auditor: 'Auditor Regulatorio',
};

const ROLES_OPCIONES: { value: string; label: string }[] = [
  { value: '', label: 'Todos los roles' },
  ...Object.entries(ROLES_ETIQUETAS).map(([value, label]) => ({ value, label })),
];

@Component({
  selector: 'app-usuario-list',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, Invitar],
  templateUrl: './usuario-list.html',
  styleUrl: './usuario-list.scss',
})
export class UsuarioList implements OnInit {
  private readonly usuarioService = inject(UsuarioService);
  private readonly toast = inject(ToastService);

  protected readonly usuarios = signal<UsuarioResumen[]>([]);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly filtroBusqueda = signal('');
  protected readonly filtroRol = signal('');
  protected readonly mostrarModalInvitar = signal(false);
  protected readonly rolesOpciones = ROLES_OPCIONES;

  // Paginacion
  protected readonly paginaActual = signal(1);
  protected readonly registrosPorPagina = 10;

  protected readonly usuariosFiltrados = computed(() => {
    const q = this.filtroBusqueda().trim().toLowerCase();
    const rol = this.filtroRol();
    return this.usuarios().filter((u) => {
      const coincideTexto =
        !q ||
        u.nombre.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        (u.rol_nombre && u.rol_nombre.toLowerCase().includes(q));
      const coincideRol = !rol || u.rol_codigo === rol;
      return coincideTexto && coincideRol;
    });
  });

  protected readonly totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.usuariosFiltrados().length / this.registrosPorPagina)),
  );

  protected readonly usuariosPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * this.registrosPorPagina;
    return this.usuariosFiltrados().slice(inicio, inicio + this.registrosPorPagina);
  });

  ngOnInit(): void {
    this.cargarUsuarios();
  }

  protected cargarUsuarios(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.usuarioService.listarUsuarios().subscribe({
      next: (lista) => {
        this.usuarios.set(lista);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected cambiarFiltroRol(rol: string): void {
    this.filtroRol.set(rol);
    this.paginaActual.set(1);
  }

  protected cambiarFiltroBusqueda(q: string): void {
    this.filtroBusqueda.set(q);
    this.paginaActual.set(1);
  }

  protected abrirModalInvitar(): void {
    this.mostrarModalInvitar.set(true);
  }

  protected cerrarModalInvitar(): void {
    this.mostrarModalInvitar.set(false);
  }

  protected alEnviarInvitacion(): void {
    this.cargarUsuarios();
    this.cerrarModalInvitar();
  }

  protected etiquetaRol(rolCodigo: string | null): string {
    if (!rolCodigo) return 'Sin rol';
    return ROLES_ETIQUETAS[rolCodigo] || rolCodigo;
  }

  protected claseEstado(estado: string): string {
    switch (estado) {
      case 'activo':
        return 'ah-pill--ok';
      case 'suspendido':
        return 'ah-pill--critico';
      default:
        return 'ah-pill--atencion';
    }
  }

  protected paginaAnterior(): void {
    if (this.paginaActual() > 1) {
      this.paginaActual.update((p) => p - 1);
    }
  }

  protected paginaSiguiente(): void {
    if (this.paginaActual() < this.totalPaginas()) {
      this.paginaActual.update((p) => p + 1);
    }
  }
}
