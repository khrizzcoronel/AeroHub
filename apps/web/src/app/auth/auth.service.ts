import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

// URL del backend compuesto (services/gateway/main.py). Sin build de
// produccion todavia -- mismo criterio que tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';
const CLAVE_STORAGE = 'aerohub.sesion';

export interface ModuloVisible {
  codigo: string;
  nombre: string;
  ruta: string | null;
}

export interface Perfil {
  usuario_id: string;
  email: string;
  nombre: string;
  email_verificado: boolean;
  debe_cambiar_password: boolean;
  tenant_id: string | null;
  tenant_codigo: string | null;
  tenant_razon_social: string | null;
  rol_codigo: string;
  rol_nombre: string;
  scopes: string[];
  modulos_visibles: ModuloVisible[];
}

interface LoginResponse {
  token: string;
  expira_en_minutos: number;
  perfil: Perfil;
}

interface SesionAlmacenada {
  token: string;
  perfil: Perfil;
}

/** Traduce mensajes de error técnicos y nombres de campos de la BD a lenguaje claro en español */
export function mensajeDeError(err: HttpErrorResponse): string {
  let msg = typeof err.error?.detail === 'string'
    ? err.error.detail
    : `Error ${err.status}: ${err.message}`;

  msg = msg.replace(/aeropuerto_id y plan_id son obligatorios/gi, 'Debe seleccionar un aeropuerto y un plan válidos de la lista.');
  msg = msg.replace(/aeropuerto_id/gi, 'aeropuerto');
  msg = msg.replace(/plan_id/gi, 'plan');
  msg = msg.replace(/email_admin/gi, 'correo del administrador');
  msg = msg.replace(/nombre_admin/gi, 'nombre del administrador');
  msg = msg.replace(/password_actual/gi, 'contraseña actual');
  msg = msg.replace(/password_nueva/gi, 'contraseña nueva');
  msg = msg.replace(/contrasena actual incorrecta/gi, 'La contraseña temporal ingresada es incorrecta.');
  msg = msg.replace(/la contrasena debe tener al menos/gi, 'La contraseña debe tener al menos');
  msg = msg.replace(/la contrasena debe incluir/gi, 'La contraseña debe incluir');

  return msg;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly sesion = signal<SesionAlmacenada | null>(this.leerDeStorage());

  readonly perfil = computed(() => this.sesion()?.perfil ?? null);
  readonly token = computed(() => this.sesion()?.token ?? null);
  readonly estaAutenticado = computed(() => this.sesion() !== null);

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${API_BASE_URL}/auth/login`, { email, password })
      .pipe(tap((respuesta) => this.guardarSesion(respuesta.token, respuesta.perfil)));
  }

  logout(): void {
    const token = this.token();
    this.sesion.set(null);
    localStorage.removeItem(CLAVE_STORAGE);
    if (token) {
      // Best-effort: el estado local ya se limpio pase lo que pase con
      // la respuesta del servidor.
      this.http.post(`${API_BASE_URL}/auth/logout`, {}).subscribe({ error: () => undefined });
    }
  }

  cambiarPassword(passwordActual: string, passwordNueva: string): Observable<unknown> {
    return this.http
      .post(`${API_BASE_URL}/auth/cambiar-password`, {
        password_actual: passwordActual.trim(),
        password_nueva: passwordNueva,
      })
      .pipe(
        tap(() => {
          this.marcarPasswordCambiada();
          this.refrescarPerfil().subscribe({ error: () => undefined });
        }),
      );
  }

  solicitarRecuperacion(email: string): Observable<unknown> {
    return this.http.post(`${API_BASE_URL}/auth/recuperar`, { email });
  }

  restablecerPassword(token: string, passwordNueva: string): Observable<unknown> {
    return this.http.post(`${API_BASE_URL}/auth/restablecer`, {
      token,
      password_nueva: passwordNueva,
    });
  }

  verificarCorreo(token: string): Observable<unknown> {
    return this.http.post(`${API_BASE_URL}/auth/verificar-correo`, { token });
  }

  aceptarInvitacion(token: string, nombre: string, password: string): Observable<unknown> {
    return this.http.post(`${API_BASE_URL}/usuarios/aceptar-invitacion`, {
      token,
      nombre,
      password,
    });
  }

  invitarUsuario(email: string, rolCodigo: string): Observable<{ invitacion_id: string; expira_en: string }> {
    return this.http.post<{ invitacion_id: string; expira_en: string }>(
      `${API_BASE_URL}/usuarios/invitaciones`,
      { email, rol_codigo: rolCodigo },
    );
  }

  refrescarPerfil(): Observable<Perfil> {
    return this.http.get<Perfil>(`${API_BASE_URL}/auth/yo`).pipe(
      tap((perfil) => {
        const actual = this.sesion();
        if (actual) {
          this.guardarSesion(actual.token, perfil);
        }
      }),
    );
  }

  /** Tras cambiar la password exitosamente: el perfil en memoria queda
   * desactualizado (`debe_cambiar_password` seguiria en `true`) hasta el
   * proximo `GET /auth/yo` -- se llama explicitamente para no dejar al
   * usuario atrapado en la pantalla de cambio obligatorio. */
  marcarPasswordCambiada(): void {
    const actual = this.sesion();
    if (actual) {
      this.guardarSesion(actual.token, { ...actual.perfil, debe_cambiar_password: false });
    }
  }

  private guardarSesion(token: string, perfil: Perfil): void {
    const sesion: SesionAlmacenada = { token, perfil };
    this.sesion.set(sesion);
    localStorage.setItem(CLAVE_STORAGE, JSON.stringify(sesion));
  }

  private leerDeStorage(): SesionAlmacenada | null {
    const crudo = localStorage.getItem(CLAVE_STORAGE);
    if (!crudo) return null;
    try {
      return JSON.parse(crudo) as SesionAlmacenada;
    } catch {
      return null;
    }
  }
}
