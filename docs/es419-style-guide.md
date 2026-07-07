# Guía de estilo para español latinoamericano (ES-419)

Esta guía define el criterio editorial para `translations/es419.csv`. El objetivo
es ofrecer una interfaz clara, breve y natural para usuarios latinoamericanos sin
alterar identificadores técnicos ni la estructura que DBI necesita en tiempo de
ejecución.

## Voz y tono

- Usar español latinoamericano neutro y tratamiento de **tú**.
- Preferir instrucciones directas: **Selecciona**, **Presiona**, **Ingresa**.
- Evitar regionalismos, voseo y traducciones literales del ruso o del inglés.
- Usar mayúscula inicial de oración; no capitalizar cada palabra de un menú.

## Terminología preferida

| Concepto | Usar | Evitar |
| --- | --- | --- |
| Settings | Configuración | Ajustes, Opciones |
| Press a button | Presiona | Pulsa, Oprime |
| Backup (interfaz) | Respaldo | Copia, Backup |
| Restore | Restaurar | Recuperar |
| Save data | Datos de guardado | Saves, partidas guardadas |
| Storage | Almacenamiento | Depósito |
| File browser | Explorador de archivos | Navegador de archivos |
| Dump (acción técnica) | Volcar | Dumpear |
| Shortcut | Acceso directo | Atajo |
| Update (sustantivo) | Actualización | Update |

Mantener sin traducir los identificadores y protocolos técnicos: `DBI`, `NAND`,
`SysNAND`, `SD`, `NRO`, `NSP`, `NSZ`, `XCI`, `XCZ`, `MTP`, `FTP`, `HTTP`,
`TitleID`, `SDK`, `LFS`, nombres de archivos, rutas y comandos.

## Restricciones técnicas

- Conservar exactamente placeholders como `{}`, `{:02X}`, `%s` y similares.
- Conservar tokens como `[[LF]]`, `[[TAB]]`, `[[CR]]` y `[[ESC]]`.
- No cambiar secuencias escapadas como `\\n`, `\\t` o `\\x1b`.
- Preservar saltos de línea, espacios significativos, dos puntos y paréntesis.
- No traducir rutas, direcciones URL, nombres de archivos ni valores de configuración.
- Preferir textos breves para evitar cortes o desbordamientos en la pantalla.

## Lista de revisión

Antes de aceptar una modificación:

1. Leer la cadena dentro de su menú o mensaje completo.
2. Comprobar que el término coincide con esta guía.
3. Verificar placeholders, tokens, espacios y saltos de línea.
4. Ejecutar `python -m unittest discover -s tests -v`.
5. Generar `translation_es419.bin` y probar la pantalla afectada en DBI 895.

Las traducciones destinadas a otra versión de DBI deben mantenerse separadas
hasta confirmar la compatibilidad exacta del `DBI.nro` correspondiente.
