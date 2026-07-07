# 📋 Logger MTP - Documentación

## 🎯 Propósito

Sistema de logging robusto para **transferencias masivas MTP** que:

✅ Rastrea cada archivo transferido (exitoso, fallido, salteado)  
✅ Registra errores específicos de cada transferencia  
✅ Genera reportes detallados en texto y JSON  
✅ Implementa reintentos automáticos configurables  
✅ Proporciona estadísticas de velocidad y tiempo  

---

## 📦 Componentes

### 1. `RegistroTransferencia`
Almacena información de un archivo individual.

**Atributos:**
- `nombre_archivo`: Nombre del archivo
- `estado`: "pendiente", "exitoso", "fallido", "salteado"
- `error`: Mensaje de error (si aplica)
- `tamaño_bytes`: Tamaño del archivo
- `reintentos`: Número de reintentos
- `velocidad_mbps`: Velocidad de transferencia

### 2. `LoggerMTP`
Logger persistente que maneja múltiples transferencias.

**Métodos principales:**
```python
# Registrar un archivo
registro = logger.registrar_archivo("archivo.bin", 1024*1024)

# Marcar estados
logger.marcar_exitoso("archivo.bin", velocidad_mbps=45.5)
logger.marcar_fallido("archivo.bin", "Error: conexión perdida", reintentos=2)
logger.marcar_salteado("archivo.bin", "Archivo no encontrado")

# Obtener resumen
resumen = logger.obtener_resumen()

# Generar reportes
reporte_txt = logger.generar_reporte_texto()
logger.guardar_reporte()  # Guarda JSON y TXT
logger.mostrar_resumen_consola()
```

### 3. `GestorTransferenciaMTP`
Gestor de transferencias con reintentos automáticos.

**Métodos:**
```python
# Simular transferencia (para testing)
exitoso = gestor.simular_transferencia(
    nombre="archivo.nsp",
    tamaño_bytes=3000*1024*1024,
    probabilidad_fallo=0.1  # 10% de fallo
)

# Obtener fallidos
fallidos = gestor.obtener_fallidos()
```

---

## 💻 Uso Básico

### Ejemplo 1: Transferencia Simple

```python
from src.core.mtp_logger import LoggerMTP

# Crear logger
logger = LoggerMTP(directorio_logs="logs")

# Registrar archivo
logger.registrar_archivo("game.nsp", tamaño_bytes=2000*1024*1024)

# Simular transferencia exitosa
logger.marcar_exitoso("game.nsp", velocidad_mbps=50.0)

# Mostrar resumen
logger.mostrar_resumen_consola()
```

### Ejemplo 2: Transferencia Masiva con Reintentos

```python
from src.core.mtp_logger import LoggerMTP, GestorTransferenciaMTP

# Crear logger y gestor
logger = LoggerMTP()
gestor = GestorTransferenciaMTP(logger, reintentos_max=3)

# Archivos para transferir
archivos = [
    ("game1.nsp", 2000*1024*1024),
    ("game2.nsp", 3000*1024*1024),
    ("update.nsp", 500*1024*1024),
]

# Simular transferencias
for nombre, tamaño in archivos:
    exitoso = gestor.simular_transferencia(
        nombre, tamaño, 
        probabilidad_fallo=0.15  # 15% de chance de fallar
    )
    
    if not exitoso:
        print(f"⚠️  {nombre} falló después de reintentos")

# Mostrar reporte
logger.mostrar_resumen_consola()
```

### Ejemplo 3: Integración con DBI

```python
from src.core.mtp_logger import LoggerMTP

def transferir_traduccion(archivos_nsp):
    """Transferir múltiples archivos con logging."""
    
    logger = LoggerMTP("logs/dbi_transfers")
    
    for archivo_nsp in archivos_nsp:
        try:
            registro = logger.registrar_archivo(
                archivo_nsp.name,
                tamaño_bytes=archivo_nsp.stat().st_size
            )
            registro.tiempo_inicio = datetime.now()
            
            # Transferir archivo (tu código DBI aquí)
            # dbi.transfer_file(archivo_nsp)
            
            logger.marcar_exitoso(archivo_nsp.name, velocidad_mbps=45.0)
            
        except Exception as e:
            logger.marcar_fallido(
                archivo_nsp.name,
                str(e),
                reintentos=1
            )
    
    # Guardar reporte
    logger.mostrar_resumen_consola()
    logger.guardar_reporte()
```

---

## 📊 Formato de Resumen

```
╔════════════════════════════════════════════════════════════╗
║        REPORTE DE TRANSFERENCIA MTP MASIVA                 ║
╚════════════════════════════════════════════════════════════╝

📊 RESUMEN GENERAL
────────────────────────────────────────────────────────────
  Total de archivos:     10
  ✅ Exitosos:           8
  ❌ Fallidos:           1
  ⏭️  Salteados:          1
  Porcentaje de éxito:   80.0%

📦 DATOS TRANSFERIDOS
────────────────────────────────────────────────────────────
  Bytes transferidos:    15,000,000,000
  MB transferidos:       14305.12 MB
  Tiempo total:          300.45 segundos

❌ ARCHIVOS FALLIDOS
────────────────────────────────────────────────────────────
  • game_corrupted.nsp
    Error: Checksum mismatch
    Reintentos: 3

⏭️  ARCHIVOS SALTEADOS
────────────────────────────────────────────────────────────
  • game_duplicate.nsp
    Razón: Archivo duplicado detectado

✅ ARCHIVOS EXITOSOS (primeros 10)
────────────────────────────────────────────────────────────
  • game1.nsp @ 50.2 MB/s
  • game2.nsp @ 48.9 MB/s
  • game3.nsp @ 51.1 MB/s
  ...
```

---

## 📁 Estructura de Archivos Generados

```
logs/
├── transferencia_mtp_20260705_143025.json
│   ├── timestamp
│   ├── resumen (estadísticas)
│   └── registros (detalle por archivo)
│
└── reporte_mtp_20260705_143025.txt
    └── Reporte legible formateado
```

### Formato JSON

```json
{
  "timestamp": "2026-07-05T14:30:25.123456",
  "resumen": {
    "total_archivos": 3,
    "exitosos": 2,
    "fallidos": 1,
    "salteados": 0,
    "bytes_transferidos": 5368709120,
    "mb_transferidos": 5120.0,
    "tiempo_total_segundos": 102.34,
    "porcentaje_exito": 66.7
  },
  "registros": {
    "game1.nsp": {
      "archivo": "game1.nsp",
      "estado": "exitoso",
      "error": null,
      "tamaño_mb": 2048.0,
      "tiempo_segundos": 40.5,
      "reintentos": 0,
      "velocidad_mbps": 50.6
    }
  }
}
```

---

## 🧪 Tests Disponibles

```bash
# Ejecutar todos los tests MTP
python -m unittest tests.test_mtp_logging -v

# Test específico
python -m unittest tests.test_mtp_logging.TestLoggerMTP.test_marcar_exitoso -v

# Con cobertura
python -m coverage run -m unittest discover -s tests -p "test_*.py"
python -m coverage report
```

---

## ⚙️ Configuración

### Cambiar directorio de logs
```python
logger = LoggerMTP(directorio_logs="custom/path/logs")
```

### Cambiar máximo de reintentos
```python
gestor = GestorTransferenciaMTP(logger, reintentos_max=5)
```

### Cambiar probabilidad de fallo (testing)
```python
gestor.simular_transferencia(archivo, tamaño, probabilidad_fallo=0.25)
```

---

## 🔧 Integración con Pipeline DBIPatcher

Este módulo está diseñado para ser integrado en el comando `deploy`:

```python
# En src/main.py
from src.core.mtp_logger import LoggerMTP, GestorTransferenciaMTP

def cmd_deploy(...):
    """Desplegar traducciones y monitorear transferencias."""
    
    logger = LoggerMTP()
    
    # ... código de transferencia ...
    
    logger.mostrar_resumen_consola()
    logger.guardar_reporte()
```

---

## ✅ Características Completadas

- ✅ Registro individual de transferencias
- ✅ Tracking de estados (exitoso, fallido, salteado)
- ✅ Reporte en texto y JSON
- ✅ Sistema de reintentos configurable
- ✅ Estadísticas de velocidad
- ✅ Cobertura de testing completa (15+ tests)
- ✅ Documentación en español

---

## 📝 Notas

- Los logs se guardan en `logs/` por defecto
- Cada sesión genera nuevos archivos con timestamp
- El reporte se muestra automáticamente en consola
- Compatible con Python 3.12+
- Sin dependencias externas requeridas
