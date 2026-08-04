import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/** Agrega `Authorization: Bearer` a toda peticion cuando hay sesion, y
 * redirige a `/login` ante un 401 (sesion vencida o revocada) -- el
 * usuario nunca se queda mirando una pantalla que ya no puede cargar
 * datos sin saber por que. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const token = auth.token();
  const peticion = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(peticion).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && token) {
        // 401: sesion expirada o revocada -> logout y redirigir a login
        if (error.status === 401) {
          auth.logout();
          router.navigate(['/login']);
        }
        // 403 con mensaje de scope insuficiente: el token es viejo (emitido
        // antes de que se actualizaran los scopes del rol). Limpiamos la
        // sesion para forzar un nuevo login con token fresco.
        if (error.status === 403 &&
            typeof error.error?.detail === 'string' &&
            error.error.detail.includes('scope insuficiente')) {
          auth.logout();
          router.navigate(['/login']);
        }
      }
      return throwError(() => error);
    }),
  );
};
