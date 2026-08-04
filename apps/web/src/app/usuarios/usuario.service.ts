import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UsuarioResumen {
  id: string;
  email: string;
  nombre: string;
  estado: string;
  creado_en: string;
  ultimo_acceso_en: string | null;
  rol_codigo: string | null;
  rol_nombre: string | null;
}

export interface InvitarResponse {
  invitacion_id: string;
  expira_en: string;
}

const API_BASE_URL = 'http://localhost:8000';

@Injectable({
  providedIn: 'root',
})
export class UsuarioService {
  private readonly http = inject(HttpClient);

  listarUsuarios(): Observable<UsuarioResumen[]> {
    return this.http.get<UsuarioResumen[]>(`${API_BASE_URL}/usuarios`);
  }

  invitarUsuario(email: string, rolCodigo: string): Observable<InvitarResponse> {
    return this.http.post<InvitarResponse>(`${API_BASE_URL}/usuarios/invitaciones`, {
      email,
      rol_codigo: rolCodigo,
    });
  }
}
