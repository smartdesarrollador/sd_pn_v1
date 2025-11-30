"""
List Controller
Gestiona la lógica de negocio de listas avanzadas
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import DBManager
from core.clipboard_manager import ClipboardManager

logger = logging.getLogger(__name__)


class ListController(QObject):
    """
    Controlador para gestionar listas avanzadas

    Responsabilidades:
    - Validaciones de negocio
    - Orquestación de operaciones complejas
    - Emisión de señales PyQt6
    - Logging de operaciones
    """

    # Señales PyQt6 (nueva arquitectura v3.1.0 - usa list_id)
    list_created = pyqtSignal(int, int)  # (lista_id, category_id)
    list_updated = pyqtSignal(int, int)  # (lista_id, category_id)
    list_deleted = pyqtSignal(int, int)  # (lista_id, category_id)
    list_renamed = pyqtSignal(int, str, str, int)  # (lista_id, old_name, new_name, category_id)

    # Señales de ejecución secuencial
    execution_started = pyqtSignal(int, int)  # (lista_id, total_items)
    execution_step = pyqtSignal(int, str)  # (step_number, label)
    execution_completed = pyqtSignal(int)  # (lista_id)
    execution_cancelled = pyqtSignal()

    # Señales legacy (deprecadas - mantener para compatibilidad durante migración)
    list_created_legacy = pyqtSignal(str, int)  # (list_group, category_id)
    list_updated_legacy = pyqtSignal(str, int)  # (list_group, category_id)
    list_deleted_legacy = pyqtSignal(str, int)  # (list_group, category_id)

    # Señales de error
    error_occurred = pyqtSignal(str)  # (error_message)

    def __init__(self, db_manager: DBManager, clipboard_manager: ClipboardManager = None):
        """
        Inicializa el controlador de listas

        Args:
            db_manager: Gestor de base de datos
            clipboard_manager: Gestor de portapapeles (opcional)
        """
        super().__init__()
        self.db = db_manager
        self.clipboard_manager = clipboard_manager or ClipboardManager()

        # Estado de ejecución secuencial
        self._execution_timer = None
        self._execution_items = []
        self._execution_index = 0
        self._execution_list_name = ""
        self._execution_list_id = 0  # NUEVO: Guardar lista_id en ejecución

        logger.info("ListController initialized")

    # ========== VALIDACIONES ==========

    def validate_list_data(self, list_name: str, items_data: List[Dict[str, Any]],
                          category_id: int = None, exclude_list_id: int = None) -> tuple[bool, str]:
        """
        Valida los datos de una lista antes de crear/actualizar

        Args:
            list_name: Nombre de la lista
            items_data: Lista de datos de items
            category_id: ID de categoría (para validar nombre único)
            exclude_list_id: ID de lista a excluir en validación (para edición)

        Returns:
            Tuple (is_valid, error_message)
        """
        # Validar nombre de lista
        if not list_name or not list_name.strip():
            return False, "El nombre de la lista no puede estar vacío"

        if len(list_name) > 100:
            return False, "El nombre de la lista es demasiado largo (máximo 100 caracteres)"

        # Validar unicidad del nombre (usando método de DBManager)
        if category_id is not None:
            if not self.db.is_lista_name_unique(category_id, list_name, exclude_id=exclude_list_id):
                return False, f"Ya existe una lista con el nombre '{list_name}' en esta categoría"

        # Validar items
        if not items_data or len(items_data) == 0:
            return False, "La lista debe tener al menos un paso/item"

        if len(items_data) > 50:
            return False, "La lista no puede tener más de 50 pasos"

        # Validar cada item
        for i, item in enumerate(items_data, 1):
            if not item.get('label'):
                return False, f"El paso #{i} debe tener un nombre/label"

            if len(item.get('label', '')) > 200:
                return False, f"El nombre del paso #{i} es demasiado largo"

        return True, ""

    # ========== OPERACIONES CRUD ==========

    def create_list_from_items(self, list_name: str, category_id: int, item_ids: List[int]) -> tuple[bool, str, List[int]]:
        """
        Crea una nueva lista a partir de items existentes (por sus IDs)

        Automáticamente agrega los tags ["lista", "nombre_de_la_lista"] a cada item

        Args:
            list_name: Nombre de la lista
            category_id: ID de la categoría destino
            item_ids: Lista de IDs de items existentes

        Returns:
            Tuple (success, message, new_item_ids)
        """
        try:
            # Crear tags automáticos para la lista: ["lista", "nombre_de_la_lista"]
            auto_tags = ["lista"]
            if list_name:
                auto_tags.append(list_name)

            # Obtener datos de los items existentes
            items_data = []
            for item_id in item_ids:
                # Obtener item de la BD
                item = self.db.get_item(item_id)
                if item:
                    # Obtener tags existentes del item
                    existing_tags = item.get('tags', [])
                    if isinstance(existing_tags, str):
                        # Parsear si viene como string
                        try:
                            import json
                            existing_tags = json.loads(existing_tags)
                        except:
                            existing_tags = [tag.strip() for tag in existing_tags.split(',') if tag.strip()]

                    # Combinar tags automáticos con tags existentes (sin duplicados)
                    combined_tags = auto_tags.copy()
                    for tag in existing_tags:
                        if tag and tag not in combined_tags:
                            combined_tags.append(tag)

                    # Crear dict con los datos necesarios para la lista
                    item_data = {
                        'label': item.get('label', ''),
                        'content': item.get('content', ''),
                        'type': item.get('type', 'text'),
                        'icon': item.get('icon'),
                        'description': item.get('description'),
                        'is_sensitive': item.get('is_sensitive', False),
                        'tags': combined_tags  # Agregar tags automáticos + existentes
                    }
                    items_data.append(item_data)
                else:
                    logger.warning(f"Item {item_id} not found - skipping")

            if not items_data:
                error_msg = "No se encontraron items válidos para crear la lista"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False, error_msg, []

            # Usar create_list con los datos obtenidos
            success, message, lista_id, item_ids = self.create_list(category_id, list_name, items_data)
            return success, message, item_ids  # Mantener firma original para compatibilidad

        except Exception as e:
            error_msg = f"Error al crear lista desde items: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False, error_msg, []

    def create_list(self, category_id: int, list_name: str,
                   items_data: List[Dict[str, Any]], description: str = None) -> tuple[bool, str, int, List[int]]:
        """
        Crea una nueva lista con validaciones (nueva arquitectura v3.1.0)

        Args:
            category_id: ID de la categoría
            list_name: Nombre de la lista
            items_data: Lista de datos de items
            description: Descripción opcional de la lista

        Returns:
            Tuple (success, message, lista_id, item_ids)
        """
        # Validar datos
        is_valid, error_msg = self.validate_list_data(list_name, items_data, category_id)
        if not is_valid:
            logger.warning(f"Validación fallida al crear lista '{list_name}': {error_msg}")
            self.error_occurred.emit(error_msg)
            return False, error_msg, 0, []

        try:
            # 1. Crear registro en tabla listas
            lista_id = self.db.create_lista(category_id, list_name, description)

            # 2. Crear items con list_id
            item_ids = []
            for i, item_data in enumerate(items_data, start=1):
                item_id = self.db.add_item(
                    category_id=category_id,
                    label=item_data.get('label', ''),
                    content=item_data.get('content', ''),
                    item_type=item_data.get('type', 'text'),
                    icon=item_data.get('icon'),
                    description=item_data.get('description'),
                    is_sensitive=item_data.get('is_sensitive', False),
                    tags=item_data.get('tags', []),
                    list_id=lista_id,  # NUEVO: FK a tabla listas
                    orden_lista=i
                )
                item_ids.append(item_id)

            logger.info(f"Lista creada exitosamente: '{list_name}' (id={lista_id}, {len(item_ids)} items)")

            # Emitir señal nueva (con lista_id)
            self.list_created.emit(lista_id, category_id)

            # Emitir señal legacy para compatibilidad
            self.list_created_legacy.emit(list_name, category_id)

            return True, f"Lista '{list_name}' creada con {len(item_ids)} pasos", lista_id, item_ids

        except Exception as e:
            error_msg = f"Error al crear lista: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False, error_msg, 0, []

    def update_list(self, lista_id: int, new_name: str = None, description: str = None,
                   items_data: List[Dict[str, Any]] = None) -> tuple[bool, str]:
        """
        Actualiza una lista existente (nueva arquitectura v3.1.0)

        Args:
            lista_id: ID de la lista a actualizar
            new_name: Nuevo nombre (opcional)
            description: Nueva descripción (opcional)
            items_data: Nuevos datos de items (opcional)

        Returns:
            Tuple (success, message)
        """
        try:
            # Obtener lista actual
            lista = self.db.get_lista(lista_id)
            if not lista:
                error_msg = f"Lista con ID {lista_id} no encontrada"
                self.error_occurred.emit(error_msg)
                return False, error_msg

            old_name = lista['name']
            category_id = lista['category_id']

            # Si se está renombrando, validar nuevo nombre
            if new_name and new_name != old_name:
                is_valid, error_msg = self.validate_list_data(
                    new_name, items_data or [], category_id, exclude_list_id=lista_id
                )
                if not is_valid and "al menos un" not in error_msg:  # Ignorar error de items vacíos si solo renombramos
                    self.error_occurred.emit(error_msg)
                    return False, error_msg

            # Si se están actualizando items, validar
            if items_data is not None:
                final_name = new_name if new_name else old_name
                is_valid, error_msg = self.validate_list_data(final_name, items_data, category_id, exclude_list_id=lista_id)
                if not is_valid:
                    self.error_occurred.emit(error_msg)
                    return False, error_msg

            # 1. Actualizar metadata de lista
            updates = {}
            if new_name:
                updates['name'] = new_name
            if description is not None:
                updates['description'] = description

            if updates:
                self.db.update_lista(lista_id, **updates)

            # 2. Si hay items_data, actualizar items (eliminar viejos, crear nuevos)
            if items_data is not None:
                # Eliminar items actuales de la lista
                current_items = self.db.get_items_by_lista(lista_id)
                for item in current_items:
                    self.db.delete_item(item['id'])

                # Crear nuevos items
                for i, item_data in enumerate(items_data, start=1):
                    self.db.add_item(
                        category_id=category_id,
                        label=item_data.get('label', ''),
                        content=item_data.get('content', ''),
                        item_type=item_data.get('type', 'text'),
                        icon=item_data.get('icon'),
                        description=item_data.get('description'),
                        is_sensitive=item_data.get('is_sensitive', False),
                        tags=item_data.get('tags', []),
                        list_id=lista_id,
                        orden_lista=i
                    )

            final_name = new_name if new_name else old_name
            logger.info(f"Lista actualizada exitosamente: '{old_name}' -> '{final_name}' (id={lista_id})")

            # Emitir señales
            if new_name and new_name != old_name:
                self.list_renamed.emit(lista_id, old_name, new_name, category_id)
            else:
                self.list_updated.emit(lista_id, category_id)

            # Señales legacy
            self.list_updated_legacy.emit(final_name, category_id)

            return True, f"Lista '{final_name}' actualizada exitosamente"

        except Exception as e:
            error_msg = f"Error al actualizar lista: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False, error_msg

    def delete_list(self, lista_id: int) -> tuple[bool, str]:
        """
        Elimina una lista completa (nueva arquitectura v3.1.0)

        Args:
            lista_id: ID de la lista

        Returns:
            Tuple (success, message)
        """
        try:
            # Obtener datos de lista antes de eliminar
            lista = self.db.get_lista(lista_id)
            if not lista:
                error_msg = f"Lista con ID {lista_id} no encontrada"
                self.error_occurred.emit(error_msg)
                return False, error_msg

            list_name = lista['name']
            category_id = lista['category_id']

            # Eliminar de la base de datos (CASCADE eliminará items automáticamente)
            success = self.db.delete_lista(lista_id)

            if success:
                logger.info(f"Lista eliminada exitosamente: '{list_name}' (id={lista_id})")

                # Emitir señales
                self.list_deleted.emit(lista_id, category_id)
                self.list_deleted_legacy.emit(list_name, category_id)

                return True, f"Lista '{list_name}' eliminada"
            else:
                return False, "Error al eliminar lista"

        except Exception as e:
            error_msg = f"Error al eliminar lista: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False, error_msg

    def rename_list(self, lista_id: int, new_name: str) -> tuple[bool, str]:
        """
        Renombra una lista (wrapper conveniente de update_list)
        Nueva arquitectura v3.1.0

        Args:
            lista_id: ID de la lista
            new_name: Nuevo nombre

        Returns:
            Tuple (success, message)
        """
        return self.update_list(lista_id, new_name=new_name)

    # ========== CONSULTAS ==========

    def get_lists(self, category_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todas las listas de una categoría (nueva arquitectura v3.1.0)

        Args:
            category_id: ID de la categoría

        Returns:
            Lista de diccionarios con info de listas (desde tabla listas)
        """
        try:
            return self.db.get_listas_by_category_new(category_id)
        except Exception as e:
            logger.error(f"Error al obtener listas: {e}", exc_info=True)
            return []

    def get_list_items(self, lista_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene los items de una lista específica (nueva arquitectura v3.1.0)

        Args:
            lista_id: ID de la lista

        Returns:
            Lista de items ordenados por orden_lista
        """
        try:
            return self.db.get_items_by_lista(lista_id)
        except Exception as e:
            logger.error(f"Error al obtener items de lista: {e}", exc_info=True)
            return []

    def get_list_count(self, category_id: int) -> int:
        """
        Obtiene el número total de listas en una categoría

        Args:
            category_id: ID de la categoría

        Returns:
            Número de listas
        """
        listas = self.get_lists(category_id)
        return len(listas)

    # ========== OPERACIONES DE CLIPBOARD ==========

    def copy_all_list_items(self, lista_id: int, separator: str = '\n') -> tuple[bool, str]:
        """
        Copia todo el contenido de una lista al clipboard (nueva arquitectura v3.1.0)

        Args:
            lista_id: ID de la lista
            separator: Separador entre items (por defecto salto de línea)

        Returns:
            Tuple (success, message)
        """
        try:
            # Obtener datos de lista
            lista = self.db.get_lista(lista_id)
            if not lista:
                return False, f"Lista con ID {lista_id} no encontrada"

            items = self.get_list_items(lista_id)

            if not items:
                return False, "La lista está vacía"

            # Concatenar contenidos
            contents = [item['content'] for item in items]
            combined_content = separator.join(contents)

            # Copiar al clipboard
            success = self.clipboard_manager.copy_text(combined_content)

            if success:
                logger.info(f"Contenido completo de lista '{lista['name']}' (id={lista_id}) copiado al clipboard ({len(items)} items)")
                return True, f"Copiados {len(items)} pasos de '{lista['name']}'"
            else:
                return False, "Error al copiar al clipboard"

        except Exception as e:
            error_msg = f"Error al copiar lista: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False, error_msg

    # ========== EJECUCIÓN SECUENCIAL ==========

    def execute_list_sequentially(self, lista_id: int, delay_ms: int = 500) -> bool:
        """
        Ejecuta una lista secuencialmente, copiando cada item al clipboard con delay
        Nueva arquitectura v3.1.0

        Args:
            lista_id: ID de la lista
            delay_ms: Delay entre cada paso en milisegundos (default 500ms)

        Returns:
            bool: True si se inició la ejecución
        """
        try:
            # Obtener datos de lista
            lista = self.db.get_lista(lista_id)
            if not lista:
                self.error_occurred.emit(f"Lista con ID {lista_id} no encontrada")
                return False

            # Obtener items de la lista
            items = self.get_list_items(lista_id)

            if not items:
                self.error_occurred.emit("La lista está vacía")
                return False

            # Cancelar ejecución previa si existe
            self.cancel_execution()

            # Configurar ejecución
            self._execution_items = items
            self._execution_index = 0
            self._execution_list_id = lista_id  # Guardar lista_id en lugar de list_name
            self._execution_list_name = lista['name']  # Mantener para logs

            # Crear y configurar timer
            self._execution_timer = QTimer()
            self._execution_timer.timeout.connect(self._execute_next_step)

            # Emitir señal de inicio
            self.execution_started.emit(lista_id, len(items))
            logger.info(f"Iniciando ejecución secuencial de lista '{lista['name']}' (id={lista_id}, {len(items)} pasos, {delay_ms}ms delay)")

            # Ejecutar primer paso inmediatamente
            self._execute_next_step()

            # Iniciar timer para siguientes pasos
            if len(items) > 1:
                self._execution_timer.start(delay_ms)

            return True

        except Exception as e:
            error_msg = f"Error al ejecutar lista: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False

    def _execute_next_step(self):
        """Ejecuta el siguiente paso de la lista (método interno)"""
        if self._execution_index >= len(self._execution_items):
            # Ejecución completada
            self._finish_execution()
            return

        # Obtener item actual
        item = self._execution_items[self._execution_index]
        step_number = self._execution_index + 1

        try:
            # Copiar contenido al clipboard
            self.clipboard_manager.copy_text(item['content'])

            # Emitir señal de paso ejecutado
            self.execution_step.emit(step_number, item['label'])
            logger.debug(f"Paso {step_number}/{len(self._execution_items)} ejecutado: {item['label']}")

            # Incrementar índice
            self._execution_index += 1

        except Exception as e:
            logger.error(f"Error al ejecutar paso {step_number}: {e}")
            self._finish_execution()

    def _finish_execution(self):
        """Finaliza la ejecución secuencial"""
        if self._execution_timer:
            self._execution_timer.stop()
            self._execution_timer = None

        lista_id = getattr(self, '_execution_list_id', 0)
        list_name = self._execution_list_name
        self._execution_items = []
        self._execution_index = 0
        self._execution_list_name = ""
        self._execution_list_id = 0

        self.execution_completed.emit(lista_id)
        logger.info(f"Ejecución secuencial de lista '{list_name}' (id={lista_id}) completada")

    def cancel_execution(self):
        """Cancela la ejecución secuencial actual"""
        if self._execution_timer and self._execution_timer.isActive():
            self._execution_timer.stop()
            self._execution_timer = None
            self._execution_items = []
            self._execution_index = 0
            self._execution_list_name = ""
            self._execution_list_id = 0

            self.execution_cancelled.emit()
            logger.info("Ejecución secuencial cancelada")

    def is_executing(self) -> bool:
        """Retorna True si hay una ejecución secuencial en curso"""
        return self._execution_timer is not None and self._execution_timer.isActive()
