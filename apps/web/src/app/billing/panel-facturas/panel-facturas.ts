import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { BillingService, Factura, FacturaDetalle } from '../billing.service';

// Sin login real todavia (mismo estado que el resto de apps/web) -- el
// token JWT se pega a mano.
@Component({
  selector: 'app-panel-facturas',
  imports: [CommonModule, FormsModule],
  templateUrl: './panel-facturas.html',
  // Cifras monetarias alineadas a la derecha con numeros tabulares --
  // legibilidad real de montos en columna, no decoracion.
  styles: `
    .columna-monto {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
  `,
})
export class PanelFacturas {
  protected readonly tokenJwt = signal('');
  protected readonly error = signal<string | null>(null);
  protected readonly cargando = signal(false);

  protected readonly facturas = signal<Factura[]>([]);
  protected readonly detalle = signal<FacturaDetalle | null>(null);

  protected readonly aerolineaId = signal('');
  protected readonly periodoInicio = signal('');
  protected readonly periodoFin = signal('');
  protected readonly ultimoCalculo = signal<string | null>(null);

  protected readonly motivoDisputa = signal('');

  private readonly billingService = inject(BillingService);

  protected cargarFacturas(): void {
    this.error.set(null);
    this.billingService.listarFacturas(this.tokenJwt()).subscribe({
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
        this.tokenJwt(),
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
    this.billingService.obtenerFactura(facturaId, this.tokenJwt()).subscribe({
      next: (respuesta) => this.detalle.set(respuesta),
      error: (err: HttpErrorResponse) => this.error.set(this.mensajeDeError(err)),
    });
  }

  protected emitirFactura(facturaId: string): void {
    this.cargando.set(true);
    this.error.set(null);
    this.billingService.emitirFactura(facturaId, this.tokenJwt()).subscribe({
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
    this.billingService.disputarFactura(facturaId, this.motivoDisputa(), this.tokenJwt()).subscribe({
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
