import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category


class CategoryLoader:
    """
    Load categories from json to DB.
    """

    def __init__(self, session: Session):
        self.db = session
        self.config_path = settings.TOPICS_PATH

    def load(self) -> int:
        """
        Realize loading and return number of categories.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        count = 0
        for cat_data in config.get("categories", []):
            existing = self.db.query(Category).filter_by(
                slug=cat_data["slug"]
            ).first()

            if existing:
                existing.name = cat_data["name"]
                existing.description = cat_data.get("description")
            else:
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data.get("description"),
                )
                self.db.add(category)
                count += 1

        self.db.commit()
        return count
    