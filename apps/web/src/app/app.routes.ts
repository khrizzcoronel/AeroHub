import { Route } from '@angular/router';
import { AceptarInvitacion } from './auth/aceptar-invitacion/aceptar-invitacion';
import { authGuard } from './auth/auth.guard';
import { CambiarPassword } from './auth/cambiar-password/cambiar-password';
import { Login } from './auth/login/login';
import { Recuperar } from './auth/recuperar/recuperar';
import { Restablecer } from './auth/restablecer/restablecer';
import { VerificarCorreo } from './auth/verificar-correo/verificar-correo';
import { PanelFacturas } from './billing/panel-facturas/panel-facturas';
import { PanelTarifarios } from './billing/panel-tarifarios/panel-tarifarios';
import { TableroPuertas } from './puertas/tablero-puertas/tablero-puertas';
import { PanelTurnaround } from './rampa/panel-turnaround/panel-turnaround';
import { Shell } from './shell/shell';
import { TenantList } from './tenants/tenant-list/tenant-list';
import { Invitar } from './usuarios/invitar/invitar';
import { UsuarioList } from './usuarios/usuario-list/usuario-list';
import { ApiKeyList } from './api-keys/api-key-list/api-key-list';
import { LicenciaList } from './licencias/licencia-list/licencia-list';
import { EstadoTiempoReal } from './vuelos/estado-tiempo-real/estado-tiempo-real';
import { PanelCompliance } from './compliance/panel-compliance/panel-compliance';
import { PanelSoporte } from './soporte/panel-soporte/panel-soporte';
import { InicioComponent } from './inicio.component';
import { PantallaList } from './fids/pantalla-list/pantalla-list';
import { DashboardInformes } from './informes/dashboard-informes/dashboard-informes';

export const appRoutes: Route[] = [
  // Publicas -- sin sesion, mismo criterio que RUTAS_EXENTAS del gateway.
  { path: 'login', component: Login },
  { path: 'recuperar', component: Recuperar },
  { path: 'restablecer', component: Restablecer },
  { path: 'verificar-correo', component: VerificarCorreo },
  { path: 'aceptar-invitacion', component: AceptarInvitacion },

  // Autenticadas, envueltas en el shell con menu dinamico (FR-028).
  // `data.title` alimenta el indicador de vista actual del shell -- no
  // depende de modulos_visibles (esa lista solo cubre M1-M9, no las
  // vistas de identidad/tenancy que viven fuera del menu dinamico).
  {
    path: '',
    component: Shell,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', component: InicioComponent },
      { path: 'cambiar-password', component: CambiarPassword, data: { title: 'Cambiar contraseña' } },
      { path: 'usuarios', component: UsuarioList, data: { title: 'Usuarios y Equipo' } },
      { path: 'usuarios/invitar', component: Invitar, data: { title: 'Invitar usuario' } },
      { path: 'api-keys', component: ApiKeyList, data: { title: 'API Keys e Integraciones' } },
      { path: 'licencias', component: LicenciaList, data: { title: 'Licencias y Módulos' } },
      { path: 'tenants', component: TenantList, data: { title: 'Tenants' } },
      {
        path: 'vuelos/tiempo-real',
        component: EstadoTiempoReal,
        data: { title: 'AODB · Estado de vuelos' },
      },
      { path: 'fids/pantallas', component: PantallaList, data: { title: 'FIDS Management' } },
      { path: 'compliance/panel', component: PanelCompliance, data: { title: 'Compliance Hub' } },
      { path: 'soporte/panel', component: PanelSoporte, data: { title: 'Soporte' } },
      { path: 'puertas/tablero', component: TableroPuertas, data: { title: 'Terminal & Gate Manager' } },
      { path: 'rampa/turnaround', component: PanelTurnaround, data: { title: 'Ground Operations' } },
      { path: 'billing/facturas', component: PanelFacturas, data: { title: 'Revenue & Billing' } },
      {
        path: 'billing/tarifarios',
        component: PanelTarifarios,
        data: { title: 'Tarifarios y conciliación' },
      },
      { path: 'informes/dashboard', component: DashboardInformes, data: { title: 'Dashboard' } },
    ],
  },
];
