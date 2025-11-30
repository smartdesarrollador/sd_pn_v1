"""
Lista Model
Modelo para listas de items (nueva arquitectura v3.1.0)
"""
from typing import Dict, Any, Optional, List
from datetime import datetime


class Lista:
    """
    Model representing a lista (list of items)

    Una lista es un agrupamiento de items que se ejecutan/copian secuencialmente.
    Esta clase reemplaza el sistema anterior basado en is_list/list_group.
    """

    def __init__(
        self,
        lista_id: int,
        category_id: int,
        name: str,
        description: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        last_used: Optional[str] = None,
        use_count: int = 0
    ):
        """
        Initialize Lista

        Args:
            lista_id: ID único de la lista
            category_id: ID de la categoría a la que pertenece
            name: Nombre de la lista (único por categoría)
            description: Descripción opcional de la lista
            created_at: Timestamp de creación
            updated_at: Timestamp de última actualización
            last_used: Timestamp de último uso
            use_count: Contador de usos
        """
        self.id = lista_id
        self.category_id = category_id
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.last_used = last_used
        self.use_count = use_count

        # Campos calculados (no persistidos en BD)
        self.item_count: int = 0  # Número de items en la lista
        self.items: List[Any] = []  # Items de la lista (cargados bajo demanda)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now().isoformat()

    def increment_use_count(self) -> None:
        """Increment use count and update last_used timestamp"""
        self.use_count += 1
        self.last_used = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert lista to dictionary

        Returns:
            Dict with all lista fields
        """
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "item_count": self.item_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Lista':
        """
        Create a Lista from a dictionary

        Args:
            data: Dictionary with lista data (from DB or JSON)

        Returns:
            Lista instance
        """
        lista = cls(
            lista_id=data.get("id"),
            category_id=data.get("category_id"),
            name=data.get("name", ""),
            description=data.get("description"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_used=data.get("last_used"),
            use_count=data.get("use_count", 0)
        )

        # Set calculated fields if present
        if "item_count" in data:
            lista.item_count = data["item_count"]

        return lista

    def has_items(self) -> bool:
        """Check if lista has items"""
        return self.item_count > 0

    def is_used(self) -> bool:
        """Check if lista has been used at least once"""
        return self.use_count > 0

    def get_formatted_use_count(self) -> str:
        """
        Get formatted use count for display

        Returns:
            Formatted string like "Used 5 times" or "Never used"
        """
        if self.use_count == 0:
            return "Never used"
        elif self.use_count == 1:
            return "Used 1 time"
        else:
            return f"Used {self.use_count} times"

    def get_formatted_last_used(self) -> str:
        """
        Get formatted last used timestamp for display

        Returns:
            Formatted string like "Last used: 2025-11-29 13:40" or "Never used"
        """
        if not self.last_used:
            return "Never used"

        try:
            dt = datetime.fromisoformat(self.last_used)
            return f"Last used: {dt.strftime('%Y-%m-%d %H:%M')}"
        except:
            return "Last used: Unknown"

    def __repr__(self) -> str:
        return f"Lista(id={self.id}, name='{self.name}', category={self.category_id}, items={self.item_count})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Lista):
            return False
        return self.id == other.id and self.category_id == other.category_id

    def __hash__(self) -> int:
        return hash((self.id, self.category_id))
