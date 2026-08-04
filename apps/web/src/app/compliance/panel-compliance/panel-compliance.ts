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

  // --- Accesos de auditor ---
  protected readonly accesosAuditor = signal<AccesoAuditor[]>([]);
  protected readonly mostrarModalAcceso = signal(false);
  protected readonly auditorUsuarioId = signal('');
  protected readonly inicioAcceso = signal('');
  protected readonly finAcceso = signal('');
  protected readonly motivoAcceso = signal('');
  protected readonly errorAcceso = signal<string | null>(null);
  protected readonly guardandoAcceso = signal(false);

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

  // research.md Decision 4 -- puede escribir si el perfil trae el scope
  // compliance:escribir (mismo criterio ya usado en shell.ts, sin
  // duplicar la regla de autorizacion real que ya aplica el backend).
  protected readonly puedeEscribir = computed(() =>
    (this.authService.perfil()?.scopes ?? []).includes('compliance:escribir'),
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
}
