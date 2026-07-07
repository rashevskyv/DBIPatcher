# 💎 DBI Patcher: localización universal

[English](README.md) | [Español](README_ES.md)

[![Última versión en GitHub](https://img.shields.io/github/v/release/rashevskyv/DBIPatcher)](https://github.com/rashevskyv/DBIPatcher/releases)
[![Descargas en GitHub](https://img.shields.io/github/downloads/rashevskyv/DBIPatcher/total)](https://github.com/rashevskyv/DBIPatcher/releases)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Motor avanzado de localización asistida por IA para [DBI](https://github.com/rashevskyv/dbi), una completa herramienta homebrew para Nintendo Switch. El proyecto ofrece traducciones para más de 22 idiomas y permite usar DBI en el idioma de cada usuario.

---

## 🌟 Características

- **🤖 Traducción asistida por IA**: utiliza **Claude 3.5 Sonnet** para generar traducciones sensibles al contexto.
- **🌍 Más de 22 idiomas**: incluye traducciones desde ucraniano hasta japonés y emplea inglés como respaldo automático.
- **📏 Alineación visual**: ajusta de forma inteligente los dos puntos, corchetes y espacios de la interfaz.
- **✅ Validación estricta**: comprueba tokens (`[[LF]]`, `[[TAB]]`), placeholders, paréntesis y estructura.
- **🚀 Despliegue automatizado**: prepara traducciones y versiones publicables mediante un mismo pipeline.

---

## 🛠️ Idiomas disponibles

| Código | Idioma | Código | Idioma |
| :--- | :--- | :--- | :--- |
| **UA** | Ucraniano | **EN** | Inglés (EE. UU.) |
| **BE** | Bielorruso | **ENGB** | Inglés (Reino Unido) |
| **PL** | Polaco | **DE** | Alemán |
| **FR** | Francés | **FRCA** | Francés (Canadá) |
| **IT** | Italiano | **ES** | Español (España) |
| **JP** | Japonés | **ES419** | Español (Latinoamérica) |
| **KR** | Coreano | **PT** | Portugués (Portugal) |
| **ZHCN** | Chino simplificado | **PTBR** | Portugués (Brasil) |
| **ZHTW** | Chino tradicional | **NL** | Neerlandés |
| **KK** | Kazajo | **ET** | Estonio |
| **LT** | Lituano | **LV** | Letón |

---

## 📥 Instalación

1. Abre la sección de [versiones publicadas](https://github.com/rashevskyv/DBIPatcher/releases/latest).
2. Descarga el **`DBI.nro`** compatible y el archivo `translation_XX.bin` correspondiente a tu idioma.
3. Cambia el nombre del archivo de traducción a `translation.bin`.
4. Copia `DBI.nro` y `translation.bin` en la misma carpeta de la tarjeta SD, normalmente `/switch/DBI/`.

> [!CAUTION]
> Cada traducción es compatible únicamente con el `DBI.nro` incluido en la misma versión publicada. Mezclar archivos de versiones diferentes puede provocar errores visuales o cierres inesperados.

Para español latinoamericano, utiliza `translation_es419.bin`. Para español de España, utiliza `translation_es.bin`.

---

## 🏗️ Uso del pipeline para desarrolladores

### Requisitos

- Python 3.12 o posterior.
- GitHub CLI (`gh`) para publicar versiones.
- Acceso a la API de Claude 3.5 mediante el proxy configurado por el proyecto.

### Preparación local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Controles de calidad

```powershell
# Validar el CSV latinoamericano y el binario generado
python -m unittest discover -s tests -v

# Generar solamente la traducción ES-419
python scripts/build_translation_bin.py translations/es419.csv -o output/translation_es419.bin

# Sincronizar el CSV ES-419 revisado con el diccionario maestro
python scripts/import_translation_csv.py es419
```

### Comandos principales

```powershell
# Ejecutar el ciclo completo de pruebas
python -m src.main test

# Publicar una versión en GitHub
python -m src.main deploy

# Ejecutar etapas individuales
python -m src.main sync       # Sincronizar el diccionario con los CSV fuente
python -m src.main translate  # Traducir cadenas pendientes mediante IA
python -m src.main align      # Corregir la alineación visual por bloques
python -m src.main validate   # Validar la integridad de las traducciones
python -m src.main build      # Generar archivos binarios de traducción
```

---

## ⚠️ Problemas conocidos

- ~~Algunos textos estaban integrados directamente en el binario y no podían traducirse mediante `translation.bin`, incluidos **Да** (Sí) y **Нет** (No).~~ ✅ Corregido.
- Las fábulas Shadok permanecen en su forma original.
- ~~Los nombres de idiomas del menú de configuración estaban integrados directamente en el binario.~~ ✅ Corregido.
- Las traducciones se han probado principalmente con [Kefir](https://github.com/rashevskyv/kefir). En ese entorno funcionan con [Sphaira](https://github.com/ITotalJustice/sphaira) y [nx-hbmenu](https://github.com/switchbrew/nx-hbmenu/releases/). Consulta el [issue #12](https://github.com/rashevskyv/DBIPatcher/issues/12) si la traducción no se aplica con otro entorno o lanzador.

---

## 🤝 Cómo contribuir

Las traducciones se encuentran en el directorio `translations/`:

1. Crea un fork del repositorio.
2. Modifica el CSV correspondiente a tu idioma.
3. Ejecuta los controles de calidad.
4. Envía un Pull Request.

Las contribuciones para español latinoamericano deben seguir la [guía de estilo ES-419](docs/es419-style-guide.md).

---

## 📜 Créditos

- **Creador de DBI**: [duckbill](https://github.com/rashevskyv/dbi).
- **Motor de localización**: [tg:@buinich_bohdan](https://github.com/rashevskyv).
- **Agradecimiento especial**: Claude 3.5 Sonnet por asistir en las traducciones.

> *Creado con ❤️ para la comunidad de Nintendo Switch.*
