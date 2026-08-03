import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { BillingService, Factura, FacturaDetalle } from '../billing.service';

// Semaforo de estado de factura (Sprint S1.13, research.md Decision 1):
// mapeo exhaustivo de los 5 valores de chk_factura_estado.
export function claseEstadoFactura(estado: string): string {
  if (estado === 'vencida' || estado === 'disputada') {
    return 'ah-tira--critico';
  }
  if (estado === 'emitida') {
    return 'ah-tira--atencion';
  }
  if (estado === 'pagada') {
    return 'ah-tira--ok';
  }
  return ''; // 'borrador' -- neutro
}

@Component({
  selector: 'app-panel-facturas',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-facturas.html',
  styleUrl: './panel-facturas.scss',
})
export class PanelFacturas {
  protected readonly error = signal<string | null>(null);
  protected readonly cargando = signal(false);

  protected readonly facturas = signal<Factura[]>([]);
  protected readonly detalle = signal<FacturaDetalle | null>(null);

  protected readonly aerolineaId = signal('');
  protected readonly periodoInicio = signal('');
  protected readonly periodoFin = signal('');
  protected readonly ultimoCalculo = signal<string | null>(null);

  protected readonly motivoDisputa = signal('');

  protected readonly claseEstadoFactura = claseEstadoFactura;

  private readonly billingService = inject(BillingService);

  protected cargarFacturas(): void {
    this.error.set(null);
    this.billingService.listarFacturas().subscribe({
      next: (respuesta) => this.facturas.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected calcularFacturacion(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.ultimoCalculo.set(null);
    this.billingService
      .calcularFacturacion(
        {
          aerolinea_id: this.aerolineaId(),
          periodo_inicio: this.periodoInicio(),
          periodo_fin: this.periodoFin(),
        },
      )
      .subscribe({
        next: (respuesta) => {
          this.cargando.set(false);
          if (respuesta.factura_id === null) {
            this.ultimoCalculo.set('Sin vuelos en el periodo -- ningun cargo que facturar.');
          } else {
            this.ultimoCalculo.set(
              `Factura ${respuesta.factura_id}: ${respuesta.cargos_calculados} cargo(s) nuevo(s), ` +
                `${respuesta.cargos_ya_existentes} ya facturado(s) antes.`,
            );
          }
          this.cargarFacturas();
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(this.mensajeDeError(err));
          this.cargando.set(false);
        },
      });
  }

  protected verDetalle(facturaId: string): void {
    this.error.set(null);
    this.billingService.obtenerFactura(facturaId).subscribe({
      next: (respuesta) => this.detalle.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected emitirFactura(facturaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.emitirFactura(facturaId).subscribe({
      next: () => {
        this.cargando.set(false);
        this.verDetalle(facturaId);
        this.cargarFacturas();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  protected disputarFactura(facturaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.disputarFactura(facturaId, this.motivoDisputa()).subscribe({
      next: () => {
        this.cargando.set(false);
        this.motivoDisputa.set('');
        this.verDetalle(facturaId);
        this.cargarFacturas();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(this.mensajeDeError(err));
        this.cargando.set(false);
      },
    });
  }

  private mensajeDeError(err: HttpErrorResponse): string {
    return typeof err.error?.detail === 'string'
      ? err.error.detail
      : `Error ${err.status}: ${err.message}`;
  }
}
