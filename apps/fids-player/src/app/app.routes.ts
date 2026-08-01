import { Route } from '@angular/router';
import { PantallaPlayer } from './pantallas/pantalla-player/pantalla-player';

export const appRoutes: Route[] = [
  { path: '', pathMatch: 'full', redirectTo: 'pantallas/reproductor' },
  { path: 'pantallas/reproductor', component: PantallaPlayer },
];
