"""
Logger robusto para transferencias MTP masivas.
Rastrea archivos exitosos, fallidos y proporciona reportes detallados.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


class RegistroTransferencia:
    """Almacena información de una transferencia individual."""
    
    def __init__(self, nombre_archivo: str):
        self.nombre_archivo = nombre_archivo
        self.estado = "pendiente"  # pendiente, exitoso, fallido, salteado
        self.error = None
        self.tamaño_bytes = 0
        self.tiempo_inicio = None
        self.tiempo_fin = None
        self.reintentos = 0
        self.velocidad_mbps = 0.0
    
    def a_diccionario(self) -> dict:
        """Convierte el registro a diccionario para JSON."""
        return {
            "archivo": self.nombre_archivo,
            "estado": self.estado,
            "error": self.error,
            "tamaño_mb": round(self.tamaño_bytes / (1024**2), 2),
            "tiempo_segundos": self._calcular_tiempo(),
            "reintentos": self.reintentos,
            "velocidad_mbps": round(self.velocidad_mbps, 2)
        }
    
    def _calcular_tiempo(self) -> float:
        """Calcula tiempo transcurrido en segundos."""
        if self.tiempo_inicio and self.tiempo_fin:
            return (self.tiempo_fin - self.tiempo_inicio).total_seconds()
        return 0.0


class LoggerMTP:
    """Logger persistente para transferencias MTP masivas."""
    
    def __init__(self, directorio_logs: str = "logs"):
        """
        Inicializa el logger MTP.
        
        Args:
            directorio_logs: Ruta donde guardar los logs
        """
        self.directorio_logs = Path(directorio_logs)
        self.directorio_logs.mkdir(exist_ok=True)
        
        # Nombre del archivo log con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archivo_log = self.directorio_logs / f"transferencia_mtp_{timestamp}.json"
        self.archivo_reporte = self.directorio_logs / f"reporte_mtp_{timestamp}.txt"
        
        # Registros de transferencias
        self.registros: Dict[str, RegistroTransferencia] = {}
        self.hora_inicio = datetime.now()
        self.total_bytes = 0
        
        # Inicializar archivo log
        self._guardar_log()
    
    def registrar_archivo(self, nombre_archivo: str, tamaño_bytes: int = 0) -> RegistroTransferencia:
        """Registra un nuevo archivo para transferencia."""
        registro = RegistroTransferencia(nombre_archivo)
        registro.tamaño_bytes = tamaño_bytes
        self.registros[nombre_archivo] = registro
        self.total_bytes += tamaño_bytes
        return registro
    
    def marcar_exitoso(self, nombre_archivo: str, velocidad_mbps: float = 0.0):
        """Marca un archivo como transferido exitosamente."""
        if nombre_archivo in self.registros:
            registro = self.registros[nombre_archivo]
            registro.estado = "exitoso"
            registro.tiempo_fin = datetime.now()
            registro.velocidad_mbps = velocidad_mbps
    
    def marcar_fallido(self, nombre_archivo: str, error: str, reintentos: int = 0):
        """Marca un archivo como fallido."""
        if nombre_archivo in self.registros:
            registro = self.registros[nombre_archivo]
            registro.estado = "fallido"
            registro.error = error
            registro.reintentos = reintentos
            registro.tiempo_fin = datetime.now()
    
    def marcar_salteado(self, nombre_archivo: str, razon: str):
        """Marca un archivo como salteado."""
        if nombre_archivo in self.registros:
            registro = self.registros[nombre_archivo]
            registro.estado = "salteado"
            registro.error = razon
    
    def obtener_resumen(self) -> dict:
        """Retorna resumen de la transferencia."""
        exitosos = [r for r in self.registros.values() if r.estado == "exitoso"]
        fallidos = [r for r in self.registros.values() if r.estado == "fallido"]
        salteados = [r for r in self.registros.values() if r.estado == "salteado"]
        
        bytes_exitosos = sum(r.tamaño_bytes for r in exitosos)
        tiempo_total = (datetime.now() - self.hora_inicio).total_seconds()
        
        return {
            "total_archivos": len(self.registros),
            "exitosos": len(exitosos),
            "fallidos": len(fallidos),
            "salteados": len(salteados),
            "bytes_transferidos": bytes_exitosos,
            "mb_transferidos": round(bytes_exitosos / (1024**2), 2),
            "tiempo_total_segundos": round(tiempo_total, 2),
            "porcentaje_exito": round((len(exitosos) / len(self.registros) * 100) if self.registros else 0, 1)
        }
    
    def _guardar_log(self):
        """Guarda el registro actual en JSON."""
        datos = {
            "timestamp": datetime.now().isoformat(),
            "resumen": self.obtener_resumen(),
            "registros": {nombre: r.a_diccionario() for nombre, r in self.registros.items()}
        }
        
        with open(self.archivo_log, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    
    def generar_reporte_texto(self) -> str:
        """Genera reporte legible en texto."""
        resumen = self.obtener_resumen()
        
        exitosos = [r for r in self.registros.values() if r.estado == "exitoso"]
        fallidos = [r for r in self.registros.values() if r.estado == "fallido"]
        salteados = [r for r in self.registros.values() if r.estado == "salteado"]
        
        lineas = [
            "╔════════════════════════════════════════════════════════════╗",
            "║        REPORTE DE TRANSFERENCIA MTP MASIVA                 ║",
            "╚════════════════════════════════════════════════════════════╝",
            "",
            "📊 RESUMEN GENERAL",
            "─" * 60,
            f"  Total de archivos:     {resumen['total_archivos']}",
            f"  ✅ Exitosos:           {resumen['exitosos']}",
            f"  ❌ Fallidos:           {resumen['fallidos']}",
            f"  ⏭️  Salteados:          {resumen['salteados']}",
            f"  Porcentaje de éxito:   {resumen['porcentaje_exito']}%",
            "",
            "📦 DATOS TRANSFERIDOS",
            "─" * 60,
            f"  Bytes transferidos:    {resumen['bytes_transferidos']:,}",
            f"  MB transferidos:       {resumen['mb_transferidos']} MB",
            f"  Tiempo total:          {resumen['tiempo_total_segundos']} segundos",
            ""
        ]
        
        if fallidos:
            lineas.extend([
                "❌ ARCHIVOS FALLIDOS",
                "─" * 60,
            ])
            for registro in fallidos:
                lineas.append(f"  • {registro.nombre_archivo}")
                lineas.append(f"    Error: {registro.error}")
                lineas.append(f"    Reintentos: {registro.reintentos}")
            lineas.append("")
        
        if salteados:
            lineas.extend([
                "⏭️  ARCHIVOS SALTEADOS",
                "─" * 60,
            ])
            for registro in salteados:
                lineas.append(f"  • {registro.nombre_archivo}")
                lineas.append(f"    Razón: {registro.error}")
            lineas.append("")
        
        if exitosos:
            lineas.extend([
                "✅ ARCHIVOS EXITOSOS (primeros 10)",
                "─" * 60,
            ])
            for registro in exitosos[:10]:
                velocidad = f" @ {registro.velocidad_mbps:.1f} MB/s" if registro.velocidad_mbps > 0 else ""
                lineas.append(f"  • {registro.nombre_archivo}{velocidad}")
            
            if len(exitosos) > 10:
                lineas.append(f"  ... y {len(exitosos) - 10} más")
            lineas.append("")
        
        lineas.extend([
            "📁 ARCHIVOS DE LOG",
            "─" * 60,
            f"  JSON: {self.archivo_log}",
            f"  TXT:  {self.archivo_reporte}",
            ""
        ])
        
        return "\n".join(lineas)
    
    def guardar_reporte(self):
        """Guarda el reporte en archivo de texto."""
        reporte = self.generar_reporte_texto()
        with open(self.archivo_reporte, 'w', encoding='utf-8') as f:
            f.write(reporte)
        return reporte
    
    def mostrar_resumen_consola(self):
        """Imprime el resumen en consola."""
        self._guardar_log()
        reporte = self.guardar_reporte()
        print(reporte)


class GestorTransferenciaMTP:
    """Gestor de transferencias MTP con reintentos y recuperación."""
    
    def __init__(self, logger: LoggerMTP, reintentos_max: int = 3):
        """
        Inicializa el gestor.
        
        Args:
            logger: Instancia del logger MTP
            reintentos_max: Máximo número de reintentos por archivo
        """
        self.logger = logger
        self.reintentos_max = reintentos_max
        self.fallidos_con_reintentos = {}
    
    def simular_transferencia(self, nombre_archivo: str, tamaño_bytes: int, 
                             probabilidad_fallo: float = 0.1) -> bool:
        """
        Simula una transferencia (para testing).
        
        Args:
            nombre_archivo: Nombre del archivo
            tamaño_bytes: Tamaño en bytes
            probabilidad_fallo: Probabilidad de fallo (0.0-1.0)
        
        Returns:
            True si fue exitoso, False si falló
        """
        import random
        
        registro = self.logger.registrar_archivo(nombre_archivo, tamaño_bytes)
        registro.tiempo_inicio = datetime.now()
        
        reintentos = 0
        while reintentos < self.reintentos_max:
            if random.random() > probabilidad_fallo:
                # Exitoso
                velocidad = tamaño_bytes / (1024**2) / random.uniform(0.5, 2.0)
                self.logger.marcar_exitoso(nombre_archivo, velocidad)
                return True
            
            reintentos += 1
            if reintentos < self.reintentos_max:
                print(f"  ADVERTENCIA: {nombre_archivo}: Reintentando ({reintentos}/{self.reintentos_max})...")
        
        # Falló después de reintentos
        self.logger.marcar_fallido(nombre_archivo, "Error de conexión USB", reintentos)
        self.fallidos_con_reintentos[nombre_archivo] = reintentos
        return False
    
    def obtener_fallidos(self) -> List[str]:
        """Retorna lista de archivos fallidos."""
        return [r.nombre_archivo for r in self.logger.registros.values() 
                if r.estado == "fallido"]
