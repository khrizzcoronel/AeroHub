import { Route } from '@angular/router';
import { TenantCreation } from './tenants/tenant-creation/tenant-creation';

export const appRoutes: Route[] = [
  { path: '', pathMatch: 'full', redirectTo: 'tenants/nuevo' },
  { path: 'tenants/nuevo', component: TenantCreation },
];
