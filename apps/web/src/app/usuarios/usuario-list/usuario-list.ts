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
// Pedido explicito del usuario (2026-08-07, trabajo acotado a
// role_tenant_admin): se retira "Eliminado lógicamente" del modal -- el
// endpoint de motor sigue existiendo (mismo criterio D2(b) de
// PLAN_CORRECCION_MODULOS.md, "eliminacion fisica/logica sin consumidor
// de interfaz"), esta vista solo ofrece activar/suspender.
const TRANSICIONES: Record<string, string[]> = {
  activo: ['suspendido'],
  suspendido: ['activo'],
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
  // Estado editado localmente -- pedido explicito del usuario (2026-08-07):
  // ni el rol ni el estado se envian al backend hasta presionar "Guardar",
  // el switch solo mueve este signal.
  protected readonly estadoEdit = signal('');

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

  // KPI en vivo sobre datos ya cargados (ver docs/diseno/MODAL_Y_WORKPANEL.md
  // §1 punto 1) -- UsuarioResumen no trae email_verificado (solo el propio
  // perfil lo expone via /auth/perfil), asi que el KPI usa lo que esta
  // lista si tiene: suspendidos y sin rol asignado (rol_codigo null --
  // usuario creado sin invitacion con rol). Mostrados como chips
  // (.ah-chip) en la cabecera, no como oracion de resumen.
  protected readonly usuariosSuspendidos = computed(
    () => this.usuarios().filter((u) => u.estado === 'suspendido').length,
  );
  protected readonly usuariosSinRol = computed(
    () => this.usuarios().filter((u) => u.rol_codigo === null).length,
  );

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

  // Unica transicion posible desde `estado` (activo<->suspendido) -- null
  // para el estado terminal eliminado_logicamente, que ya no ofrece
  // ninguna accion en este modal.
  protected estadoAlternativo(estado: string): string | null {
    return this.transicionesDisponibles(estado)[0] ?? null;
  }

  // El switch solo alterna el signal local -- ver estadoEdit.
  protected alternarEstadoEdit(): void {
    this.estadoEdit.set(this.estadoEdit() === 'activo' ? 'suspendido' : 'activo');
  }

  protected verDetalles(u: UsuarioResumen): void {
    this.usuarioEditando.set(u);
    this.rolIdEdit.set(u.rol_codigo ?? '');
    this.estadoEdit.set(u.estado);
  }

  protected cerrarModalEditar(): void {
    this.usuarioEditando.set(null);
  }

  // Guarda rol y estado juntos, solo si cambiaron -- pedido explicito del
  // usuario (2026-08-07): ningun cambio se efectua hasta presionar
  // "Guardar" (antes el switch de estado llamaba a la API de inmediato).
  protected guardarEdicion(): void {
    const u = this.usuarioEditando();
    if (!u) return;
    this.error.set(null);

    const rolCambio = this.rolIdEdit() !== (u.rol_codigo ?? '');
    const estadoCambio = this.estadoEdit() !== u.estado;

    if (!rolCambio && !estadoCambio) {
      this.usuarioEditando.set(null);
      return;
    }

    const aplicarEstado = (): void => {
      if (!estadoCambio) {
        this.finalizarEdicion();
        return;
      }
      this.usuarioService.cambiarEstadoUsuario(u.id, this.estadoEdit()).subscribe({
        next: () => this.finalizarEdicion(),
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
    };

    if (rolCambio) {
      this.usuarioService.actualizarRolUsuario(u.id, this.rolIdEdit()).subscribe({
        next: () => aplicarEstado(),
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
    } else {
      aplicarEstado();
    }
  }

  private finalizarEdicion(): void {
    this.usuarioEditando.set(null);
    this.cargarUsuarios();
    this.toast.mostrar('Usuario actualizado con éxito', 'exito');
  }
}
