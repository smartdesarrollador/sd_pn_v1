"""
Manager para creación masiva de items mediante IA.

Este manager orquesta todo el proceso de bulk import:
1. Generación de prompts personalizados
2. Validación de JSON importado
3. Parseo de items desde JSON
4. Creación masiva en base de datos
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

from models.bulk_item_data import (
    BulkItemData,
    BulkItemDefaults,
    BulkImportConfig,
    ValidationResult,
    BulkCreationResult
)
from utils.json_validator import BulkJSONValidator
from utils.prompt_templates import PromptTemplate
from database.db_manager import DBManager

logger = logging.getLogger(__name__)


class AIBulkItemManager:
    """
    Manager principal para creación masiva de items con IA.

    Funcionalidades:
    - Generar prompts personalizados para IAs
    - Validar JSON importado
    - Parsear items desde JSON con merge de defaults
    - Crear items masivamente con transacciones
    - Reportar estadísticas y errores
    """

    def __init__(self, db_manager: DBManager):
        """
        Inicializa el manager.

        Args:
            db_manager: Instancia de DBManager para acceso a BD
        """
        self.db = db_manager
        self.validator = BulkJSONValidator()
        logger.info("AIBulkItemManager initialized")

    def generate_prompt(
        self,
        config: BulkImportConfig,
        simple: bool = False
    ) -> str:
        """
        Genera prompt personalizado para IA.

        Args:
            config: Configuración del bulk import
            simple: Si True, usa template simplificado

        Returns:
            String con el prompt generado
        """
        config_dict = {
            'category_id': config.category_id,
            'category_name': config.category_name,
            'item_type': config.defaults.type,
            'tags': config.defaults.tags,
            'is_favorite': config.defaults.is_favorite,
            'is_sensitive': config.defaults.is_sensitive,
            'is_list': config.defaults.is_list,
            'list_group': config.defaults.list_group,
            'user_context': config.user_context,
            'icon': config.defaults.icon,
            'color': config.defaults.color,
            'working_dir': config.defaults.working_dir
        }

        prompt = PromptTemplate.generate(config_dict, simple=simple)

        logger.info(
            f"Prompt generated for category '{config.category_name}' "
            f"(ID: {config.category_id}), type: {config.defaults.type}"
        )

        return prompt

    def generate_example_json(self, config: BulkImportConfig) -> str:
        """
        Genera un ejemplo de JSON para mostrar al usuario.

        Args:
            config: Configuración del bulk import

        Returns:
            String con JSON de ejemplo formateado
        """
        config_dict = {
            'category_id': config.category_id,
            'category_name': config.category_name,
            'item_type': config.defaults.type,
            'tags': config.defaults.tags,
            'is_favorite': config.defaults.is_favorite,
            'is_sensitive': config.defaults.is_sensitive,
            'is_list': config.defaults.is_list,
            'list_group': config.defaults.list_group
        }

        return PromptTemplate.generate_example_json(config_dict)

    def validate_json(self, json_str: str) -> ValidationResult:
        """
        Valida JSON de import.

        Realiza validación completa:
        - Sintaxis JSON
        - Schema structure
        - Business rules

        Args:
            json_str: String con el JSON a validar

        Returns:
            ValidationResult con resultado de la validación
        """
        result = self.validator.validate_json_string(json_str)

        if result.is_valid:
            logger.info(f"JSON validation passed - {result.items_count} items")
        else:
            logger.warning(f"JSON validation failed - {len(result.errors)} errors")

        return result

    def validate_category_exists(self, category_id: int) -> bool:
        """
        Valida que una categoría existe en BD.

        Args:
            category_id: ID de la categoría

        Returns:
            True si existe, False si no
        """
        return self.validator.validate_category_exists(category_id, self.db)

    def parse_items(
        self,
        json_str: str
    ) -> Tuple[List[BulkItemData], BulkItemDefaults, int]:
        """
        Parsea JSON y retorna lista de items con defaults aplicados.

        Args:
            json_str: String con JSON válido

        Returns:
            Tupla (items_list, defaults, category_id)

        Raises:
            json.JSONDecodeError: Si el JSON es inválido
            KeyError: Si faltan campos requeridos
        """
        data = json.loads(json_str)

        # Parsear defaults
        defaults_dict = data.get('defaults', {})
        defaults = BulkItemDefaults(
            type=defaults_dict.get('type', 'TEXT'),
            tags=defaults_dict.get('tags', ''),
            is_favorite=defaults_dict.get('is_favorite', 0),
            is_sensitive=defaults_dict.get('is_sensitive', 0),
            is_list=defaults_dict.get('is_list', 0),
            list_group=defaults_dict.get('list_group'),
            icon=defaults_dict.get('icon'),
            color=defaults_dict.get('color'),
            description=defaults_dict.get('description'),
            working_dir=defaults_dict.get('working_dir'),
            badge=defaults_dict.get('badge')
        )

        # Parsear items
        items = []
        for item_dict in data['items']:
            item = BulkItemData(
                label=item_dict['label'],
                content=item_dict['content'],
                type=item_dict.get('type', 'TEXT'),
                tags=item_dict.get('tags', ''),
                description=item_dict.get('description'),
                icon=item_dict.get('icon'),
                color=item_dict.get('color'),
                is_favorite=item_dict.get('is_favorite', 0),
                is_sensitive=item_dict.get('is_sensitive', 0),
                is_list=item_dict.get('is_list', 0),
                list_group=item_dict.get('list_group'),
                orden_lista=item_dict.get('orden_lista'),
                working_dir=item_dict.get('working_dir'),
                badge=item_dict.get('badge')
            )

            # Aplicar defaults
            item.merge_defaults(defaults)
            items.append(item)

        category_id = data['category_id']

        logger.info(
            f"Parsed {len(items)} items for category {category_id} "
            f"with defaults: type={defaults.type}, tags='{defaults.tags}', "
            f"is_list={defaults.is_list}, list_group='{defaults.list_group}'"
        )

        return items, defaults, category_id

    def create_items_bulk(
        self,
        items: List[BulkItemData],
        category_id: int
    ) -> BulkCreationResult:
        """
        Crea items masivamente en BD.

        Proceso:
        1. Validar que categoría existe
        2. Filtrar items seleccionados
        3. Insertar en transacción
        4. Actualizar item_count de categoría
        5. Retornar estadísticas

        Args:
            items: Lista de items a crear
            category_id: ID de la categoría destino

        Returns:
            BulkCreationResult con estadísticas y errores
        """
        start_time = time.time()
        result = BulkCreationResult(success=False, category_id=category_id)

        # Validar que categoría existe
        category = self.db.get_category_by_id(category_id)
        if not category:
            result.add_error(f"Categoría {category_id} no existe en la base de datos")
            logger.error(f"Category {category_id} not found")
            return result

        # Filtrar solo items seleccionados
        selected_items = [item for item in items if item.selected]

        if not selected_items:
            result.add_error("No hay items seleccionados para crear")
            logger.warning("No items selected for creation")
            return result

        logger.info(
            f"Starting bulk creation: {len(selected_items)} items "
            f"to category {category_id} ({category['name']})"
        )

        # Inserción en transacción
        try:
            with self.db.transaction() as conn:
                # Si los items son de lista, crear la lista primero en tabla listas
                lista_id = None
                if selected_items and selected_items[0].is_list == 1 and selected_items[0].list_group:
                    list_name = selected_items[0].list_group
                    list_description = f"Lista creada desde IA Bulk Wizard"

                    try:
                        lista_id = self.db.create_lista(
                            category_id=category_id,
                            name=list_name,
                            description=list_description
                        )
                        logger.info(f"Created lista record: id={lista_id}, name='{list_name}'")
                    except ValueError as e:
                        # Si ya existe una lista con ese nombre, intentar obtenerla
                        logger.warning(f"Lista '{list_name}' may already exist: {e}")
                        # Buscar lista existente
                        existing_listas = self.db.get_listas_by_category_new(category_id)
                        for lista in existing_listas:
                            if lista['name'] == list_name:
                                lista_id = lista['id']
                                logger.info(f"Using existing lista: id={lista_id}")
                                break

                        if lista_id is None:
                            # Si no se pudo crear ni encontrar, lanzar error
                            raise ValueError(f"No se pudo crear la lista '{list_name}': {e}")

                # Si los items son de lista, asignar orden secuencial (comenzando desde 1)
                list_order_counter = 1

                for item in selected_items:
                    try:
                        # Convertir tags de string a lista
                        # Ej: "clonar_proyecto" → ["clonar_proyecto"]
                        # Ej: "git,deploy,automation" → ["git", "deploy", "automation"]
                        tags_list = [tag.strip() for tag in item.tags.split(',') if tag.strip()] if item.tags else []

                        # Asignar orden_lista y list_id si es lista
                        orden_lista = None
                        item_list_id = None
                        if item.is_list == 1 and lista_id:
                            item_list_id = lista_id  # Usar lista_id de la nueva arquitectura
                            orden_lista = item.orden_lista if item.orden_lista is not None else list_order_counter
                            list_order_counter += 1

                        # Crear item usando el método del DBManager
                        # IMPORTANTE: Usar nueva arquitectura (list_id) en lugar de legacy (is_list, list_group)
                        item_id = self.db.add_item(
                            category_id=category_id,
                            label=item.label,
                            content=item.content,
                            item_type=item.type,
                            tags=tags_list,
                            description=item.description,
                            icon=item.icon,
                            color=item.color,
                            is_sensitive=item.is_sensitive,
                            is_favorite=item.is_favorite,
                            # Nueva arquitectura v3.1.0
                            list_id=item_list_id,
                            orden_lista=orden_lista,
                            # Legacy (para compatibilidad)
                            is_list=item.is_list,
                            list_group=item.list_group,
                            working_dir=item.working_dir,
                            badge=item.badge
                        )

                        result.created_count += 1

                        logger.debug(
                            f"Created item {item_id}: '{item.label}' "
                            f"(type: {item.type}, sensitive: {item.is_sensitive}, "
                            f"list_id: {item_list_id}, orden: {orden_lista})"
                        )

                    except Exception as e:
                        error_msg = f"Error creando '{item.label}': {str(e)}"
                        result.add_error(error_msg)
                        logger.error(f"Failed to create item '{item.label}': {e}", exc_info=True)

                # Actualizar item_count de categoría
                try:
                    self.db.update_category_item_count(category_id)
                except Exception as e:
                    logger.error(f"Failed to update category item_count: {e}")
                    # No es crítico, continuar

            # Si se creó al menos un item, es exitoso
            result.success = result.created_count > 0

            # Calcular duración
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms

            logger.info(
                f"Bulk creation completed: {result.created_count} created, "
                f"{result.failed_count} failed in {duration_ms}ms"
            )

        except Exception as e:
            error_msg = f"Error en transacción de base de datos: {str(e)}"
            result.add_error(error_msg)
            logger.error(f"Transaction failed: {e}", exc_info=True)

        return result

    def get_statistics(self, items: List[BulkItemData]) -> Dict[str, Any]:
        """
        Genera estadísticas sobre los items a importar.

        Args:
            items: Lista de items

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            'total_items': len(items),
            'selected_items': sum(1 for item in items if item.selected),
            'by_type': {
                'TEXT': 0,
                'URL': 0,
                'CODE': 0,
                'PATH': 0
            },
            'favorites': sum(1 for item in items if item.is_favorite),
            'sensitive': sum(1 for item in items if item.is_sensitive),
            'with_description': sum(1 for item in items if item.description),
            'with_tags': sum(1 for item in items if item.tags),
            'with_icon': sum(1 for item in items if item.icon),
            'with_color': sum(1 for item in items if item.color)
        }

        # Contar por tipo
        for item in items:
            if item.type in stats['by_type']:
                stats['by_type'][item.type] += 1

        return stats

    def get_tips_for_type(self, item_type: str) -> str:
        """
        Retorna tips para un tipo de item específico.

        Args:
            item_type: Tipo de item (TEXT, URL, CODE, PATH)

        Returns:
            String con tips
        """
        return PromptTemplate.get_tips_for_type(item_type)
