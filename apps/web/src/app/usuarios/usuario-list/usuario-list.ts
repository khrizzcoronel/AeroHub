import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { UsuarioResumen, UsuarioService, etiquetaEstadoUsuario } from '../usuario.service';
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

// Opciones de rol para el <select> del modal de edicion -- sin "Todos los
// roles" (eso es solo del filtro).
const ROLES_OPCIONES_EDICION = Object.entries(ROLES_ETIQUETAS).map(([value, label]) => ({
  value,
  label,
}));

// Transiciones validas -- espejo de domain/usuario.py::_TRANSICIONES_VALIDAS
// (services/tenancy/aerohub_tenancy/domain/usuario.py). Se repite aqui SOLO
// para no ofrecer en el UI un boton que el backend va a rechazar con 422
// -- el backend sigue siendo la unica fuente de verdad que valida de
// verdad (domain/usuario.py::validar_transicion_estado_usuario).
const TRANSICIONES: Record<string, string[]> = {
  activo: ['suspendido', 'eliminado_logicamente'],
  suspendido: ['activo', 'eliminado_logicamente'],
  eliminado_logicamente: [],
};

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
  protected readonly rolesOpcionesEdicion = ROLES_OPCIONES_EDICION;
  protected readonly etiquetaEstadoUsuario = etiquetaEstadoUsuario;

  // Modal "Ver detalles" -- mismo patron que tenant-list: pill de estado
  // en la cabecera, formulario de edicion (rol), transiciones de estado
  // validas para ese usuario puntual.
  protected readonly usuarioEditando = signal<UsuarioResumen | null>(null);
  protected readonly rolIdEdit = signal('');

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

  // Mismo semaforo que tenants (S1.13): activo=ok, suspendido=atencion
  // (reversible), eliminado_logicamente=critico (terminal, espejo de
  // dado_de_baja en claseEstadoTenant).
  protected claseEstado(estado: string): string {
    switch (estado) {
      case 'activo':
        return 'ah-pill--ok';
      case 'eliminado_logicamente':
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

  protected transicionesDisponibles(estado: string): string[] {
    return TRANSICIONES[estado] ?? [];
  }

  protected verDetalles(u: UsuarioResumen): void {
    this.usuarioEditando.set(u);
    this.rolIdEdit.set(u.rol_codigo ?? '');
  }

  protected cerrarModalEditar(): void {
    this.usuarioEditando.set(null);
  }

  protected guardarEdicion(): void {
    const usuarioId = this.usuarioEditando()?.id;
    if (!usuarioId) return;
    this.error.set(null);
    this.usuarioService.actualizarRolUsuario(usuarioId, this.rolIdEdit()).subscribe({
      next: () => {
        this.usuarioEditando.set(null);
        this.cargarUsuarios();
        this.toast.mostrar('Usuario actualizado con éxito', 'exito');
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected cambiarEstadoDesdeModal(usuarioId: string, estadoNuevo: string): void {
    this.error.set(null);
    this.usuarioService.cambiarEstadoUsuario(usuarioId, estadoNuevo).subscribe({
      next: () => {
        this.usuarioEditando.set(null);
        this.cargarUsuarios();
        this.toast.mostrar(`Estado actualizado a: ${etiquetaEstadoUsuario(estadoNuevo)}`, 'exito');
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }
}
