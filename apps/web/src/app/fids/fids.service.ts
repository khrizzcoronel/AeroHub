import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// URL del backend compuesto -- ver el comentario equivalente en
// tenants/tenant.service.ts.
const API_BASE_URL = 'http://localhost:8000';

export interface Plantilla {
  id: string;
  nombre: string;
  definicion_json: Record<string, unknown>;
  version: number;
  vigente_desde: string;
}

export interface Pantalla {
  id: string;
  terminal_id: string;
  codigo: string;
  plantilla_id: string;
  ubicacion_descripcion: string | null;
  estado: string;
  ultima_senal_en: string | null;
  version_firmware: string | null;
}

export interface Terminal {
  id: string;
  codigo: string;
  nombre: string;
}

export interface PublicarPlantillaRequest {
  nombre: string;
  definicion_json: Record<string, unknown>;
}

export interface PublicarPlantillaResponse {
  plantilla_id: string;
  version: number;
}

export interface RegistrarPantallaRequest {
  terminal_id: string;
  codigo: string;
  plantilla_id: string;
  ubicacion_descripcion?: string | null;
}

export interface RegistrarPantallaResponse {
  pantalla_id: string;
}

@Injectable({ providedIn: 'root' })
export class FidsService {
  private readonly http = inject(HttpClient);

  listarPlantillas(): Observable<Plantilla[]> {
    return this.http.get<Plantilla[]>(`${API_BASE_URL}/fids/plantillas`);
  }

  publicarPlantilla(peticion: PublicarPlantillaRequest): Observable<PublicarPlantillaResponse> {
    return this.http.post<PublicarPlantillaResponse>(`${API_BASE_URL}/fids/plantillas`, peticion);
  }

  listarPantallas(): Observable<Pantalla[]> {
    return this.http.get<Pantalla[]>(`${API_BASE_URL}/fids/pantallas`);
  }

  registrarPantalla(peticion: RegistrarPantallaRequest): Observable<RegistrarPantallaResponse> {
    return this.http.post<RegistrarPantallaResponse>(`${API_BASE_URL}/fids/pantallas`, peticion);
  }

  asignarPlantilla(pantallaId: string, plantillaId: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE_URL}/fids/pantallas/${pantallaId}/plantilla`, {
      plantilla_id: plantillaId,
    });
  }

  listarTerminales(): Observable<Terminal[]> {
    return this.http.get<Terminal[]>(`${API_BASE_URL}/fids/catalogo/terminales`);
  }
}
