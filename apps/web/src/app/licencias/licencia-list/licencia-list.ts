import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { LicenciaResumen, LicenciaService } from '../licencia.service';
import { mensajeDeError } from '../../auth/auth.service';

@Component({
  selector: 'app-licencia-list',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './licencia-list.html',
  styleUrl: './licencia-list.scss',
})
export class LicenciaList implements OnInit {
  private readonly licenciaService = inject(LicenciaService);

  protected readonly licencias = signal<LicenciaResumen[]>([]);
  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);

  // Ver detalles (Fase 4 de docs/diseno/PLAN_CORRECCION_MODULOS.md, item
  // 12): no admite edicion -- una licencia la gobierna el plan del tenant,
  // no se administra individualmente (§5 del plan).
  protected readonly licenciaViendoDetalle = signal<LicenciaResumen | null>(null);

  ngOnInit(): void {
    this.cargarLicencias();
  }

  protected verDetalle(l: LicenciaResumen): void {
    this.licenciaViendoDetalle.set(l);
  }

  protected cerrarDetalle(): void {
    this.licenciaViendoDetalle.set(null);
  }

  protected cargarLicencias(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.licenciaService.listarLicencias().subscribe({
      next: (lista) => {
        this.licencias.set(lista);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected claseVigencia(esVigente: boolean): string {
    return esVigente ? 'ah-pill--ok' : 'ah-pill--critico';
  }

  protected textoVigencia(esVigente: boolean): string {
    return esVigente ? 'Activa / Vigente' : 'Expirada';
  }
}
