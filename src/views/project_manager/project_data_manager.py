"""
Gestor de datos para vista completa de proyecto

Obtiene y agrupa datos de proyectos desde la base de datos
para visualización en vista completa.

Autor: Widget Sidebar Team
Versión: 1.0
"""

from typing import Dict, List, Optional


class ProjectDataManager:
    """
    Gestor de datos para vista completa de proyecto

    Se encarga de:
    - Obtener datos del proyecto desde BD
    - Agrupar items por tags de proyecto
    - Agrupar items por categorías, listas y tags de items
    - Filtrar datos según criterios

    NOTA: Por ahora usa datos mock para testing.
    En futuras fases se integrará con DBManager real.
    """

    def __init__(self, db_manager=None):
        """
        Inicializar gestor de datos

        Args:
            db_manager: Instancia de DBManager (opcional por ahora)
        """
        self.db = db_manager

    def get_project_full_data(self, project_id: int) -> Optional[Dict]:
        """
        Obtener datos completos del proyecto agrupados por tags

        Args:
            project_id: ID del proyecto

        Returns:
            Diccionario con estructura:
            {
                'project_id': int,
                'project_name': str,
                'project_icon': str,
                'tags': [
                    {
                        'tag_name': str,
                        'tag_color': str,
                        'groups': [
                            {
                                'type': 'category' | 'list' | 'tag',
                                'name': str,
                                'items': [...]
                            }
                        ]
                    }
                ],
                'ungrouped_items': [...]
            }
        """
        # Si no hay DBManager, usar datos mock
        if not self.db:
            return self._get_mock_project_data(project_id)

        # Obtener datos reales de la BD
        return self._get_real_project_data(project_id)

    def _get_mock_project_data(self, project_id: int) -> Dict:
        """
        Obtener datos mock para testing

        Args:
            project_id: ID del proyecto

        Returns:
            Datos mock del proyecto
        """
        return {
            'project_id': project_id,
            'project_name': 'proy_test_3',
            'project_icon': '📁',
            'tags': [
                {
                    'tag_name': 'git',
                    'tag_color': '#32CD32',
                    'groups': [
                        {
                            'type': 'category',
                            'name': 'CONFIG',
                            'items': [
                                {
                                    'id': 1,
                                    'label': 'Inicializar repositorio',
                                    'content': '$ git init\n$ git clone <url_del_repositorio>',
                                    'type': 'CODE',
                                    'description': 'Comandos para iniciar un nuevo repositorio'
                                },
                                {
                                    'id': 2,
                                    'label': 'Configurar usuario',
                                    'content': '$ git config --global user.name "Tu Nombre"\n$ git config --global user.email "tu@email.com"',
                                    'type': 'CODE',
                                    'description': 'Configuración de identidad'
                                }
                            ]
                        },
                        {
                            'type': 'category',
                            'name': 'COMMITS',
                            'items': [
                                {
                                    'id': 3,
                                    'label': 'Crear commit',
                                    'content': '$ git add .\n$ git commit -m "mensaje del commit"\n$ git push origin main',
                                    'type': 'CODE',
                                    'description': 'Flujo básico de commits'
                                }
                            ]
                        }
                    ]
                },
                {
                    'tag_name': 'backend',
                    'tag_color': '#FF6B6B',
                    'groups': [
                        {
                            'type': 'list',
                            'name': 'APIs REST',
                            'items': [
                                {
                                    'id': 4,
                                    'label': 'Documentación de FastAPI',
                                    'content': 'https://fastapi.tiangolo.com/',
                                    'type': 'URL',
                                    'description': 'Framework web moderno y rápido para Python'
                                },
                                {
                                    'id': 5,
                                    'label': 'Endpoint de autenticación',
                                    'content': 'Este endpoint maneja el login de usuarios mediante JWT tokens. Requiere email y password en el body de la petición POST. Retorna un token de acceso válido por 24 horas y un refresh token válido por 7 días.',
                                    'type': 'TEXT',
                                    'description': 'Descripción del endpoint /api/auth/login'
                                }
                            ]
                        },
                        {
                            'type': 'category',
                            'name': 'Database',
                            'items': [
                                {
                                    'id': 6,
                                    'label': 'Carpeta de migraciones',
                                    'content': 'C:\\Users\\ASUS\\Desktop\\proyectos_python\\widget_sidebar\\src\\database\\migrations',
                                    'type': 'PATH',
                                    'description': 'Directorio con migraciones de BD'
                                }
                            ]
                        }
                    ]
                },
                {
                    'tag_name': 'docs',
                    'tag_color': '#FFD700',
                    'groups': [
                        {
                            'type': 'tag',
                            'name': 'python',
                            'items': [
                                {
                                    'id': 7,
                                    'label': 'Guía de estilos PEP 8',
                                    'content': 'https://peps.python.org/pep-0008/',
                                    'type': 'URL',
                                    'description': 'Convenciones de código Python'
                                },
                                {
                                    'id': 8,
                                    'label': 'Introducción a Python',
                                    'content': '''Python es un lenguaje de programación de alto nivel, interpretado y de propósito general. Su filosofía de diseño enfatiza la legibilidad del código con el uso de indentación significativa. Python es dinámicamente tipado y cuenta con recolección de basura automática. Soporta múltiples paradigmas de programación, incluyendo programación estructurada, orientada a objetos y funcional.

Las características principales de Python incluyen:
- Sintaxis clara y legible
- Biblioteca estándar extensa
- Gran comunidad y ecosistema de paquetes
- Multiplataforma (Windows, macOS, Linux)
- Ideal para desarrollo web, ciencia de datos, automatización, IA y más

Python fue creado por Guido van Rossum y lanzado por primera vez en 1991. El nombre del lenguaje viene de Monty Python, no de la serpiente pitón como muchos creen.''',
                                    'type': 'TEXT',
                                    'description': 'Resumen sobre el lenguaje Python (texto extenso con >800 chars)'
                                }
                            ]
                        }
                    ]
                }
            ],
            'ungrouped_items': [
                {
                    'id': 9,
                    'label': 'Nota miscelánea',
                    'content': 'Este es un item que no pertenece a ningún tag de proyecto específico.',
                    'type': 'TEXT',
                    'description': 'Item sin tag de proyecto'
                }
            ]
        }

    def _get_real_project_data(self, project_id: int) -> Optional[Dict]:
        """
        Obtener datos reales del proyecto desde la base de datos

        Args:
            project_id: ID del proyecto

        Returns:
            Diccionario con estructura de datos del proyecto o None si no existe
        """
        try:
            # 1. Obtener información básica del proyecto
            project = self.db.get_project(project_id)
            if not project:
                return None

            # 2. Obtener TODOS los tags que tienen elementos asociados al proyecto
            # Ordenados según project_tag_orders (respetando el orden del usuario)
            conn = self.db.connect()
            cursor = conn.execute("""
                SELECT DISTINCT pet.id, pet.name, pet.color
                FROM project_element_tag_associations ta
                JOIN project_element_tags pet ON ta.tag_id = pet.id
                JOIN project_relations pr ON ta.project_relation_id = pr.id
                LEFT JOIN project_tag_orders pto ON pto.project_id = pr.project_id AND pto.tag_id = pet.id
                WHERE pr.project_id = ?
                ORDER BY COALESCE(pto.order_index, 999999), pet.name ASC
            """, (project_id,))
            project_tags = [dict(row) for row in cursor.fetchall()]

            # 3. Construir estructura de tags con sus grupos
            tags_data = []

            for project_tag in project_tags:
                tag_id = project_tag['id']
                tag_name = project_tag['name']
                tag_color = project_tag.get('color', '#808080')

                # Obtener todas las relaciones del proyecto
                all_relations = self.db.get_project_relations(project_id)

                # Filtrar relaciones que están asociadas a este tag
                # (basado en la tabla project_element_tag_associations)
                tag_relations = self._get_relations_for_tag(tag_id, all_relations)

                # Aplicar orden filtrado si existe para este tag
                tag_relations = self._apply_filtered_order(project_id, tag_id, tag_relations)

                # Procesar relaciones en el orden correcto (después de aplicar filtrado)
                groups_data = []

                for rel in tag_relations:
                    entity_type = rel['entity_type']
                    entity_id = rel['entity_id']

                    if entity_type == 'category':
                        items = self.db.get_items_by_category(entity_id)
                        if items:
                            category_name = self._get_category_name(entity_id)
                            groups_data.append({
                                'type': 'category',
                                'name': category_name,
                                'items': self._format_items(items)
                            })

                    elif entity_type == 'list':
                        items = self.db.get_items_by_lista(entity_id)
                        if items:
                            list_name = items[0].get('lista_name', 'Lista sin nombre') if items else 'Lista'
                            groups_data.append({
                                'type': 'list',
                                'name': list_name,
                                'items': self._format_items(items)
                            })

                    elif entity_type == 'tag':
                        items = self.db.get_items_by_tag_id(entity_id)
                        if items:
                            tag_name_item = self._get_item_tag_name(entity_id)
                            groups_data.append({
                                'type': 'tag',
                                'name': tag_name_item,
                                'items': self._format_items(items)
                            })

                    elif entity_type == 'table':
                        items = self.db.get_items_by_table(entity_id)
                        if items:
                            table_name = self._get_table_name(entity_id)
                            groups_data.append({
                                'type': 'table',
                                'name': table_name,
                                'items': self._format_items(items)
                            })

                    elif entity_type == 'item':
                        item = self.db.get_item(entity_id)
                        if item:
                            groups_data.append({
                                'type': 'item',
                                'name': item.get('label', 'Item sin nombre'),
                                'items': self._format_items([item])
                            })

                    elif entity_type == 'process':
                        process = self.db.get_process(entity_id)
                        if process:
                            groups_data.append({
                                'type': 'process',
                                'name': process.get('name', 'Proceso sin nombre'),
                                'items': []
                            })

                # Solo agregar el tag si tiene grupos con items
                if groups_data:
                    tags_data.append({
                        'tag_name': tag_name,
                        'tag_color': tag_color,
                        'groups': groups_data
                    })

            # 4. Obtener elementos sin tag de proyecto (elementos "Sin clasificar")
            unclassified_items = self._get_unclassified_elements(project_id)

            # 5. Obtener items sin agrupar (items que no están en ningún elemento)
            ungrouped_items = self._get_ungrouped_items(project_id, tags_data, unclassified_items)

            # 6. Construir y retornar estructura final
            return {
                'project_id': project_id,
                'project_name': project.get('name', 'Proyecto sin nombre'),
                'project_icon': project.get('icon', '📁'),
                'tags': tags_data,
                'unclassified_elements': unclassified_items,
                'ungrouped_items': ungrouped_items
            }

        except Exception as e:
            # Log del error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo datos reales del proyecto {project_id}: {e}")
            # Retornar datos mock en caso de error
            return self._get_mock_project_data(project_id)

    def _get_relations_for_tag(self, tag_id: int, all_relations: List[Dict]) -> List[Dict]:
        """
        Obtiene las relaciones asociadas a un tag específico del proyecto

        Args:
            tag_id: ID del tag de proyecto
            all_relations: Lista de todas las relaciones del proyecto

        Returns:
            Lista de relaciones asociadas al tag
        """
        # Obtener asociaciones del tag con relaciones
        tag_associations = self.db.get_project_relations_by_tag(tag_id)

        # Extraer IDs de relaciones
        relation_ids = [assoc['id'] for assoc in tag_associations]

        # Filtrar relaciones
        return [rel for rel in all_relations if rel['id'] in relation_ids]

    def _apply_filtered_order(self, project_id: int, filter_tag_id: int,
                              tag_relations: List[Dict]) -> List[Dict]:
        """
        Aplica el orden filtrado a las relaciones de un tag si existe

        Args:
            project_id: ID del proyecto
            filter_tag_id: ID del tag de proyecto
            tag_relations: Lista de relaciones del tag

        Returns:
            Lista de relaciones ordenadas según orden filtrado o global
        """
        try:
            # Obtener orden filtrado para este tag
            filtered_orders = self.db.get_filtered_order(project_id, filter_tag_id)

            if not filtered_orders:
                # No hay orden personalizado, usar orden global
                return sorted(tag_relations, key=lambda x: x.get('order_index', 0))

            # Separar relaciones con orden personalizado de las que no
            ordered_relations = []
            unordered_relations = []

            for rel in tag_relations:
                element_type = 'relation'  # Las relaciones siempre son tipo 'relation'
                element_id = rel['id']
                key = (element_type, element_id)

                if key in filtered_orders:
                    ordered_relations.append((filtered_orders[key], rel))
                else:
                    unordered_relations.append(rel)

            # Ordenar relaciones por order_index filtrado
            ordered_relations.sort(key=lambda x: x[0])
            result = [rel for _, rel in ordered_relations]

            # Agregar relaciones sin orden al final (usando su orden global)
            unordered_relations.sort(key=lambda x: x.get('order_index', 0))
            result.extend(unordered_relations)

            return result

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error aplicando orden filtrado: {e}")
            # En caso de error, usar orden global
            return sorted(tag_relations, key=lambda x: x.get('order_index', 0))

    def _get_category_name(self, category_id: int) -> str:
        """
        Obtiene el nombre de una categoría

        Args:
            category_id: ID de la categoría

        Returns:
            Nombre de la categoría
        """
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Categoría {category_id}'
        except:
            return f'Categoría {category_id}'

    def _get_item_tag_name(self, tag_id: int) -> str:
        """
        Obtiene el nombre de un tag de item

        Args:
            tag_id: ID del tag

        Returns:
            Nombre del tag
        """
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Tag {tag_id}'
        except:
            return f'Tag {tag_id}'

    def _get_table_name(self, table_id: int) -> str:
        """
        Obtiene el nombre de una tabla

        Args:
            table_id: ID de la tabla

        Returns:
            Nombre de la tabla
        """
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM custom_tables WHERE id = ?", (table_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Tabla {table_id}'
        except:
            return f'Tabla {table_id}'

    def _format_items(self, items: List[Dict]) -> List[Dict]:
        """
        Formatea items para la vista completa

        Args:
            items: Lista de items de la BD

        Returns:
            Lista de items formateados
        """
        formatted_items = []

        for item in items:
            formatted_items.append({
                'id': item.get('id'),
                'label': item.get('label', 'Item sin nombre'),
                'content': item.get('content', ''),
                'type': item.get('type', 'TEXT'),
                'description': item.get('description', '')
            })

        return formatted_items

    def _get_unclassified_elements(self, project_id: int) -> List[Dict]:
        """
        Obtiene elementos del proyecto que NO tienen tag de proyecto asociado

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de elementos sin clasificar con sus items
        """
        try:
            conn = self.db.connect()

            # Obtener relaciones sin tag de proyecto
            cursor = conn.execute("""
                SELECT pr.*
                FROM project_relations pr
                LEFT JOIN project_element_tag_associations ta ON pr.id = ta.project_relation_id
                WHERE pr.project_id = ? AND ta.id IS NULL
            """, (project_id,))

            unclassified_relations = cursor.fetchall()

            unclassified_elements = []

            for rel in unclassified_relations:
                rel_dict = dict(rel)
                entity_type = rel_dict['entity_type']
                entity_id = rel_dict['entity_id']

                # Obtener nombre y items según el tipo
                if entity_type == 'category':
                    name = self._get_category_name(entity_id)
                    items = self.db.get_items_by_category(entity_id)
                elif entity_type == 'list':
                    cursor2 = conn.execute("SELECT name FROM listas WHERE id = ?", (entity_id,))
                    row = cursor2.fetchone()
                    name = row['name'] if row else f'Lista {entity_id}'
                    items = self.db.get_items_by_lista(entity_id)
                elif entity_type == 'tag':
                    name = self._get_item_tag_name(entity_id)
                    items = self.db.get_items_by_tag_id(entity_id)
                elif entity_type == 'table':
                    name = self._get_table_name(entity_id)
                    items = self.db.get_items_by_table(entity_id)
                elif entity_type == 'item':
                    item = self.db.get_item(entity_id)
                    name = item.get('label', 'Item sin nombre') if item else f'Item {entity_id}'
                    items = [item] if item else []
                elif entity_type == 'process':
                    process = self.db.get_process(entity_id)
                    name = process.get('name', 'Proceso sin nombre') if process else f'Proceso {entity_id}'
                    items = []  # Los procesos no tienen items
                else:
                    continue

                if items or entity_type == 'process':  # Agregar si tiene items o es proceso
                    unclassified_elements.append({
                        'type': entity_type,
                        'name': name,
                        'items': self._format_items(items) if items else []
                    })

            return unclassified_elements

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo elementos sin clasificar: {e}")
            return []

    def _get_ungrouped_items(self, project_id: int, tags_data: List[Dict], unclassified_elements: List[Dict] = None) -> List[Dict]:
        """
        Obtiene items del proyecto que no están bajo ningún tag

        Args:
            project_id: ID del proyecto
            tags_data: Datos de tags ya procesados

        Returns:
            Lista de items sin agrupar
        """
        # Obtener todos los IDs de items que ya están en tags
        grouped_item_ids = set()
        for tag in tags_data:
            for group in tag.get('groups', []):
                for item in group.get('items', []):
                    grouped_item_ids.add(item['id'])

        # Obtener todas las relaciones del proyecto
        all_relations = self.db.get_project_relations(project_id)

        # Obtener todos los items del proyecto
        all_project_items = []

        # Items de categorías del proyecto
        category_relations = [r for r in all_relations if r['entity_type'] == 'category']
        for rel in category_relations:
            items = self.db.get_items_by_category(rel['entity_id'])
            all_project_items.extend(items)

        # Items de listas del proyecto
        list_relations = [r for r in all_relations if r['entity_type'] == 'list']
        for rel in list_relations:
            items = self.db.get_items_by_lista(rel['entity_id'])
            all_project_items.extend(items)

        # Filtrar items que no están en grouped_item_ids
        ungrouped = []
        seen_ids = set()

        for item in all_project_items:
            item_id = item.get('id')
            if item_id not in grouped_item_ids and item_id not in seen_ids:
                seen_ids.add(item_id)
                ungrouped.append({
                    'id': item_id,
                    'label': item.get('label', 'Item sin nombre'),
                    'content': item.get('content', ''),
                    'type': item.get('type', 'TEXT'),
                    'description': item.get('description', '')
                })

        return ungrouped

    def filter_by_project_tags(
        self,
        project_data: Dict,
        tag_filters: List[str],
        match_mode: str = 'OR'
    ) -> Dict:
        """
        Filtrar datos del proyecto por tags

        Args:
            project_data: Datos del proyecto completo
            tag_filters: Lista de nombres de tags para filtrar
            match_mode: 'AND' o 'OR' para coincidencia de tags

        Returns:
            Datos del proyecto filtrados
        """
        if not tag_filters:
            return project_data

        filtered_data = project_data.copy()
        filtered_data['tags'] = []

        # Filtrar tags
        for tag_data in project_data['tags']:
            if tag_data['tag_name'] in tag_filters:
                filtered_data['tags'].append(tag_data)

        # Si es modo AND, verificar que tenga todos los tags
        if match_mode == 'AND' and len(filtered_data['tags']) != len(tag_filters):
            filtered_data['tags'] = []

        return filtered_data

    def get_total_items_count(self, project_data: Dict) -> int:
        """
        Obtener cantidad total de items en el proyecto

        Args:
            project_data: Datos del proyecto

        Returns:
            Número total de items
        """
        total = 0

        # Contar items en tags
        for tag in project_data.get('tags', []):
            for group in tag.get('groups', []):
                total += len(group.get('items', []))

        # Contar items sin agrupar
        total += len(project_data.get('ungrouped_items', []))

        return total

    def get_tags_summary(self, project_data: Dict) -> List[Dict]:
        """
        Obtener resumen de tags con conteos

        Args:
            project_data: Datos del proyecto

        Returns:
            Lista de diccionarios con nombre, color y conteo de cada tag
        """
        summary = []

        for tag in project_data.get('tags', []):
            item_count = 0
            for group in tag.get('groups', []):
                item_count += len(group.get('items', []))

            summary.append({
                'name': tag['tag_name'],
                'color': tag['tag_color'],
                'count': item_count
            })

        return summary
