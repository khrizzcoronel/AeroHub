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
  // Grafico del dashboard (feedback directo del usuario 2026-08-07: las
  // tablas crudas "estorban" -- se reemplazan por un grafico de barras por
  // defecto, con boton "Ver detalle" para la tabla). Agrupa client-side las
  // filas YA CARGADAS por este campo -- mismo principio que los KPI
  // (§2 punto 3 del plan: un conteo en el cliente no es un informe
  // compuesto). Sin campoAgrupacion, la seccion no ofrece grafico y
  // muestra la tabla directamente.
  campoAgrupacion?: string;
  // Color fijo por valor crudo del campo de agrupacion (variable CSS).
  // Reservado para agrupaciones que SI son un estado real con semaforo ya
  // establecido en otra vista del modulo (facturas, turnarounds, tenants) --
  // dataviz skill: "status colors are reserved, never reused for series
  // identity". Sin entrada para un valor -> COLOR_DEFAULT (categorico
  // neutro, no evaluativo).
  colorPorValor?: Record<string, string>;
  // Etiqueta legible para un valor crudo (p. ej. 'L' -> 'Llegada'). Sin
  // entrada -> se usa el valor con guiones bajos reemplazados por espacios.
  etiquetasCategoria?: Record<string, string>;
}

// Los 4 tonos de semaforo ya establecidos en toda la app
// (docs/diseno/DIRECCION_VISUAL.md) -- el unico lugar donde entra color
// saturado. COLOR_DEFAULT (blue-500, "accion primaria") se usa para
// agrupaciones que no son un estado evaluativo (p. ej. sentido L/S).
const COLOR_OK = 'var(--ah-estado-ok)';
const COLOR_ATENCION = 'var(--ah-estado-atencion)';
const COLOR_CRITICO = 'var(--ah-estado-critico)';
const COLOR_NEUTRO = 'var(--ah-estado-neutro)';
export const COLOR_DEFAULT = 'var(--ah-blue-500)';

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
  campoAgrupacion: 'sentido',
  etiquetasCategoria: { L: 'Llegada', S: 'Salida' },
};

export const CONFIG_INFORME_ASIGNACIONES: ConfigInforme = {
  titulo: 'Gestión de Terminales y Puertas',
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
  campoAgrupacion: 'estado',
};

export const CONFIG_INFORME_TURNAROUNDS: ConfigInforme = {
  titulo: 'Operaciones de Rampa',
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
  campoAgrupacion: 'estado',
  // Mismo mapeo que claseEstadoTurnaround en rampa/panel-turnaround --
  // aca no se distingue el refinamiento "vencido" (el informe simple no
  // trae fin_previsto), asi que en_curso queda en atencion sin importar
  // si esta demorado.
  colorPorValor: {
    planificado: COLOR_NEUTRO,
    en_curso: COLOR_ATENCION,
    completado: COLOR_OK,
    interrumpido: COLOR_CRITICO,
  },
};

export const CONFIG_INFORME_FACTURACION: ConfigInforme = {
  titulo: 'Facturación e Ingresos',
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
  campoAgrupacion: 'estado',
  // Mismo mapeo que claseEstadoFactura en billing/panel-facturas.
  colorPorValor: {
    borrador: COLOR_NEUTRO,
    emitida: COLOR_ATENCION,
    pagada: COLOR_OK,
    vencida: COLOR_CRITICO,
    disputada: COLOR_CRITICO,
  },
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
  campoAgrupacion: 'estado',
  // Mismo mapeo que claseEstadoTenant en tenants/tenant-list.
  colorPorValor: {
    en_onboarding: COLOR_NEUTRO,
    activo: COLOR_OK,
    suspendido: COLOR_ATENCION,
    dado_de_baja: COLOR_CRITICO,
  },
};

export const CONFIG_INFORME_COMPLIANCE: ConfigInforme = {
  titulo: 'Centro de Cumplimiento',
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
  // El log de auditoria no tiene un campo de "estado" propio -- agrupar
  // por tabla es lo que responde la pregunta real de un auditor/SRE
  // ("que tabla concentra la actividad auditada"), sin semaforo (no es
  // un valor evaluativo bueno/malo).
  campoAgrupacion: 'tabla',
};

// ---------------------------------------------------------------------------
// Dashboards operativos por rol (docs/diseno/PLAN_DASHBOARDS_OPERATIVOS.md,
// implementado 2026-08-07). Reemplaza el barrido "una seccion por scope de
// modulo" de antes -- cada rol de la capa operativa ve una pregunta de
// jornada concreta, resuelta con KPI derivados del lado SIMPLE (MonetDB,
// consulta en vivo) de cada informe. Nada de aca llama a
// GET /analytics/tactico/* -- ese endpoint y el resto de la infraestructura
// de ClickHouse (aerohub_analytics_api, tools/sincronizar_analytics_demo.py)
// se dejan intactos, sin consumidor operativo, reservados para el dashboard
// TACTICO real que llegue con la Fase 2/S2.4 (decision D4(a) del plan) --
// endpointCompuesto/moduloCodigo de ConfigInforme se conservan en el tipo
// por eso, aunque el dashboard operativo no los use.
export interface KpiOperativo {
  etiqueta: string;
  // Indice dentro de `secciones` de este rol -- el KPI se calcula sobre las
  // filas YA CARGADAS de esa seccion, nunca con una llamada nueva al
  // backend (principio del plan §2, punto 3: "un conteo en el cliente
  // sobre filas ya traidas no es un informe compuesto").
  seccionIndice: number;
  calculo: (filas: Record<string, unknown>[]) => number;
}

export interface DashboardRolConfig {
  rolCodigo: string;
  // Una oracion: que pregunta de jornada responde este dashboard (plan §4).
  pregunta: string;
  secciones: ConfigInforme[];
  kpis: KpiOperativo[];
}

const contarTotal = (filas: Record<string, unknown>[]): number => filas.length;

const contarPorValor =
  (campo: string, valor: string) =>
  (filas: Record<string, unknown>[]): number =>
    filas.filter((f) => f[campo] === valor).length;

const contarDistintoDe =
  (campo: string, valor: string) =>
  (filas: Record<string, unknown>[]): number =>
    filas.filter((f) => f[campo] !== valor).length;

// D1(a) del plan: role_ramp_agent usa el informe de turnarounds del
// tenant tal cual (no existe un endpoint "mis tareas del periodo" --
// construirlo es trabajo de backend nuevo, fuera de alcance de este pase).
export const DASHBOARDS_POR_ROL: Record<string, DashboardRolConfig> = {
  role_operations_controller: {
    rolCodigo: 'role_operations_controller',
    pregunta: '¿Cómo viene la operación del turno?',
    secciones: [CONFIG_INFORME_VUELOS, CONFIG_INFORME_ASIGNACIONES, CONFIG_INFORME_TURNAROUNDS],
    kpis: [
      { etiqueta: 'Vuelos del período', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Asignaciones del período', seccionIndice: 1, calculo: contarTotal },
      { etiqueta: 'Turnarounds del período', seccionIndice: 2, calculo: contarTotal },
      {
        etiqueta: 'Turnarounds no completados',
        seccionIndice: 2,
        calculo: contarDistintoDe('estado', 'completado'),
      },
    ],
  },
  role_billing_officer: {
    rolCodigo: 'role_billing_officer',
    pregunta: '¿Qué facturas requieren acción?',
    secciones: [CONFIG_INFORME_FACTURACION],
    kpis: [
      { etiqueta: 'Emitidas', seccionIndice: 0, calculo: contarPorValor('estado', 'emitida') },
      { etiqueta: 'Pagadas', seccionIndice: 0, calculo: contarPorValor('estado', 'pagada') },
      { etiqueta: 'Vencidas', seccionIndice: 0, calculo: contarPorValor('estado', 'vencida') },
      { etiqueta: 'Disputadas', seccionIndice: 0, calculo: contarPorValor('estado', 'disputada') },
    ],
  },
  role_airline_coordinator: {
    rolCodigo: 'role_airline_coordinator',
    pregunta: '¿Cómo van los vuelos de mi aerolínea?',
    // M6 Passenger queda fuera (D2(a) del plan): sin informe simple hoy,
    // y GET /passenger/tiempos-espera exige terminal_id+fecha puntuales
    // (no acepta rango), no encaja con este dashboard.
    secciones: [CONFIG_INFORME_VUELOS],
    kpis: [
      { etiqueta: 'Vuelos del período', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Llegadas', seccionIndice: 0, calculo: contarPorValor('sentido', 'L') },
      { etiqueta: 'Salidas', seccionIndice: 0, calculo: contarPorValor('sentido', 'S') },
    ],
  },
  role_ramp_agent: {
    rolCodigo: 'role_ramp_agent',
    pregunta: '¿Qué tengo que hacer ahora?',
    secciones: [CONFIG_INFORME_TURNAROUNDS],
    kpis: [
      { etiqueta: 'Turnarounds del período', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'En curso', seccionIndice: 0, calculo: contarPorValor('estado', 'en_curso') },
      { etiqueta: 'Interrumpidos', seccionIndice: 0, calculo: contarPorValor('estado', 'interrumpido') },
    ],
  },
  role_tenant_admin: {
    rolCodigo: 'role_tenant_admin',
    pregunta: '¿Cómo va la operación de mi tenant hoy?',
    // Union de los 4 informes operativos -- M9 (capa estrategica) y M2/M6
    // (brechas D2/D3, sin informe) quedan fuera, igual que Tenancy
    // (capa de plataforma, no aplica a este rol).
    secciones: [
      CONFIG_INFORME_VUELOS,
      CONFIG_INFORME_ASIGNACIONES,
      CONFIG_INFORME_TURNAROUNDS,
      CONFIG_INFORME_FACTURACION,
    ],
    kpis: [
      { etiqueta: 'Vuelos', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Asignaciones', seccionIndice: 1, calculo: contarTotal },
      { etiqueta: 'Turnarounds', seccionIndice: 2, calculo: contarTotal },
      { etiqueta: 'Facturas', seccionIndice: 3, calculo: contarTotal },
    ],
  },
  // Fuera del alcance formal del plan (capa de plataforma, §7 "que NO
  // cubre"), pero se preserva con el mismo mecanismo nuevo para no
  // regresionar el unico informe que este rol ya podia ver (Tenants,
  // scope tenants:administrar) -- sin esto, el enlace "Dashboard" se le
  // habria quedado vacio de la nada al cambiar el mecanismo de deteccion
  // de "por scope" a "por rol".
  role_platform_admin: {
    rolCodigo: 'role_platform_admin',
    pregunta: '¿Cómo está la base de tenants?',
    secciones: [CONFIG_INFORME_TENANTS],
    kpis: [
      { etiqueta: 'Tenants', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Activos', seccionIndice: 0, calculo: contarPorValor('estado', 'activo') },
      { etiqueta: 'Suspendidos', seccionIndice: 0, calculo: contarPorValor('estado', 'suspendido') },
    ],
  },
  // docs/diseno/PLAN_CORRECCION_Y_DASHBOARD_ROLES_RESTANTES.md §2.1 --
  // unicos 2 de los 10 roles restantes con GRANT de motor real verificado
  // (compliance.log_auditoria, 93_grants_compliance.sql:25/27). El resto
  // (role_tenant_analyst, role_business_viewer) queda fuera a proposito:
  // tienen scope de aplicacion pero la matriz 4.3.1 les niega el GRANT,
  // un dashboard ahi solo devolveria 403 en cada seccion.
  role_sre: {
    rolCodigo: 'role_sre',
    pregunta: '¿Qué actividad de auditoría requiere atención?',
    secciones: [CONFIG_INFORME_COMPLIANCE],
    kpis: [
      { etiqueta: 'Eventos del período', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Inserciones', seccionIndice: 0, calculo: contarPorValor('operacion', 'INSERT') },
      { etiqueta: 'Actualizaciones', seccionIndice: 0, calculo: contarPorValor('operacion', 'UPDATE') },
    ],
  },
  role_regulatory_auditor: {
    rolCodigo: 'role_regulatory_auditor',
    pregunta: '¿Qué eventos de auditoría se registraron?',
    secciones: [CONFIG_INFORME_COMPLIANCE],
    kpis: [
      { etiqueta: 'Eventos del período', seccionIndice: 0, calculo: contarTotal },
      { etiqueta: 'Inserciones', seccionIndice: 0, calculo: contarPorValor('operacion', 'INSERT') },
      { etiqueta: 'Actualizaciones', seccionIndice: 0, calculo: contarPorValor('operacion', 'UPDATE') },
    ],
  },
};
