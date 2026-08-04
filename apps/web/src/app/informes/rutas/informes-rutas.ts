import { Component } from '@angular/core';
import { PanelInforme } from '../panel-informe/panel-informe';
import {
  CONFIG_INFORME_ASIGNACIONES,
  CONFIG_INFORME_COMPLIANCE,
  CONFIG_INFORME_FACTURACION,
  CONFIG_INFORME_TENANTS,
  CONFIG_INFORME_TURNAROUNDS,
  CONFIG_INFORME_VUELOS,
} from '../informes-config';

// Sprint S1.18 -- 6 componentes de 1 linea, cada uno solo fija el
// @Input `config` de panel-informe con la configuracion de su modulo.
// Necesarios porque el router de Angular no tiene withComponentInputBinding()
// habilitado (app.config.ts) -- sin esto, @Input({required:true}) no
// puede alimentarse directo desde `route.data`.

@Component({
  selector: 'app-informes-vuelos',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesVuelos {
  protected readonly config = CONFIG_INFORME_VUELOS;
}

@Component({
  selector: 'app-informes-asignaciones',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesAsignaciones {
  protected readonly config = CONFIG_INFORME_ASIGNACIONES;
}

@Component({
  selector: 'app-informes-turnarounds',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesTurnarounds {
  protected readonly config = CONFIG_INFORME_TURNAROUNDS;
}

@Component({
  selector: 'app-informes-facturacion',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesFacturacion {
  protected readonly config = CONFIG_INFORME_FACTURACION;
}

@Component({
  selector: 'app-informes-tenants',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesTenants {
  protected readonly config = CONFIG_INFORME_TENANTS;
}

@Component({
  selector: 'app-informes-compliance',
  imports: [PanelInforme],
  template: `<app-panel-informe [config]="config" />`,
})
export class InformesCompliance {
  protected readonly config = CONFIG_INFORME_COMPLIANCE;
}
