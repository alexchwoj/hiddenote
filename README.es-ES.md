

<img width="1920" height="1080" alt="hiddennote" src="https://github.com/user-attachments/assets/55c51112-65f6-425e-b6ef-4ec2bc95c5b2" />


# hiddenote

Una aplicación de toma de notas cifrada construida con Python y PyQt6.
Todas las notas se cifran localmente: no se envía nada a ningún servidor.

## Características

### Seguridad

- **Hash de contraseñas Argon2id** con migración automática desde bases de datos SHA-256 v1
- **Cifrado AES-256** (Fernet) con clave derivada por PBKDF2
- **Cambiar contraseña maestra** — vuelve a cifrar todas las notas de forma transparente
- **Bloqueo automático** tras un tiempo de inactividad configurable
- **Límite de intentos fallidos** — 5 contraseñas incorrectas cierran la aplicación
- **Verificación de integridad HMAC** — detecta manipulaciones externas en la base de datos al iniciar
- **Copia de seguridad cifrada** — copia el archivo de la base de datos en cualquier momento

### Editor

- **Editor Markdown** con vista previa en vivo (tablas, bloques de código, tabla de contenidos, resaltado de sintaxis)
- **Buscar y reemplazar** (`Ctrl+H`) con anterior / siguiente / reemplazar todo y modo sensible a mayúsculas/minúsculas
- **Números de línea** (alternar con clic derecho)
- **Contador en vivo de palabras y caracteres** e indicador de línea / columna en la barra de estado
- **Insertar fecha y hora** en el cursor (`Ctrl+Shift+D`)
- **Modo solo lectura** por nota
- **Imprimir** la vista previa renderizada (`Ctrl+P`)
- **Autoguardado** con un retraso (debounce) de 1,5 s

### Organización

- **Etiquetas** — múltiples etiquetas por nota, filtrar la lista por etiqueta
- **Fijar** notas importantes en la parte superior (★)
- **Archivar** notas antiguas sin eliminarlas
- **Papelera** — eliminación suave con limpieza automática de 30 días; la eliminación permanente requiere una segunda confirmación
- **Filtros de vista** — Todos / Fijados / Archivados / Papelera
- **Ordenar** por última actualización, fecha de creación o título
- **Renombrar** notas desde el menú contextual

### Exportar e importar

- Exportar notas como **Markdown**, **HTML** o **texto sin formato**
- Importar archivos `.txt` / `.md` desde el disco
- Copia de seguridad manual de la base de datos desde el diálogo de Configuración

### Historial

- **Historial de versiones** — hasta 20 instantáneas por nota, guardadas con `Ctrl+S` o al salir de la nota
- **Restaurar** cualquier instantánea anterior con un solo clic

## Atajos

| Atajo                 | Acción                                              |
| --------------------- | --------------------------------------------------- |
| `Ctrl+N` / `Insert`   | Nueva nota                                          |
| `Ctrl+S`              | Guardar y crear instantánea de versión              |
| `Ctrl+F`              | Enfocar búsqueda de notas                           |
| `Ctrl+H`              | Buscar y reemplazar en el editor                    |
| `Ctrl+Shift+D`        | Insertar fecha y hora actual                        |
| `Ctrl+L`              | Bloquear aplicación                                 |
| `Ctrl+P`              | Imprimir                                            |
| `Delete`              | Mover la nota seleccionada a la papelera            |
| Clic derecho en nota  | Renombrar, fijar, archivar, etiquetas, exportar, historial de versiones |
| Clic derecho en editor| Alternar números de línea, opciones de diseño       |

## Requisitos

- Python 3.9+
- Dependencias listadas en `requirements.txt`

```text
argon2-cffi
cryptography
Markdown
Pygments
PyQt6
```

### Dependencias adicionales para Linux

```bash
sudo apt install -y libxcb-cursor0 libxcb-cursor-dev binutils python3-dev
```

## Instalación

```bash
git clone https://github.com/alexchwoj/hiddenote.git
cd hiddenote
pip install -r requirements.txt
python main.py
```

## Compilación

```bash
# Windows
python build.py --platform windows

# Linux
python build.py --platform linux

# macOS
python build.py --platform macos
```

## Registro de cambios

Consulte [CHANGELOG.md](CHANGELOG.md) para ver el historial completo de versiones.


## Capturas de pantalla
<img width="1200" height="800" alt="image" src="https://github.com/user-attachments/assets/f08b82b4-a9f9-4877-aa9c-dde1ff5eaeb9" />
<img width="1204" height="806" alt="image" src="https://github.com/user-attachments/assets/271a9340-4d2f-45fb-856e-0252506f74b7" />
<img width="1205" height="806" alt="image" src="https://github.com/user-attachments/assets/5d7129b7-0d5e-47d2-a24d-a6a0fce07876" />


## Licencia

MIT: consulte [LICENSE](LICENSE) para más detalles.
