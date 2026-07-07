"""
Tests para el sistema de logging MTP.
Verifica que los registros, reportes y reintentos funcionen correctamente.
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from src.core.mtp_logger import LoggerMTP, GestorTransferenciaMTP, RegistroTransferencia


class TestRegistroTransferencia(unittest.TestCase):
    """Tests para RegistroTransferencia."""
    
    def test_crear_registro(self):
        """Verifica creación de registro."""
        registro = RegistroTransferencia("archivo.bin")
        self.assertEqual(registro.nombre_archivo, "archivo.bin")
        self.assertEqual(registro.estado, "pendiente")
        self.assertIsNone(registro.error)
    
    def test_marcar_exitoso(self):
        """Verifica marcar como exitoso."""
        registro = RegistroTransferencia("archivo.bin")
        registro.tiempo_inicio = datetime.now()
        registro.tiempo_fin = datetime.now()
        registro.velocidad_mbps = 45.5
        
        self.assertEqual(registro.velocidad_mbps, 45.5)
        self.assertIsNotNone(registro.tiempo_inicio)
    
    def test_convertir_diccionario(self):
        """Verifica conversión a diccionario."""
        registro = RegistroTransferencia("test.bin")
        registro.tamaño_bytes = 1024 * 1024  # 1 MB
        registro.estado = "exitoso"
        
        dic = registro.a_diccionario()
        self.assertEqual(dic["archivo"], "test.bin")
        self.assertEqual(dic["estado"], "exitoso")
        self.assertEqual(dic["tamaño_mb"], 1.0)


class TestLoggerMTP(unittest.TestCase):
    """Tests para LoggerMTP."""
    
    def setUp(self):
        """Crea logger temporal para cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = LoggerMTP(self.temp_dir)
    
    def tearDown(self):
        """Limpia archivos temporales."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_registrar_archivo(self):
        """Verifica registro de archivo."""
        registro = self.logger.registrar_archivo("archivo1.bin", 1024*1024)
        
        self.assertIn("archivo1.bin", self.logger.registros)
        self.assertEqual(registro.tamaño_bytes, 1024*1024)
    
    def test_marcar_exitoso(self):
        """Verifica marcar como exitoso."""
        self.logger.registrar_archivo("archivo1.bin", 1024)
        self.logger.marcar_exitoso("archivo1.bin", 50.0)
        
        registro = self.logger.registros["archivo1.bin"]
        self.assertEqual(registro.estado, "exitoso")
        self.assertEqual(registro.velocidad_mbps, 50.0)
    
    def test_marcar_fallido(self):
        """Verifica marcar como fallido."""
        self.logger.registrar_archivo("archivo1.bin")
        self.logger.marcar_fallido("archivo1.bin", "Desconexión USB", 2)
        
        registro = self.logger.registros["archivo1.bin"]
        self.assertEqual(registro.estado, "fallido")
        self.assertEqual(registro.error, "Desconexión USB")
        self.assertEqual(registro.reintentos, 2)
    
    def test_marcar_salteado(self):
        """Verifica marcar como salteado."""
        self.logger.registrar_archivo("archivo1.bin")
        self.logger.marcar_salteado("archivo1.bin", "Archivo no encontrado")
        
        registro = self.logger.registros["archivo1.bin"]
        self.assertEqual(registro.estado, "salteado")
        self.assertEqual(registro.error, "Archivo no encontrado")
    
    def test_resumen_sin_transferencias(self):
        """Verifica resumen vacío."""
        resumen = self.logger.obtener_resumen()
        
        self.assertEqual(resumen["total_archivos"], 0)
        self.assertEqual(resumen["exitosos"], 0)
    
    def test_resumen_con_transferencias(self):
        """Verifica resumen con archivos."""
        self.logger.registrar_archivo("archivo1.bin", 1024)
        self.logger.registrar_archivo("archivo2.bin", 2048)
        self.logger.registrar_archivo("archivo3.bin", 512)
        
        self.logger.marcar_exitoso("archivo1.bin")
        self.logger.marcar_fallido("archivo2.bin", "Error")
        self.logger.marcar_salteado("archivo3.bin", "Sin espacio")
        
        resumen = self.logger.obtener_resumen()
        
        self.assertEqual(resumen["total_archivos"], 3)
        self.assertEqual(resumen["exitosos"], 1)
        self.assertEqual(resumen["fallidos"], 1)
        self.assertEqual(resumen["salteados"], 1)
    
    def test_guardar_log_json(self):
        """Verifica que el archivo JSON se crea."""
        self.logger.registrar_archivo("archivo1.bin", 1024)
        self.logger._guardar_log()
        
        self.assertTrue(self.logger.archivo_log.exists())
        
        with open(self.logger.archivo_log, 'r') as f:
            datos = json.load(f)
            self.assertIn("resumen", datos)
            self.assertIn("registros", datos)
    
    def test_generar_reporte_texto(self):
        """Verifica generación de reporte."""
        self.logger.registrar_archivo("archivo1.bin", 1024*1024)
        self.logger.registrar_archivo("archivo2.bin", 512*1024)
        
        self.logger.marcar_exitoso("archivo1.bin", 45.0)
        self.logger.marcar_fallido("archivo2.bin", "Timeout", 1)
        
        reporte = self.logger.generar_reporte_texto()
        
        self.assertIn("REPORTE", reporte)
        self.assertIn("RESUMEN", reporte)
        self.assertIn("✅ Exitosos", reporte)
        self.assertIn("❌ Fallidos", reporte)
    
    def test_guardar_reporte(self):
        """Verifica que el reporte se guarda."""
        self.logger.registrar_archivo("archivo1.bin")
        self.logger.marcar_exitoso("archivo1.bin")
        
        self.logger.guardar_reporte()
        
        self.assertTrue(self.logger.archivo_reporte.exists())


class TestGestorTransferenciaMTP(unittest.TestCase):
    """Tests para GestorTransferenciaMTP."""
    
    def setUp(self):
        """Crea gestor temporal."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = LoggerMTP(self.temp_dir)
        self.gestor = GestorTransferenciaMTP(self.logger, reintentos_max=3)
    
    def tearDown(self):
        """Limpia archivos."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_simular_transferencia_exitosa(self):
        """Verifica simulación exitosa (sin fallos)."""
        resultado = self.gestor.simular_transferencia(
            "archivo1.bin", 1024*1024, probabilidad_fallo=0.0
        )
        
        self.assertTrue(resultado)
        self.assertEqual(self.logger.registros["archivo1.bin"].estado, "exitoso")
    
    def test_simular_transferencia_fallida(self):
        """Verifica simulación fallida (siempre falla)."""
        resultado = self.gestor.simular_transferencia(
            "archivo1.bin", 1024*1024, probabilidad_fallo=1.0
        )
        
        self.assertFalse(resultado)
        self.assertEqual(self.logger.registros["archivo1.bin"].estado, "fallido")
    
    def test_obtener_fallidos(self):
        """Verifica obtener lista de fallidos."""
        self.logger.registrar_archivo("archivo1.bin")
        self.logger.registrar_archivo("archivo2.bin")
        self.logger.registrar_archivo("archivo3.bin")
        
        self.logger.marcar_exitoso("archivo1.bin")
        self.logger.marcar_fallido("archivo2.bin", "Error")
        self.logger.marcar_fallido("archivo3.bin", "Error")
        
        fallidos = self.gestor.obtener_fallidos()
        
        self.assertEqual(len(fallidos), 2)
        self.assertIn("archivo2.bin", fallidos)
        self.assertIn("archivo3.bin", fallidos)
    
    def test_reintentos_limitados(self):
        """Verifica que reintentos respetan el máximo."""
        gestor = GestorTransferenciaMTP(self.logger, reintentos_max=2)
        resultado = gestor.simular_transferencia(
            "archivo1.bin", 1024, probabilidad_fallo=1.0
        )
        
        self.assertFalse(resultado)
        self.assertEqual(self.logger.registros["archivo1.bin"].reintentos, 2)


class TestIntegracionMTP(unittest.TestCase):
    """Tests de integración del sistema MTP."""
    
    def setUp(self):
        """Crea entorno para test."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = LoggerMTP(self.temp_dir)
        self.gestor = GestorTransferenciaMTP(self.logger)
    
    def tearDown(self):
        """Limpia archivos."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_flujo_completo_transferencia(self):
        """Verifica flujo completo con múltiples archivos."""
        archivos = [
            ("game1.nsp", 2000*1024*1024),
            ("game2.nsp", 3000*1024*1024),
            ("game3.nsp", 1500*1024*1024),
            ("update.nsp", 500*1024*1024),
        ]
        
        for nombre, tamaño in archivos:
            self.gestor.simular_transferencia(nombre, tamaño, probabilidad_fallo=0.2)
        
        resumen = self.logger.obtener_resumen()
        reporte = self.logger.generar_reporte_texto()
        
        self.assertEqual(resumen["total_archivos"], 4)
        self.assertIn("exitosos", resumen)
        self.assertIn("REPORTE", reporte)
    
    def test_reporte_con_todos_estados(self):
        """Verifica reporte con todos los estados."""
        self.logger.registrar_archivo("exitoso.nsp", 1024*1024)
        self.logger.registrar_archivo("fallido.nsp", 2048*1024)
        self.logger.registrar_archivo("salteado.nsp", 512*1024)
        
        self.logger.marcar_exitoso("exitoso.nsp", 45.0)
        self.logger.marcar_fallido("fallido.nsp", "Desconexión", 2)
        self.logger.marcar_salteado("salteado.nsp", "No hay espacio")
        
        reporte = self.logger.guardar_reporte()
        
        # Verificar que contiene todas las secciones
        self.assertIn("EXITOSOS", reporte)
        self.assertIn("FALLIDOS", reporte)
        self.assertIn("SALTEADOS", reporte)
        self.assertIn("Porcentaje de éxito", reporte)


if __name__ == "__main__":
    unittest.main()
