from typing import Dict, List, Optional


class AreaDataManager:
    def __init__(self, db_manager=None):
        self.db = db_manager

    def get_area_full_data(self, area_id: int) -> Optional[Dict]:
        if not self.db:
            return self._get_mock_area_data(area_id)

        return self._get_real_area_data(area_id)

    def _get_mock_area_data(self, area_id: int) -> Dict:
        return {
            'area_id': area_id,
            'area_name': 'Area Test',
            'area_icon': '🏢',
            'tags': [],
            'unclassified_elements': [],
            'ungrouped_items': []
        }

    def _get_real_area_data(self, area_id: int) -> Optional[Dict]:
        try:
            area = self.db.get_area(area_id)
            if not area:
                return None

            conn = self.db.connect()
            cursor = conn.execute("""
                SELECT DISTINCT aet.id, aet.name, aet.color
                FROM area_element_tag_associations ata
                JOIN area_element_tags aet ON ata.tag_id = aet.id
                JOIN area_relations ar ON ata.area_relation_id = ar.id
                LEFT JOIN area_tag_orders ato ON ato.area_id = ar.area_id AND ato.tag_id = aet.id
                WHERE ar.area_id = ?
                ORDER BY COALESCE(ato.order_index, 999999), aet.name ASC
            """, (area_id,))
            area_tags = [dict(row) for row in cursor.fetchall()]

            tags_data = []

            for area_tag in area_tags:
                tag_id = area_tag['id']
                tag_name = area_tag['name']
                tag_color = area_tag.get('color', '#808080')

                all_relations = self.db.get_area_relations(area_id)
                tag_relations = self._get_relations_for_tag(tag_id, all_relations)

                # Aplicar orden filtrado si existe para este tag
                tag_relations = self._apply_filtered_order(area_id, tag_id, tag_relations)

                groups_data = []

                # Procesar relaciones en el orden correcto (después de aplicar filtrado)
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

                if groups_data:
                    tags_data.append({
                        'tag_name': tag_name,
                        'tag_color': tag_color,
                        'groups': groups_data
                    })

            unclassified_items = self._get_unclassified_elements(area_id)
            ungrouped_items = self._get_ungrouped_items(area_id, tags_data, unclassified_items)

            return {
                'area_id': area_id,
                'area_name': area.get('name', 'Área sin nombre'),
                'area_icon': area.get('icon', '🏢'),
                'tags': tags_data,
                'unclassified_elements': unclassified_items,
                'ungrouped_items': ungrouped_items
            }

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo datos reales del área {area_id}: {e}")
            return self._get_mock_area_data(area_id)

    def _get_relations_for_tag(self, tag_id: int, all_relations: List[Dict]) -> List[Dict]:
        try:
            conn = self.db.connect()
            cursor = conn.execute("""
                SELECT area_relation_id
                FROM area_element_tag_associations
                WHERE tag_id = ?
            """, (tag_id,))
            relation_ids = [row['area_relation_id'] for row in cursor.fetchall()]
            return [rel for rel in all_relations if rel['id'] in relation_ids]
        except:
            return []

    def _apply_filtered_order(self, area_id: int, filter_tag_id: int,
                              tag_relations: List[Dict]) -> List[Dict]:
        """
        Aplica el orden filtrado a las relaciones de un tag si existe

        Args:
            area_id: ID del área
            filter_tag_id: ID del tag de área
            tag_relations: Lista de relaciones del tag

        Returns:
            Lista de relaciones ordenadas según orden filtrado o global
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.debug(f"Aplicando orden filtrado para área {area_id}, tag {filter_tag_id}")
            logger.debug(f"Número de relaciones: {len(tag_relations)}")

            # Obtener orden filtrado para este tag
            filtered_orders = self.db.get_area_filtered_order(area_id, filter_tag_id)

            logger.debug(f"Órdenes filtrados encontrados: {len(filtered_orders)}")
            if filtered_orders:
                logger.debug(f"Órdenes: {filtered_orders}")

            if not filtered_orders:
                # No hay orden personalizado, usar orden global
                logger.debug("No hay orden personalizado, usando orden global")
                return sorted(tag_relations, key=lambda x: x.get('order_index', 0))

            # Separar relaciones con orden personalizado de las que no
            ordered_relations = []
            unordered_relations = []

            for rel in tag_relations:
                element_type = 'relation'  # Las relaciones siempre son tipo 'relation'
                element_id = rel['id']
                key = (element_type, element_id)

                logger.debug(f"Procesando relación {element_id}, buscando key {key}")

                if key in filtered_orders:
                    order_idx = filtered_orders[key]
                    ordered_relations.append((order_idx, rel))
                    logger.debug(f"  -> Encontrado en filtered_orders con orden {order_idx}")
                else:
                    unordered_relations.append(rel)
                    logger.debug(f"  -> No encontrado, usando orden global {rel.get('order_index', 0)}")

            # Ordenar relaciones por order_index filtrado
            ordered_relations.sort(key=lambda x: x[0])
            result = [rel for _, rel in ordered_relations]

            # Agregar relaciones sin orden al final (usando su orden global)
            unordered_relations.sort(key=lambda x: x.get('order_index', 0))
            result.extend(unordered_relations)

            logger.debug(f"Resultado final: {len(result)} relaciones")
            for idx, rel in enumerate(result):
                logger.debug(f"  {idx}: relation_id={rel['id']}, entity_type={rel.get('entity_type')}")

            return result

        except Exception as e:
            logger.error(f"Error aplicando orden filtrado en área: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # En caso de error, usar orden global
            return sorted(tag_relations, key=lambda x: x.get('order_index', 0))

    def _get_category_name(self, category_id: int) -> str:
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Categoría {category_id}'
        except:
            return f'Categoría {category_id}'

    def _get_item_tag_name(self, tag_id: int) -> str:
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Tag {tag_id}'
        except:
            return f'Tag {tag_id}'

    def _get_table_name(self, table_id: int) -> str:
        try:
            conn = self.db.connect()
            cursor = conn.execute("SELECT name FROM custom_tables WHERE id = ?", (table_id,))
            row = cursor.fetchone()
            return row['name'] if row else f'Tabla {table_id}'
        except:
            return f'Tabla {table_id}'

    def _format_items(self, items: List[Dict]) -> List[Dict]:
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

    def _get_unclassified_elements(self, area_id: int) -> List[Dict]:
        try:
            conn = self.db.connect()

            cursor = conn.execute("""
                SELECT ar.*
                FROM area_relations ar
                LEFT JOIN area_element_tag_associations ata ON ar.id = ata.area_relation_id
                WHERE ar.area_id = ? AND ata.id IS NULL
            """, (area_id,))

            unclassified_relations = cursor.fetchall()
            unclassified_elements = []

            for rel in unclassified_relations:
                rel_dict = dict(rel)
                entity_type = rel_dict['entity_type']
                entity_id = rel_dict['entity_id']

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
                    items = []
                else:
                    continue

                if items or entity_type == 'process':
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

    def _get_ungrouped_items(self, area_id: int, tags_data: List[Dict], unclassified_elements: List[Dict] = None) -> List[Dict]:
        grouped_item_ids = set()
        for tag in tags_data:
            for group in tag.get('groups', []):
                for item in group.get('items', []):
                    grouped_item_ids.add(item['id'])

        all_relations = self.db.get_area_relations(area_id)
        all_area_items = []

        category_relations = [r for r in all_relations if r['entity_type'] == 'category']
        for rel in category_relations:
            items = self.db.get_items_by_category(rel['entity_id'])
            all_area_items.extend(items)

        list_relations = [r for r in all_relations if r['entity_type'] == 'list']
        for rel in list_relations:
            items = self.db.get_items_by_lista(rel['entity_id'])
            all_area_items.extend(items)

        ungrouped = []
        seen_ids = set()

        for item in all_area_items:
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

    def filter_by_area_tags(
        self,
        area_data: Dict,
        tag_filters: List[str],
        match_mode: str = 'OR'
    ) -> Dict:
        if not tag_filters:
            return area_data

        filtered_data = area_data.copy()
        filtered_data['tags'] = []

        for tag_data in area_data['tags']:
            if tag_data['tag_name'] in tag_filters:
                filtered_data['tags'].append(tag_data)

        if match_mode == 'AND' and len(filtered_data['tags']) != len(tag_filters):
            filtered_data['tags'] = []

        return filtered_data

    def get_total_items_count(self, area_data: Dict) -> int:
        total = 0
        for tag in area_data.get('tags', []):
            for group in tag.get('groups', []):
                total += len(group.get('items', []))
        total += len(area_data.get('ungrouped_items', []))
        return total

    def get_tags_summary(self, area_data: Dict) -> List[Dict]:
        summary = []
        for tag in area_data.get('tags', []):
            item_count = 0
            for group in tag.get('groups', []):
                item_count += len(group.get('items', []))

            summary.append({
                'name': tag['tag_name'],
                'color': tag['tag_color'],
                'count': item_count
            })
        return summary
