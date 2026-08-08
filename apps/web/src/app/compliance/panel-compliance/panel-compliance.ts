import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService, mensajeDeError } from '../../auth/auth.service';
import { ToastService } from '../../shared/toast.service';
import {
  AccesoAuditor,
  ComplianceService,
  ControlSoc2,
  EvidenciaSoc2,
  Incidente,
  PostMortemDetalle,
  PostMortemResumen,
  ReporteDgac,
  TipoIncidente,
  TipoReporteRegulatorio,
} from '../compliance.service';

const TAMANO_PAGINA = 10;

const ETIQUETAS_ESTADO_INCIDENTE: Record<string, string> = {
  abierto: 'Abierto',
  en_investigacion: 'En investigación',
  contenido: 'Contenido',
  cerrado: 'Cerrado',
};

export function claseEstadoIncidente(estado: string): string {
  if (estado === 'abierto') return 'ah-pill--critico';
  if (estado === 'en_investigacion') return 'ah-pill--atencion';
  if (estado === 'contenido') return 'ah-pill--atencion';
  if (estado === 'cerrado') return 'ah-pill--ok';
  return '';
}

export function etiquetaEstadoIncidente(estado: string): string {
  return ETIQUETAS_ESTADO_INCIDENTE[estado] ?? estado;
}

const ETIQUETAS_ESTADO_POST_MORTEM: Record<string, string> = {
  en_progreso: 'En progreso',
  publicado: 'Publicado',
};

export function claseEstadoPostMortem(estado: string): string {
  if (estado === 'publicado') return 'ah-pill--ok';
  if (estado === 'en_progreso') return 'ah-pill--atencion';
  return '';
}

export function etiquetaEstadoPostMortem(estado: string): string {
  return ETIQUETAS_ESTADO_POST_MORTEM[estado] ?? estado;
}

@Component({
  selector: 'app-panel-compliance',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-compliance.html',
  styleUrl: './panel-compliance.scss',
})
export class PanelCompliance {
  private readonly complianceService = inject(ComplianceService);
  private readonly toast = inject(ToastService);
  private readonly authService = inject(AuthService);

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  // --- Incidentes ---
  protected readonly tiposIncidente = signal<TipoIncidente[]>([]);
  protected readonly incidentes = signal<Incidente[]>([]);
  protected readonly mostrarModalIncidente = signal(false);
  protected readonly tipoIncidenteId = signal('');
  protected readonly descripcionIncidente = signal('');
  protected readonly severidadIncidente = signal('media');
  protected readonly detectadoEn = signal('');
  protected readonly errorIncidente = signal<string | null>(null);
  protected readonly guardandoIncidente = signal(false);

  protected readonly filtroIncidente = signal('');
  protected readonly incidentesFiltrados = computed(() => {
    const q = this.filtroIncidente().trim().toLowerCase();
    if (!q) return this.incidentes();
    return this.incidentes().filter(
      (i) =>
        i.descripcion.toLowerCase().includes(q) ||
        this.nombreTipoIncidente(i.tipo_incidente_id).toLowerCase().includes(q),
    );
  });
  protected readonly paginaActualIncidente = signal(1);
  protected readonly totalPaginasIncidente = computed(() =>
    Math.max(1, Math.ceil(this.incidentesFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly incidentesPagina = computed(() => {
    const inicio = (this.paginaActualIncidente() - 1) * TAMANO_PAGINA;
    return this.incidentesFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // --- Post-mortems ---
  protected readonly postMortems = signal<PostMortemResumen[]>([]);
  protected readonly mostrarModalPostMortem = signal(false);
  protected readonly incidenteRef = signal('');
  protected readonly severidadPm = signal('media');
  protected readonly iniciadoEn = signal('');
  protected readonly errorPostMortem = signal<string | null>(null);
  protected readonly guardandoPostMortem = signal(false);

  protected readonly detalle = signal<PostMortemDetalle | null>(null);
  protected readonly causaRaiz = signal('');
  protected readonly descripcionAccion = signal('');
  protected readonly responsableAccion = signal('');
  protected readonly venceAccion = signal('');

  protected readonly filtroPostMortem = signal('');
  protected readonly postMortemsFiltrados = computed(() => {
    const q = this.filtroPostMortem().trim().toLowerCase();
    if (!q) return this.postMortems();
    return this.postMortems().filter((p) => p.incidente_ref.toLowerCase().includes(q));
  });
  protected readonly paginaActualPostMortem = signal(1);
  protected readonly totalPaginasPostMortem = computed(() =>
    Math.max(1, Math.ceil(this.postMortemsFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly postMortemsPagina = computed(() => {
    const inicio = (this.paginaActualPostMortem() - 1) * TAMANO_PAGINA;
    return this.postMortemsFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // --- Reportes DGAC ---
  protected readonly tiposReporte = signal<TipoReporteRegulatorio[]>([]);
  protected readonly reportesDgac = signal<ReporteDgac[]>([]);
  protected readonly mostrarModalReporte = signal(false);
  protected readonly tipoReporteId = signal('');
  protected readonly periodoInicioReporte = signal('');
  protected readonly periodoFinReporte = signal('');
  protected readonly contenidoRef = signal('');
  protected readonly hashContenido = signal('');
  protected readonly errorReporte = signal<string | null>(null);
  protected readonly guardandoReporte = signal(false);

  protected readonly filtroReporte = signal('');
  protected readonly reportesDgacFiltrados = computed(() => {
    const q = this.filtroReporte().trim().toLowerCase();
    if (!q) return this.reportesDgac();
    return this.reportesDgac().filter((r) =>
      this.nombreTipoReporte(r.tipo_reporte_id).toLowerCase().includes(q),
    );
  });
  protected readonly paginaActualReporte = signal(1);
  protected readonly totalPaginasReporte = computed(() =>
    Math.max(1, Math.ceil(this.reportesDgacFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly reportesDgacPagina = computed(() => {
    const inicio = (this.paginaActualReporte() - 1) * TAMANO_PAGINA;
    return this.reportesDgacFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // --- Accesos de auditor ---
  protected readonly accesosAuditor = signal<AccesoAuditor[]>([]);
  protected readonly mostrarModalAcceso = signal(false);
  protected readonly auditorUsuarioId = signal('');
  protected readonly inicioAcceso = signal('');
  protected readonly finAcceso = signal('');
  protected readonly motivoAcceso = signal('');
  protected readonly errorAcceso = signal<string | null>(null);
  protected readonly guardandoAcceso = signal(false);

  protected readonly filtroAcceso = signal('');
  protected readonly accesosAuditorFiltrados = computed(() => {
    const q = this.filtroAcceso().trim().toLowerCase();
    if (!q) return this.accesosAuditor();
    return this.accesosAuditor().filter((a) => a.auditor_usuario_id.toLowerCase().includes(q));
  });
  protected readonly paginaActualAcceso = signal(1);
  protected readonly totalPaginasAcceso = computed(() =>
    Math.max(1, Math.ceil(this.accesosAuditorFiltrados().length / TAMANO_PAGINA)),
  );
  protected readonly accesosAuditorPagina = computed(() => {
    const inicio = (this.paginaActualAcceso() - 1) * TAMANO_PAGINA;
    return this.accesosAuditorFiltrados().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // --- Evidencia SOC2 (solo lectura para roles sin compliance:escribir) ---
  protected readonly controlesSoc2 = signal<ControlSoc2[]>([]);
  protected readonly evidenciaSoc2 = signal<EvidenciaSoc2[]>([]);
  protected readonly mostrarModalEvidencia = signal(false);
  protected readonly controlSoc2Id = signal('');
  protected readonly periodoInicioEvidencia = signal('');
  protected readonly periodoFinEvidencia = signal('');
  protected readonly rutaArtefacto = signal('');
  protected readonly hashArtefacto = signal('');
  protected readonly errorEvidencia = signal<string | null>(null);
  protected readonly guardandoEvidencia = signal(false);

  protected readonly filtroEvidencia = signal('');
  protected readonly evidenciaSoc2Filtrada = computed(() => {
    const q = this.filtroEvidencia().trim().toLowerCase();
    if (!q) return this.evidenciaSoc2();
    return this.evidenciaSoc2().filter((e) =>
      this.nombreControlSoc2(e.control_soc2_id).toLowerCase().includes(q),
    );
  });
  protected readonly paginaActualEvidencia = signal(1);
  protected readonly totalPaginasEvidencia = computed(() =>
    Math.max(1, Math.ceil(this.evidenciaSoc2Filtrada().length / TAMANO_PAGINA)),
  );
  protected readonly evidenciaSoc2Pagina = computed(() => {
    const inicio = (this.paginaActualEvidencia() - 1) * TAMANO_PAGINA;
    return this.evidenciaSoc2Filtrada().slice(inicio, inicio + TAMANO_PAGINA);
  });

  // research.md Decision 4 -- puede escribir si el perfil trae el scope
  // compliance:escribir (mismo criterio ya usado en shell.ts, sin
  // duplicar la regla de autorizacion real que ya aplica el backend).
  protected readonly puedeEscribir = computed(() =>
    (this.authService.perfil()?.scopes ?? []).includes('compliance:escribir'),
  );

  // KPI en vivo (docs/diseno/MODAL_Y_WORKPANEL.md §1.2 punto 2) --
  // mostrados como chips de cabecera de pagina (no por seccion).
  protected readonly incidentesAbiertos = computed(
    () => this.incidentes().filter((i) => i.estado !== 'cerrado').length,
  );
  protected readonly postMortemsSinPublicar = computed(
    () => this.postMortems().filter((p) => p.estado !== 'publicado').length,
  );

  constructor() {
    this.cargarTodo();
  }

  protected cargarTodo(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.complianceService.listarTiposIncidente().subscribe({ next: (r) => this.tiposIncidente.set(r) });
    this.complianceService.listarIncidentes().subscribe({
      next: (r) => this.incidentes.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.complianceService.listarPostMortems().subscribe({
      next: (r) => this.postMortems.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.complianceService.listarTiposReporte().subscribe({ next: (r) => this.tiposReporte.set(r) });
    this.complianceService.listarReportesDgac().subscribe({
      next: (r) => this.reportesDgac.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.complianceService.listarAccesosAuditor().subscribe({
      next: (r) => this.accesosAuditor.set(r),
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
    this.complianceService.listarControlesSoc2().subscribe({ next: (r) => this.controlesSoc2.set(r) });
    this.complianceService.listarEvidenciaSoc2().subscribe({
      next: (r) => {
        this.evidenciaSoc2.set(r);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  // --- Incidentes ---

  protected abrirModalIncidente(): void {
    this.errorIncidente.set(null);
    this.tipoIncidenteId.set('');
    this.descripcionIncidente.set('');
    this.severidadIncidente.set('media');
    this.detectadoEn.set('');
    this.mostrarModalIncidente.set(true);
  }

  protected cerrarModalIncidente(): void {
    this.mostrarModalIncidente.set(false);
  }

  protected crearIncidente(): void {
    this.errorIncidente.set(null);
    this.guardandoIncidente.set(true);
    this.complianceService
      .crearIncidente({
        tipo_incidente_id: this.tipoIncidenteId(),
        descripcion: this.descripcionIncidente(),
        severidad: this.severidadIncidente(),
        detectado_en: new Date(this.detectadoEn()).toISOString(),
      })
      .subscribe({
        next: () => {
          this.guardandoIncidente.set(false);
          this.mostrarModalIncidente.set(false);
          this.cargarTodo();
          this.toast.mostrar('Incidente registrado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorIncidente.set(mensajeDeError(err));
          this.guardandoIncidente.set(false);
        },
      });
  }

  protected nombreTipoIncidente(id: string): string {
    return this.tiposIncidente().find((t) => t.id === id)?.descripcion ?? id;
  }

  protected actualizarFiltroIncidente(valor: string): void {
    this.filtroIncidente.set(valor);
    this.paginaActualIncidente.set(1);
  }

  protected paginaAnteriorIncidente(): void {
    this.paginaActualIncidente.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguienteIncidente(): void {
    this.paginaActualIncidente.update((p) => Math.min(this.totalPaginasIncidente(), p + 1));
  }

  protected claseEstadoIncidente(estado: string): string {
    return claseEstadoIncidente(estado);
  }

  protected etiquetaEstadoIncidente(estado: string): string {
    return etiquetaEstadoIncidente(estado);
  }

  // --- Post-mortems ---

  protected abrirModalPostMortem(): void {
    this.errorPostMortem.set(null);
    this.incidenteRef.set('');
    this.severidadPm.set('media');
    this.iniciadoEn.set('');
    this.mostrarModalPostMortem.set(true);
  }

  protected cerrarModalPostMortem(): void {
    this.mostrarModalPostMortem.set(false);
  }

  protected crearPostMortem(): void {
    this.errorPostMortem.set(null);
    this.guardandoPostMortem.set(true);
    this.complianceService
      .crearPostMortem({
        incidente_ref: this.incidenteRef(),
        severidad: this.severidadPm(),
        iniciado_en: new Date(this.iniciadoEn()).toISOString(),
      })
      .subscribe({
        next: () => {
          this.guardandoPostMortem.set(false);
          this.mostrarModalPostMortem.set(false);
          this.cargarTodo();
          this.toast.mostrar('Post-mortem creado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorPostMortem.set(mensajeDeError(err));
          this.guardandoPostMortem.set(false);
        },
      });
  }

  protected verDetalle(id: string): void {
    this.error.set(null);
    this.complianceService.obtenerPostMortem(id).subscribe({
      next: (r) => {
        this.detalle.set(r);
        this.causaRaiz.set(r.post_mortem.causa_raiz ?? '');
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected cerrarDetalle(): void {
    this.detalle.set(null);
    this.descripcionAccion.set('');
    this.responsableAccion.set('');
    this.venceAccion.set('');
  }

  protected guardarCausaRaiz(): void {
    const d = this.detalle();
    if (!d) return;
    this.complianceService.editarCausaRaiz(d.post_mortem.id, this.causaRaiz()).subscribe({
      next: () => {
        this.toast.mostrar('Causa raíz actualizada', 'exito');
        this.verDetalle(d.post_mortem.id);
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected agregarAccion(): void {
    const d = this.detalle();
    if (!d) return;
    this.complianceService
      .agregarAccion(d.post_mortem.id, {
        descripcion: this.descripcionAccion(),
        responsable_usuario_id: this.responsableAccion(),
        vence_en: new Date(this.venceAccion()).toISOString(),
      })
      .subscribe({
        next: () => {
          this.descripcionAccion.set('');
          this.responsableAccion.set('');
          this.venceAccion.set('');
          this.verDetalle(d.post_mortem.id);
          this.toast.mostrar('Acción agregada', 'exito');
        },
        error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
      });
  }

  protected completarAccion(accionId: string): void {
    const d = this.detalle();
    if (!d) return;
    this.complianceService.completarAccion(d.post_mortem.id, accionId).subscribe({
      next: () => {
        this.verDetalle(d.post_mortem.id);
        this.toast.mostrar('Acción completada', 'exito');
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected publicar(): void {
    const d = this.detalle();
    if (!d) return;
    this.complianceService.publicarPostMortem(d.post_mortem.id).subscribe({
      next: () => {
        this.cargarTodo();
        this.verDetalle(d.post_mortem.id);
        this.toast.mostrar('Post-mortem publicado', 'exito');
      },
      error: (err: HttpErrorResponse) => this.error.set(mensajeDeError(err)),
    });
  }

  protected actualizarFiltroPostMortem(valor: string): void {
    this.filtroPostMortem.set(valor);
    this.paginaActualPostMortem.set(1);
  }

  protected paginaAnteriorPostMortem(): void {
    this.paginaActualPostMortem.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguientePostMortem(): void {
    this.paginaActualPostMortem.update((p) => Math.min(this.totalPaginasPostMortem(), p + 1));
  }

  protected claseEstadoPostMortem(estado: string): string {
    return claseEstadoPostMortem(estado);
  }

  protected etiquetaEstadoPostMortem(estado: string): string {
    return etiquetaEstadoPostMortem(estado);
  }

  // --- Reportes DGAC ---

  protected abrirModalReporte(): void {
    this.errorReporte.set(null);
    this.tipoReporteId.set('');
    this.periodoInicioReporte.set('');
    this.periodoFinReporte.set('');
    this.contenidoRef.set('');
    this.hashContenido.set('');
    this.mostrarModalReporte.set(true);
  }

  protected cerrarModalReporte(): void {
    this.mostrarModalReporte.set(false);
  }

  protected registrarReporte(): void {
    this.errorReporte.set(null);
    this.guardandoReporte.set(true);
    this.complianceService
      .registrarReporte({
        tipo_reporte_id: this.tipoReporteId(),
        periodo_inicio: this.periodoInicioReporte(),
        periodo_fin: this.periodoFinReporte(),
        contenido_ref: this.contenidoRef(),
        hash_contenido: this.hashContenido(),
      })
      .subscribe({
        next: () => {
          this.guardandoReporte.set(false);
          this.mostrarModalReporte.set(false);
          this.cargarTodo();
          this.toast.mostrar('Reporte DGAC emitido', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorReporte.set(mensajeDeError(err));
          this.guardandoReporte.set(false);
        },
      });
  }

  protected nombreTipoReporte(id: string): string {
    return this.tiposReporte().find((t) => t.id === id)?.nombre ?? id;
  }

  protected actualizarFiltroReporte(valor: string): void {
    this.filtroReporte.set(valor);
    this.paginaActualReporte.set(1);
  }

  protected paginaAnteriorReporte(): void {
    this.paginaActualReporte.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguienteReporte(): void {
    this.paginaActualReporte.update((p) => Math.min(this.totalPaginasReporte(), p + 1));
  }

  // --- Accesos de auditor ---

  protected abrirModalAcceso(): void {
    this.errorAcceso.set(null);
    this.auditorUsuarioId.set('');
    this.inicioAcceso.set('');
    this.finAcceso.set('');
    this.motivoAcceso.set('');
    this.mostrarModalAcceso.set(true);
  }

  protected cerrarModalAcceso(): void {
    this.mostrarModalAcceso.set(false);
  }

  protected otorgarAcceso(): void {
    this.errorAcceso.set(null);
    this.guardandoAcceso.set(true);
    this.complianceService
      .otorgarAcceso({
        auditor_usuario_id: this.auditorUsuarioId(),
        inicio: new Date(this.inicioAcceso()).toISOString(),
        fin: new Date(this.finAcceso()).toISOString(),
        alcance_json: {},
        motivo: this.motivoAcceso(),
      })
      .subscribe({
        next: () => {
          this.guardandoAcceso.set(false);
          this.mostrarModalAcceso.set(false);
          this.cargarTodo();
          this.toast.mostrar('Acceso de auditor otorgado', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorAcceso.set(mensajeDeError(err));
          this.guardandoAcceso.set(false);
        },
      });
  }

  protected actualizarFiltroAcceso(valor: string): void {
    this.filtroAcceso.set(valor);
    this.paginaActualAcceso.set(1);
  }

  protected paginaAnteriorAcceso(): void {
    this.paginaActualAcceso.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguienteAcceso(): void {
    this.paginaActualAcceso.update((p) => Math.min(this.totalPaginasAcceso(), p + 1));
  }

  // --- Evidencia SOC2 ---

  protected abrirModalEvidencia(): void {
    this.errorEvidencia.set(null);
    this.controlSoc2Id.set('');
    this.periodoInicioEvidencia.set('');
    this.periodoFinEvidencia.set('');
    this.rutaArtefacto.set('');
    this.hashArtefacto.set('');
    this.mostrarModalEvidencia.set(true);
  }

  protected cerrarModalEvidencia(): void {
    this.mostrarModalEvidencia.set(false);
  }

  protected registrarEvidencia(): void {
    this.errorEvidencia.set(null);
    this.guardandoEvidencia.set(true);
    this.complianceService
      .registrarEvidencia({
        control_soc2_id: this.controlSoc2Id(),
        periodo_inicio: this.periodoInicioEvidencia(),
        periodo_fin: this.periodoFinEvidencia(),
        ruta_artefacto: this.rutaArtefacto(),
        hash_artefacto: this.hashArtefacto(),
      })
      .subscribe({
        next: () => {
          this.guardandoEvidencia.set(false);
          this.mostrarModalEvidencia.set(false);
          this.cargarTodo();
          this.toast.mostrar('Evidencia SOC2 registrada', 'exito');
        },
        error: (err: HttpErrorResponse) => {
          this.errorEvidencia.set(mensajeDeError(err));
          this.guardandoEvidencia.set(false);
        },
      });
  }

  protected nombreControlSoc2(id: string): string {
    return this.controlesSoc2().find((c) => c.id === id)?.nombre ?? id;
  }

  protected actualizarFiltroEvidencia(valor: string): void {
    this.filtroEvidencia.set(valor);
    this.paginaActualEvidencia.set(1);
  }

  protected paginaAnteriorEvidencia(): void {
    this.paginaActualEvidencia.update((p) => Math.max(1, p - 1));
  }

  protected paginaSiguienteEvidencia(): void {
    this.paginaActualEvidencia.update((p) => Math.min(this.totalPaginasEvidencia(), p + 1));
  }
}
