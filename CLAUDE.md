# CLAUDE.md

Este archivo proporciona guía a Claude Code (claude.ai/code) al trabajar con código en este repositorio.

## Descripción del Proyecto

**SidePanel** es una aplicación de escritorio para Windows diseñada como un gestor avanzado de portapapeles y biblioteca de snippets. Construida con PyQt6 y SQLite, proporciona un sidebar persistente siempre visible en el borde derecho de la pantalla para acceso instantáneo a comandos, URLs, fragmentos de código y texto frecuentemente utilizados.

### Propósito
Facilitar el flujo de trabajo de usuarios mediante:
- Acceso inmediato a comandos y snippets sin cambiar de aplicación
- Organización inteligente de contenido mediante categorías personalizables
- Copiar al portapapeles con un solo clic desde cualquier lugar
- Protección de información sensible con cifrado y autenticación

### Características Principales
- **Sidebar persistente**: Panel lateral frameless de 70px, siempre visible (always-on-top)
- **Gestión por categorías**: Organización jerárquica con iconos emoji y sistema de tags
- **Seguridad robusta**: Autenticación con contraseña maestra, cifrado Fernet para items sensibles
- **Búsqueda global**: Búsqueda en tiempo real a través de todas las categorías e items
- **Sistema de favoritos**: Marcado rápido de items más utilizados
- **Tracking de uso**: Estadísticas y analytics de frecuencia de uso
- **Filtrado avanzado**: Múltiples criterios (texto, rangos numéricos, fechas, métricas)
- **Hotkey global**: `Ctrl+Shift+V` muestra/oculta el widget desde cualquier aplicación
- **Integración system tray**: Minimiza a bandeja del sistema con menú contextual
- **Navegador embebido**: Captura de snippets desde páginas web con detección automática
- **Dashboard estadístico**: Visualización de métricas de uso y patrones

**Versión:** 3.0.0 (SQLite Edition)
**Plataforma:** Windows 10/11
**Python:** 3.10+

## Comandos de Desarrollo

### Ejecutar la Aplicación
```bash
# Desde el código fuente (requiere Python 3.10+)
python main.py

# Desde entorno virtual
.\venv\Scripts\activate
python main.py
```

### Construir Ejecutable
```bash
# Construir .exe standalone con PyInstaller
build.bat

# Ubicación salida: dist\WidgetSidebar.exe
# Paquete distribución: WidgetSidebar_v2.0\
```

### Dependencias
```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# Dependencias principales:
# - PyQt6 (6.7.0) - Framework GUI
# - pyperclip (1.9.0) - Gestión del portapapeles
# - pynput (1.7.7) - Captura de hotkeys globales
# - cryptography (41.0.7) - Cifrado para items sensibles
# - python-dotenv (1.0.0) - Gestión de variables de entorno
# - bcrypt (4.0.1) - Hash de contraseñas
# - PyQtWebEngine (6.7.0) - Navegador embebido
```

## Arquitectura

### Patrón MVC
La aplicación sigue la arquitectura Model-View-Controller:

- **Models** (`src/models/`): Estructuras de datos (Category, Item, Config, TagGroup)
- **Views** (`src/views/`): Componentes UI PyQt6 (MainWindow, Sidebar, ContentPanel, SettingsWindow, FloatingPanel)
- **Controllers** (`src/controllers/`): Lógica de negocio (MainController, ClipboardController, NavigationController)

### Core Managers (`src/core/`)
Managers especializados que gestionan funcionalidades específicas:

- `config_manager.py`: Persistencia de configuración vía SQLite
- `clipboard_manager.py`: Operaciones de portapapeles usando pyperclip
- `hotkey_manager.py`: Manejo de hotkeys globales con pynput
- `tray_manager.py`: Integración con bandeja del sistema (system tray)
- `search_engine.py`: Búsqueda en tiempo real con debouncing (300ms)
- `state_manager.py`: Gestión del estado de la aplicación
- `auth_manager.py`: Autenticación de usuarios con hash bcrypt
- `session_manager.py`: Gestión de sesiones con expiración automática (24h)
- `encryption_manager.py`: Cifrado Fernet para contenido sensible
- `favorites_manager.py`: Seguimiento y gestión de favoritos
- `usage_tracker.py`: Estadísticas y analytics de uso de items
- `stats_manager.py`: Agregación de estadísticas para dashboard
- `notification_manager.py`: Sistema de notificaciones in-app
- `category_filter_engine.py`: Filtrado de categorías con caché LRU
- `advanced_filter_engine.py`: Filtrado multi-criterio complejo
- `tag_manager.py`: Gestión de tags y grupos de tags
- `export_manager.py`: Exportación/importación de datos (JSON, CSV)

### Capa de Base de Datos (`src/database/`)
La aplicación utiliza SQLite para persistencia:

- `db_manager.py`: Operaciones de BD con context managers para transacciones
- `migrations.py`: Migraciones de esquema de base de datos
- Archivo de BD: `widget_sidebar.db` (se crea automáticamente en primera ejecución)

Esquema incluye: `settings`, `categories`, `items`, `clipboard_history`, `tag_groups`, `item_tags`, `sessions`

**Importante:** La conexión a BD usa `check_same_thread=False` para compatibilidad con PyQt6. Siempre usar el context manager de transacciones para operaciones de escritura:
```python
with db.transaction() as conn:
    conn.execute(...)
```

**Cifrado de Items Sensibles:** Items marcados con `is_sensitive=True` tienen su campo `content` automáticamente cifrado en la capa de BD usando cifrado Fernet. El cifrado/descifrado ocurre transparentemente en `DBManager.add_item()`, `DBManager.update_item()`, y `DBManager.get_items_by_category()`.

### Flujo de Punto de Entrada
1. `main.py` inicializa logging y maneja rutas de ejecución frozen/script
2. Crea instancia de QApplication
3. **Flujo de autenticación:**
   - `SessionManager` verifica sesión válida
   - Si es primera vez: `FirstTimeWizard` para creación de contraseña
   - Si es usuario recurrente: `LoginDialog` para ingreso de contraseña
   - En fallo: sale de la aplicación
4. Crea `MainController` que inicializa `ConfigManager` con SQLite
5. `ConfigManager` carga categorías/items desde BD (auto-descifra items sensibles)
6. `MainWindow` se crea con referencia al controller
7. Se inicializan hotkey manager y tray manager
8. Categorías se cargan en UI del sidebar

### Arquitectura de Ventanas
- **MainWindow**: Sidebar frameless, always-on-top (70px ancho, 80% altura pantalla)
- **FloatingPanel**: Ventana separada para mostrar items de categoría, posicionada adyacente al sidebar
- **FavoritesFloatingPanel**: Panel dedicado para vista de favoritos
- **StatsFloatingPanel**: Panel de dashboard estadístico
- **GlobalSearchPanel**: Búsqueda en pantalla completa a través de todos los items
- **SettingsWindow**: Diálogo modal con 4 pestañas (Categorías, Apariencia, Hotkeys, General)
- **CategoryFilterWindow**: Interfaz de filtrado de categorías
- **AdvancedFiltersWindow**: UI de filtrado multi-criterio complejo
- **FirstTimeWizard**: Wizard de configuración de contraseña en primera ejecución
- **LoginDialog**: Diálogo de autenticación en ejecuciones subsecuentes
- **CategoryEditor**: Editor CRUD completo para categorías
- **ItemEditor**: Editor CRUD completo para items con validación
- **EmbeddedBrowserDialog**: Navegador embebido para captura de snippets desde web
- **CreateItemsWithIADialog**: Wizard de creación masiva de items con IA

### Comunicación Signal/Slot
Las señales PyQt6 conectan componentes:
- `category_selected` (str): Emitida cuando se hace clic en categoría del sidebar
- `item_selected` (Item): Emitida cuando se hace clic en item del content panel
- `item_copied` (Item): Emitida después de copiar exitosamente al portapapeles
- `filters_applied`: Emitida cuando se aplican filtros a categorías
- `tag_group_selected`: Emitida cuando se selecciona un grupo de tags

## Detalles Clave de Implementación

### Autenticación y Seguridad
- **Protección con Contraseña**: Primera ejecución muestra `FirstTimeWizard` para establecer contraseña maestra
- **Gestión de Sesiones**: Las sesiones expiran automáticamente (24h por defecto), almacenadas en BD
- **Hash de Contraseñas**: Usa bcrypt vía `AuthManager` para almacenamiento seguro
- **Cifrado**: Items sensibles cifrados con Fernet (cifrado simétrico)
  - Clave de cifrado almacenada en archivo `.env` (auto-generada en primera ejecución)
  - Derivación de clave: PBKDF2 desde contraseña maestra
  - Cifrado/descifrado transparente en capa de BD

### Sistema de Hotkeys
- Hotkey global `Ctrl+Shift+V` alterna visibilidad del widget desde cualquier aplicación
- Gestionado por `HotkeyManager` usando listener de teclado pynput
- Ejecuta en thread de fondo, comunica vía señales PyQt6

### Bandeja del Sistema
- Minimiza a system tray en lugar de cerrar
- Menú contextual: Mostrar/Ocultar, Configuración, Salir
- Doble clic en ícono del tray restaura la ventana

### Funcionalidad de Búsqueda
- Filtrado en tiempo real en `search_bar.py` con debounce de 300ms
- `search_engine.py` proporciona coincidencia fuzzy en nombres y contenido de items
- Filtra items dentro de categoría activa

### Favoritos y Tracking de Uso
- Items pueden marcarse como favoritos (campo `is_favorite`)
- `usage_tracker.py` rastrea uso de items con métricas:
  - Timestamp de último uso
  - Contador de uso
  - Patrones de uso (analytics basados en tiempo)
- `favorites_manager.py` proporciona filtrado y gestión de favoritos
- Estadísticas disponibles en `StatsFloatingPanel` y `StatsDashboard`

### Filtrado de Categorías
- **Filtrado Básico**: `CategoryFilterWindow` filtra por estado activo/fijado
- **Filtrado Avanzado**: `AdvancedFiltersWindow` soporta:
  - Búsqueda de texto (nombre, tags, contenido)
  - Rangos de conteo de items
  - Métricas de uso (conteo de accesos, rangos de fechas)
  - Múltiples criterios con lógica AND
- **Motor de Filtros**: `CategoryFilterEngine` con caché LRU para rendimiento

### Búsqueda Global
- `GlobalSearchPanel` busca a través de TODOS los items en TODAS las categorías
- Filtrado en tiempo real con debouncing
- Muestra contexto de categoría para cada resultado
- Clic en resultado copia contenido al portapapeles

### Sistema de Tags
- **Tag Groups**: Grupos de tags para organización jerárquica
- **Tag Association**: Items pueden tener múltiples tags
- **Tag Filtering**: Filtrado rápido de categorías por tags
- Base de datos: tablas `tag_groups` y `item_tags`

### Persistencia de Configuración
**Migración de JSON a SQLite:** La aplicación originalmente usaba archivos JSON (`config.json`, `default_categories.json`). Ahora usa SQLite exclusivamente. El script `build.bat` incluye paso de migración de JSON a BD.

### Build con PyInstaller
- Archivo spec: `widget_sidebar.spec`
- Incluye base de datos SQLite, recursos, e imports ocultos para pynput
- Modo consola deshabilitado (`console=False`)
- Compresión UPX habilitada

## Estructura del Proyecto
```
widget_sidebar/
├── main.py                      # Punto de entrada de la aplicación
├── widget_sidebar.db            # Base de datos SQLite (auto-creada)
├── config.json                  # Configuración legacy (deprecada)
├── default_categories.json      # Datos semilla de categorías por defecto
├── requirements.txt             # Dependencias Python
├── widget_sidebar.spec          # Configuración PyInstaller
├── build.bat                    # Script de build para exe de Windows
├── .env                         # Variables de entorno (clave cifrado)
└── src/
    ├── models/                  # Modelos de datos (Category, Item, Config, TagGroup)
    ├── views/                   # Componentes UI PyQt6
    │   ├── main_window.py       # Ventana principal frameless
    │   ├── sidebar.py           # Sidebar de categorías
    │   ├── floating_panel.py    # Panel de visualización de items
    │   ├── settings_window.py   # Diálogo de configuración
    │   ├── dialogs/             # Diálogos especializados (editors, wizards)
    │   └── widgets/             # Widgets UI reutilizables
    ├── controllers/             # Capa de lógica de negocio
    ├── core/                    # Funcionalidad core (config, clipboard, hotkeys, tray, search)
    ├── database/                # Gestión base de datos SQLite
    ├── utils/                   # Utilidades (animations, validators, constants, logger)
    └── resources/               # Recursos estáticos
```

## Convenciones Importantes

### Organización de Archivos Temporales y de Desarrollo

**IMPORTANTE:** Para mantener el repositorio limpio, TODOS los archivos temporales, de prueba y documentación local deben crearse dentro de la carpeta `util/`:

#### Archivos que SIEMPRE deben ir en `util/`:
- **Scripts de prueba**: `test_*.py` - Scripts de desarrollo/pruebas temporales
- **Scripts de debug**: `debug_*.py` - Scripts de debugging y diagnóstico
- **Scripts de demostración**: `demo_*.py` - Ejemplos y demos
- **Scripts de migración**: `migrate_*.py` - Migraciones de BD one-time
- **Scripts de población de datos**: `populate_*.py`, `add_*.py` - Scripts para agregar datos de prueba
- **Scripts de verificación**: `check_*.py`, `fix_*.py` - Utilidades de verificación y corrección
- **Scripts run**: `run_*.py` - Scripts para ejecutar migraciones u operaciones únicas
- **Documentación temporal**: `FASE*.md`, `GUIA_*.md` - Documentación de desarrollo local
- **Ejemplos JSON**: Datos de ejemplo y plantillas
- **Capturas de pantalla**: Screenshots y documentación visual

#### Archivos en la raíz del proyecto:
Solo estos archivos Python deben estar en la raíz:
- `main.py` - Punto de entrada de la aplicación
- Archivos de configuración: `requirements.txt`, `build.bat`, `.gitignore`, etc.
- Documentación oficial: `README.md`, `CLAUDE.md`, `LICENSE`

#### Ejemplo de uso:
```python
# ❌ MAL - No crear en la raíz
# test_nueva_feature.py (en raíz del proyecto)

# ✅ BIEN - Crear en util/
# util/test_nueva_feature.py
```

**Nota:** La carpeta `util/` completa está excluida del repositorio git. Los archivos ahí son solo para desarrollo local.

### Manejo de Rutas
La aplicación soporta ejecución como script y frozen (exe):
```python
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent  # Ejecutando como exe
else:
    base_dir = Path(__file__).parent        # Ejecutando como script
```
Siempre usar este patrón al referenciar archivos de la aplicación.

### Variables de Entorno
- Archivo `.env` almacena clave de cifrado (auto-generada)
- Nunca hacer commit de `.env` al control de versiones
- `EncryptionManager` maneja generación y carga de claves

### Logging
Logging comprehensivo configurado en `main.py`:
- Archivo log: `widget_sidebar_error.log` (sobrescrito cada sesión)
- Nivel log: DEBUG
- Manejador de excepciones global captura excepciones no atrapadas
- Usar `logger = logging.getLogger(__name__)` en cada módulo

### Posicionamiento de Ventanas
MainWindow se posiciona en borde derecho de pantalla con márgenes 10%:
```python
screen_height = screen.availableGeometry().height()
window_height = int(screen_height * 0.8)  # 80% altura
```

### Acceso a Base de Datos
- ConfigManager posee la instancia de DBManager
- Siempre cerrar BD al salir de aplicación (manejado en MainController.__del__)
- Usar transacciones para integridad de datos
- **Invalidación de Caché**: Llamar `controller.invalidate_filter_cache()` después de cualquier modificación en BD para asegurar coherencia de caché de filtros

## Tareas Comunes

### Agregar Nueva Categoría Programáticamente
```python
# Vía DBManager directamente
category_id = db.add_category(
    name='Nueva Categoría',
    icon='🆕',
    is_predefined=False
)
```

### Agregar Items a Categoría
```python
# Item regular
item_id = db.add_item(
    category_id=category_id,
    label='Mi Comando',
    content='git status',
    item_type='CODE'
)

# Item sensible (auto-cifrado)
item_id = db.add_item(
    category_id=category_id,
    label='API Key',
    content='sk-1234567890',
    item_type='TEXT',
    is_sensitive=True  # El contenido será cifrado
)
```

### Trabajar con Contenido Cifrado
```python
# El cifrado ocurre automáticamente en DBManager
# Al agregar/actualizar items:
db.add_item(..., is_sensitive=True)  # Contenido cifrado antes de almacenar

# Al recuperar items:
items = db.get_items_by_category(cat_id)  # Contenido auto-descifrado si es sensible
```

### Gestionar Sesiones
```python
from core.session_manager import SessionManager

session_mgr = SessionManager()
# Verificar si sesión es válida
if session_mgr.validate_session():
    print("Sesión válida")
else:
    # Mostrar diálogo de login
    pass
```

### Trabajar con Tags
```python
# Los tags se pasan directamente al crear el item
item_id = db.add_item(
    category_id=category_id,
    label='Mi Script Python',
    content='import asyncio...',
    item_type='CODE',
    tags=['python', 'async', 'backend']  # Tags como lista
)

# Los tags también se pueden actualizar
db.update_item(
    item_id=item_id,
    tags=['python', 'async', 'backend', 'nuevo-tag']
)
```

### Modificar Hotkey Global
Editar `src/core/hotkey_manager.py` y actualizar la combinación de teclas en el método `setup_hotkeys()`.

## Historial de Versiones

- **3.0.0** (SQLite Edition):
  - Migración completa a SQLite
  - Ventana de configuración con CRUD completo para categorías/items
  - Sistema de tags y grupos de tags
  - Navegador embebido para captura de snippets
  - Wizard de creación masiva con IA
  - Personalización de apariencia
  - Exportación/importación de datos
  - Dashboard de estadísticas
  - Filtrado avanzado multi-criterio

- **2.0.0**:
  - Hotkeys globales
  - Integración system tray
  - Funcionalidad de búsqueda
  - Inicio de migración SQLite

- **1.0.0**:
  - Release inicial con sidebar
  - Content panel
  - Tema oscuro
  - Animaciones
