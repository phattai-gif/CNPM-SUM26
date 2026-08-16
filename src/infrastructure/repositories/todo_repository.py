"""Todo Repository - Legacy module (not used in app schema)."""

from domain.models.itodo_repository import ITodoRepository
from domain.models.todo import Todo
from typing import List, Optional
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config
from sqlalchemy import Column, Integer, String, DateTime
from infrastructure.databases import Base
from sqlalchemy.orm import Session
from infrastructure.databases.factory_database import FactoryDatabase as db_factory

load_dotenv()


class TodoRepository(ITodoRepository):
    """Legacy todo repository - not actively used.
    
    Todo is not part of the new app schema (20 tables).
    This class is kept for backward compatibility only.
    """
    
    def __init__(self, session: Session = None):
        self._todos = []
        self._id_counter = 1
        try:
            self.session = session or db_factory.get_database('POSTGREE').session
        except Exception:
            self.session = None

    def add(self, todo: Todo):
        """Legacy method - not implemented for new schema."""
        raise NotImplementedError("Todo model not in app schema")

    def get_by_id(self, todo_id: int) -> Optional[Todo]:
        """Legacy method - not implemented for new schema."""
        raise NotImplementedError("Todo model not in app schema")


    # def list(self) -> List[Todo]:
    #     self._todos
    #     return self._todos
    def list(self) -> List[TodoModel]:
        self._todos = session.query(TodoModel).all()
        # select * from todos
        return self._todos


    def update(self, todo: TodoModel) -> TodoModel:
        try:
             #Manual mapping from Todo to TodoModel
            todo = TodoModel(
                id = todo.id,
                title=todo.title,
                description=todo.description,
                status=todo.status,
                created_at=todo.created_at,
                updated_at=todo.updated_at
            )
            self.session.merge(todo)
            self.session.commit()
            return todo
        except Exception as e:
            self.session.rollback()
            raise ValueError('Todo not found')
        finally:
            self.session.close()

    def delete(self, todo_id: int) -> None:
        # self._todos = [t for t in self._todos if t.id != todo_id] 
        try:
            todo = self.session.query(TodoModel).filter_by(id=todo_id).first()
            if todo:
                self.session.delete(todo)
                self.session.commit()
            else:
                raise ValueError('Todo not found')
        except Exception as e:
            self.session.rollback()
            raise ValueError('Todo not found')
        finally:
            self.session.close()

