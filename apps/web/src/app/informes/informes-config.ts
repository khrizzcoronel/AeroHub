// Sprint S1.18 -- una configuracion declarativa por modulo, consumida por
// dashboard-informes/ (unico panel de informes desde la iteracion de
// S1.18 del 2026-08-05 -- antes por panel-informe/, un componente por
// modulo que se retiro al consolidar los 6 en un solo panel).

export interface ColumnaInforme {
  campo: string;
  etiqueta: string;
}

export interface FiltroInforme {
  id: string;
  etiqueta: string;
  tipo: 'fecha' | 'texto' | 'select';
  opciones?: { valor: string; etiqueta: string }[];
}

export interface ConfigInforme {
  titulo: string;
  // Slug consumido por GET /analytics/tactico/{moduloCodigo} (M7,
  // ClickHouse) -- el compuesto del dashboard viene de ahi, no de
  // endpointCompuesto (que sigue existiendo para tools/sincronizar_analytics_demo.py
  // y como fallback documentado, ver research.md Decision X).
  moduloCodigo: string;
  endpointSimple: string;
  endpointCompuesto: string;
  filtros: FiltroInforme[];
  columnasSimple: ColumnaInforme[];
  columnaGrupo: string;
  columnasMetricas: ColumnaInforme[];
}

// Titulos alineados a los nombres reales de modulo usados en el resto de
// apps/web (roles_modulos.py::MODULOS y los <h1> de cada vista propia) --
// antes decian "Informes de X", inconsistente con como el usuario ya
// conoce cada modulo en el menu y en sus pantallas dedicadas.

export const CONFIG_INFORME_VUELOS: ConfigInforme = {
  titulo: 'AODB',
  moduloCodigo: 'vuelos',
  endpointSimple: '/vuelos/informes/simple',
  endpointCompuesto: '/vuelos/informes/compuesto',
  filtros: [
    { id: 'periodo_inicio', etiqueta: 'Desde', tipo: 'fecha' },
    { id: 'periodo_fin', etiqueta: 'Hasta', tipo: 'fecha' },
    { id: 'aerolinea_id', etiqueta: 'Aerolínea (id)', tipo: 'texto' },
  ],
  columnasSimple: [
    { campo: 'vuelo_id', etiqueta: 'Vuelo' },
    { campo: 'fecha_operacion', etiqueta: 'Fecha' },
    { campo: 'aerolinea_id', etiqueta: 'Aerolínea' },
    { campo: 'numero_vuelo', etiqueta: 'Número' },
    { campo: 'sentido', etiqueta: 'Sentido' },
  ],
  columnaGrupo: 'Aerolínea',
  columnasMetricas: [
    { campo: 'con_llegada', etiqueta: 'Con llegada registrada' },
    { campo: 'puntualidad_pct', etiqueta: '% Puntualidad' },
  ],
};

export const CONFIG_INFORME_ASIGNACIONES: ConfigInforme = {
  titulo: 'Terminal & Gate Manager',
  moduloCodigo: 'puertas',
  endpointSimple: '/puertas/informes/simple',
  endpointCompuesto: '/puertas/informes/compuesto',
  filtros: [
    { id: 'periodo_inicio', etiqueta: 'Desde', tipo: 'fecha' },
    { id: 'periodo_fin', etiqueta: 'Hasta', tipo: 'fecha' },
    { id: 'puerta_id', etiqueta: 'Puerta (id)', tipo: 'texto' },
  ],
  columnasSimple: [
    { campo: 'asignacion_id', etiqueta: 'Asignación' },
    { campo: 'vuelo_id', etiqueta: 'Vuelo' },
    { campo: 'puerta_id', etiqueta: 'Puerta' },
    { campo: 'inicio_previsto', etiqueta: 'Inicio' },
    { campo: 'fin_previsto', etiqueta: 'Fin' },
    { campo: 'estado', etiqueta: 'Estado' },
  ],
  columnaGrupo: 'Puerta',
  columnasMetricas: [{ campo: 'con_conflicto', etiqueta: 'Con conflicto' }],
};

export const CONFIG_INFORME_TURNAROUNDS: ConfigInforme = {
  titulo: 'Ground Operations',
  moduloCodigo: 'rampa',
  endpointSimple: '/rampa/informes/simple',
  endpointCompuesto: '/rampa/informes/compuesto',
  filtros: [
    { id: 'periodo_inicio', etiqueta: 'Desde', tipo: 'fecha' },
    { id: 'periodo_fin', etiqueta: 'Hasta', tipo: 'fecha' },
    { id: 'estado', etiqueta: 'Estado', tipo: 'texto' },
  ],
  columnasSimple: [
    { campo: 'turnaround_id', etiqueta: 'Turnaround' },
    { campo: 'vuelo_llegada_id', etiqueta: 'Vuelo llegada' },
    { campo: 'vuelo_salida_id', etiqueta: 'Vuelo salida' },
    { campo: 'inicio_previsto', etiqueta: 'Inicio previsto' },
    { campo: 'estado', etiqueta: 'Estado' },
  ],
  columnaGrupo: 'Tipo de tarea',
  columnasMetricas: [
    { campo: 'completadas', etiqueta: 'Completadas' },
    { campo: 'con_incidencia', etiqueta: 'Con incidencia' },
  ],
};

export const CONFIG_INFORME_FACTURACION: ConfigInforme = {
  titulo: 'Revenue & Billing',
  moduloCodigo: 'billing',
  endpointSimple: '/billing/informes/simple',
  endpointCompuesto: '/billing/informes/compuesto',
  filtros: [
    { id: 'periodo_inicio', etiqueta: 'Desde', tipo: 'fecha' },
    { id: 'periodo_fin', etiqueta: 'Hasta', tipo: 'fecha' },
    { id: 'aerolinea_id', etiqueta: 'Aerolínea (id)', tipo: 'texto' },
    { id: 'estado', etiqueta: 'Estado', tipo: 'texto' },
  ],
  columnasSimple: [
    { campo: 'factura_id', etiqueta: 'Factura' },
    { campo: 'aerolinea_id', etiqueta: 'Aerolínea' },
    { campo: 'periodo_inicio', etiqueta: 'Período desde' },
    { campo: 'periodo_fin', etiqueta: 'Período hasta' },
    { campo: 'moneda', etiqueta: 'Moneda' },
    { campo: 'estado', etiqueta: 'Estado' },
  ],
  columnaGrupo: 'Concepto de cargo',
  columnasMetricas: [{ campo: 'cantidad_lineas', etiqueta: 'Líneas' }],
};

export const CONFIG_INFORME_TENANTS: ConfigInforme = {
  titulo: 'Tenants',
  moduloCodigo: 'tenants',
  endpointSimple: '/tenants/informes/simple',
  endpointCompuesto: '/tenants/informes/compuesto',
  filtros: [{ id: 'estado', etiqueta: 'Estado', tipo: 'texto' }],
  columnasSimple: [
    { campo: 'tenant_id', etiqueta: 'Tenant' },
    { campo: 'codigo', etiqueta: 'Código' },
    { campo: 'razon_social', etiqueta: 'Razón social' },
    { campo: 'plan_id', etiqueta: 'Plan' },
    { campo: 'estado', etiqueta: 'Estado' },
  ],
  columnaGrupo: 'Plan:Estado',
  columnasMetricas: [
    { campo: 'usuarios_activos', etiqueta: 'Usuarios activos' },
    { campo: 'licencias_vigentes', etiqueta: 'Licencias vigentes' },
  ],
};

export const CONFIG_INFORME_COMPLIANCE: ConfigInforme = {
  titulo: 'Compliance Hub',
  moduloCodigo: 'compliance',
  endpointSimple: '/compliance/informes/simple',
  endpointCompuesto: '/compliance/informes/compuesto',
  filtros: [
    { id: 'periodo_inicio', etiqueta: 'Desde', tipo: 'fecha' },
    { id: 'periodo_fin', etiqueta: 'Hasta', tipo: 'fecha' },
  ],
  columnasSimple: [
    { campo: 'evento_id', etiqueta: 'Evento' },
    { campo: 'esquema', etiqueta: 'Esquema' },
    { campo: 'tabla', etiqueta: 'Tabla' },
    { campo: 'operacion', etiqueta: 'Operación' },
    { campo: 'rol_codigo', etiqueta: 'Rol' },
    { campo: 'ocurrido_en', etiqueta: 'Ocurrido' },
  ],
  columnaGrupo: 'Tipo de reporte DGAC',
  columnasMetricas: [],
};
