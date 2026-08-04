import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import { FidsService, Pantalla, Plantilla, Terminal } from '../fids.service';

// Semaforo de telemetria (Sprint S1.16, research.md Decision 3) --
// mapeo de presentacion puro sobre el `estado` que el backend ya
// mantiene (registrar_heartbeat / marcar_pantalla_sin_senal), sin
// recalcular nada.
export function claseEstadoPantalla(estado: string): string {
  if (estado === 'en_linea') return 'ah-pill--ok';
  if (estado === 'sin_senal') return 'ah-pill--critico';
  return ''; // 'mantenimiento' -- neutro
}

const ETIQUETAS_ESTADO_PANTALLA: Record<string, string> = {
  en_linea: 'En línea',
  sin_senal: 'Sin señal',
  mantenimiento: 'Mantenimiento',
};

export function etiquetaEstadoPantalla(estado: string): string {
  return ETIQUETAS_ESTADO_PANTALLA[estado] ?? estado;
}

@Component({
  selector: 'app-pantalla-list',
  imports: [CommonModule, FormsModule],
  templateUrl: './pantalla-list.html',
  styleUrl: './pantalla-list.scss',
})
export class PantallaList implements OnInit {
  private readonly fidsService = inject(FidsService);
  private readonly toast = inject(ToastService);

  protected readonly claseEstadoPantalla = claseEstadoPantalla;
  protected readonly etiquetaEstadoPantalla = etiquetaEstadoPantalla;

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  // --- Sección Plantillas (US2) ---
  protected readonly plantillas = signal<Plantilla[]>([]);
  protected readonly filtroPlantilla = signal('');
  protected readonly plantillasFiltradas = computed(() => {
    const q = this.filtroPlantilla().trim().toLowerCase();
    if (!q) return this.plantillas();
    return this.plantillas().filter((p) => p.nombre.toLowerCase().includes(q));
  });

  protected readonly mostrarModalPlantilla = signal(false);
  protected readonly nombrePlantilla = signal('');
  protected readonly definicionJsonTexto = signal('');
  protected readonly errorFormularioPlantilla = signal<string | null>(null);
  protected readonly guardandoPlantilla = signal(false);

  // --- Sección Pantallas (US1) ---
  protected readonly pantallas = signal<Pantalla[]>([]);
  protected readonly terminales = signal<Terminal[]>([]);
  protected readonly filtroPantalla = signal('');
  protected readonly pantallasFiltradas = computed(() => {
    const q = this.filtroPantalla().trim().toLowerCase();
    if (!q) return this.pantallas();
    return this.pantallas().filter((p) => p.codigo.toLowerCase().includes(q));
  });

  protected readonly mostrarModalRegistrar = signal(false);
  protected readonly terminalId = signal('');
  protected readonly codigoPantalla = signal('');
  protected readonly plantillaIdRegistro = signal('');
  protected readonly ubicacionDescripcion = signal('');
  protected readonly errorFormularioPantalla = signal<string | null>(null);
  protected readonly guardandoPantalla = signal(false);
  // Sprint S1.16, research.md Decision 5 -- el codigo de la pantalla
  // recien registrada queda visible en un aviso copiable, mismo patron
  // que tenant-creation con la contraseña temporal.
  protected readonly codigoRecienRegistrado = signal<string | null>(null);

  // --- Modal "Asignar plantilla" (US3) ---
  protected readonly pantallaReasignando = signal<Pantalla | null>(null);
  protected readonly plantillaIdNueva = signal('');
  protected readonly errorReasignar = signal<string | null>(null);
  protected readonly reasignando = signal(false);

  ngOnInit(): void {
    this.cargarTodo();
  }

  protected cargarTodo(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.fidsService.listarPlantillas().subscribe({
      next: (r) => this.plantillas.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.fidsService.listarPantallas().subscribe({
      next: (r) => {
        this.pantallas.set(r);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
    this.fidsService.listarTerminales().subscribe({ next: (r) => this.terminales.set(r) });
  }

  protected actualizarFiltroPlantilla(valor: string): void {
    this.filtroPlantilla.set(valor);
  }

  protected actualizarFiltroPantalla(valor: string): void {
    this.filtroPantalla.set(valor);
  }

  // --- Plantillas ---

  protected abrirModalPlantilla(): void {
    this.errorFormularioPlantilla.set(null);
    this.nombrePlantilla.set('');
    this.definicionJsonTexto.set('');
    this.mostrarModalPlantilla.set(true);
  }

  protected cerrarModalPlantilla(): void {
    this.mostrarModalPlantilla.set(false);
  }

  protected publicarPlantilla(): void {
    this.errorFormularioPlantilla.set(null);
    let definicion: Record<string, unknown>;
    try {
      definicion = JSON.parse(this.definicionJsonTexto());
    } catch {
      this.errorFormularioPlantilla.set('El contenido debe ser JSON válido.');
      return;
    }
    this.guardandoPlantilla.set(true);
    this.fidsService
      .publicarPlantilla({ nombre: this.nombrePlantilla(), definicion_json: definicion })
      .subscribe({
        next: () => {
          this.guardandoPlantilla.set(false);
          this.mostrarModalPlantilla.set(false);
          this.cargarTodo();
          this.toast.mostrar('Plantilla publicada con éxito', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioPlantilla.set(mensajeDeError(err));
          this.guardandoPlantilla.set(false);
        },
      });
  }

  // --- Pantallas ---

  protected abrirModalRegistrar(): void {
    this.errorFormularioPantalla.set(null);
    this.terminalId.set('');
    this.codigoPantalla.set('');
    this.plantillaIdRegistro.set('');
    this.ubicacionDescripcion.set('');
    this.mostrarModalRegistrar.set(true);
  }

  protected cerrarModalRegistrar(): void {
    this.mostrarModalRegistrar.set(false);
  }

  protected registrarPantalla(): void {
    this.errorFormularioPantalla.set(null);
    this.guardandoPantalla.set(true);
    this.fidsService
      .registrarPantalla({
        terminal_id: this.terminalId(),
        codigo: this.codigoPantalla(),
        plantilla_id: this.plantillaIdRegistro(),
        ubicacion_descripcion: this.ubicacionDescripcion() || null,
      })
      .subscribe({
        next: () => {
          this.guardandoPantalla.set(false);
          this.mostrarModalRegistrar.set(false);
          this.codigoRecienRegistrado.set(this.codigoPantalla());
          this.cargarTodo();
        },
        error: (err: HttpErrorResponse) => {
          this.errorFormularioPantalla.set(mensajeDeError(err));
          this.guardandoPantalla.set(false);
        },
      });
  }

  protected cerrarAvisoCodigo(): void {
    this.codigoRecienRegistrado.set(null);
  }

  protected copiarCodigo(codigo: string): void {
    navigator.clipboard?.writeText(codigo);
    this.toast.mostrar('Código copiado al portapapeles', 'info');
  }

  // --- Asignar plantilla (US3) ---

  protected abrirModalReasignar(p: Pantalla): void {
    this.errorReasignar.set(null);
    this.plantillaIdNueva.set(p.plantilla_id);
    this.pantallaReasignando.set(p);
  }

  protected cerrarModalReasignar(): void {
    this.pantallaReasignando.set(null);
  }

  protected confirmarReasignacion(): void {
    const pantalla = this.pantallaReasignando();
    if (!pantalla) return;
    this.reasignando.set(true);
    this.errorReasignar.set(null);
    this.fidsService.asignarPlantilla(pantalla.id, this.plantillaIdNueva()).subscribe({
      next: () => {
        this.reasignando.set(false);
        this.pantallaReasignando.set(null);
        this.cargarTodo();
        this.toast.mostrar(`Plantilla reasignada a ${pantalla.codigo}`, 'exito');
      },
      error: (err: HttpErrorResponse) => {
        this.errorReasignar.set(mensajeDeError(err));
        this.reasignando.set(false);
      },
    });
  }

  protected nombrePlantillaDe(plantillaId: string): string {
    const p = this.plantillas().find((item) => item.id === plantillaId);
    return p ? p.nombre : plantillaId;
  }

  protected codigoTerminalDe(terminalId: string): string {
    const t = this.terminales().find((item) => item.id === terminalId);
    return t ? t.codigo : terminalId;
  }
}
