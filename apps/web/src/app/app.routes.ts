import { Route } from '@angular/router';
import { AceptarInvitacion } from './auth/aceptar-invitacion/aceptar-invitacion';
import { authGuard } from './auth/auth.guard';
import { CambiarPassword } from './auth/cambiar-password/cambiar-password';
import { Login } from './auth/login/login';
import { Recuperar } from './auth/recuperar/recuperar';
import { Restablecer } from './auth/restablecer/restablecer';
import { VerificarCorreo } from './auth/verificar-correo/verificar-correo';
import { PanelFacturas } from './billing/panel-facturas/panel-facturas';
import { TableroPuertas } from './puertas/tablero-puertas/tablero-puertas';
import { PanelTurnaround } from './rampa/panel-turnaround/panel-turnaround';
import { Shell } from './shell/shell';
import { TenantCreation } from './tenants/tenant-creation/tenant-creation';
import { Invitar } from './usuarios/invitar/invitar';
import { EstadoTiempoReal } from './vuelos/estado-tiempo-real/estado-tiempo-real';

export const appRoutes: Route[] = [
  // Publicas -- sin sesion, mismo criterio que RUTAS_EXENTAS del gateway.
  { path: 'login', component: Login },
  { path: 'recuperar', component: Recuperar },
  { path: 'restablecer', component: Restablecer },
  { path: 'verificar-correo', component: VerificarCorreo },
  { path: 'aceptar-invitacion', component: AceptarInvitacion },

  // Autenticadas, envueltas en el shell con menu dinamico (FR-028).
  {
    path: '',
    component: Shell,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'tenants/nuevo' },
      { path: 'cambiar-password', component: CambiarPassword },
      { path: 'usuarios/invitar', component: Invitar },
      { path: 'tenants/nuevo', component: TenantCreation },
      { path: 'vuelos/tiempo-real', component: EstadoTiempoReal },
      { path: 'puertas/tablero', component: TableroPuertas },
      { path: 'rampa/turnaround', component: PanelTurnaround },
      { path: 'billing/facturas', component: PanelFacturas },
    ],
  },
];
