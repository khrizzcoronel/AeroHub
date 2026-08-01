import { Route } from '@angular/router';
import { TableroPuertas } from './puertas/tablero-puertas/tablero-puertas';
import { TenantCreation } from './tenants/tenant-creation/tenant-creation';
import { EstadoTiempoReal } from './vuelos/estado-tiempo-real/estado-tiempo-real';

export const appRoutes: Route[] = [
  { path: '', pathMatch: 'full', redirectTo: 'tenants/nuevo' },
  { path: 'tenants/nuevo', component: TenantCreation },
  { path: 'vuelos/tiempo-real', component: EstadoTiempoReal },
  { path: 'puertas/tablero', component: TableroPuertas },
];
