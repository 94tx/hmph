from __future__ import annotations

from abc import ABC
from collections import defaultdict
from dataclasses import fields
from functools import partial
from typing import Optional, Union, Callable, Any, TypeVar, Type

from .protocols import SupportsCursor

NormalType: type = Optional[Union[str, bytes, int, float]]
mapping_dict = partial(defaultdict, lambda: lambda x: x)

serializers: dict[str, Callable[[Any], NormalType]] = mapping_dict()
deserializers: dict[str, Callable[[NormalType], Any]] = mapping_dict()

def add_type(t: str, serializer: Callable[[Any], NormalType], deserializer: Callable[[NormalType], Any]):
    serializers[t] = serializer
    deserializers[t] = deserializer

def serialize_value(v: Any) -> NormalType:
    if v is None:
        return None
    return serializers[type(v).__name__](v)

def deserialize_value(v: NormalType, t: str) -> Any:
    if v is None:
        return None
    return deserializers[t](v)

T: type = TypeVar("T", bound="Model")
class Model(ABC):
    class Meta:
        table_name: Optional[str] = None
        primary_key: str = 'id'

    def serialize(self: T) -> tuple:
        return tuple(map(lambda f: serialize_value(getattr(self, f.name)), fields(self)))

    @classmethod
    def deserialize(cls: Type[T], value: Optional[dict[str, Any]]) -> Optional[T]:
        if value is None:
            return None
        kwargs = {k.name: deserialize_value(value[k.name], k.type) for k in fields(cls)}
        return cls(**kwargs)

    @classmethod
    def query(cls: Type[T], cursor: SupportsCursor, query: str, values: Optional[Union[tuple, dict]] = None) \
            -> Optional[T]:
        if values is not None:
            query = cursor.execute(query, values)
        else:
            query = cursor.execute(query)
        result = query.fetchone()
        if result is None:
            return None
        else:
            description: Any = cursor.description
            col_names: list[str] = [col[0] for col in description]
            data: dict[str, Any] = dict(zip(col_names, result))
            return cls.deserialize(data)

    @classmethod
    def query_many(cls: Type[T], cursor: SupportsCursor, query: str, values: Optional[Union[tuple, dict]] = None) \
            -> list[T]:
        if values is not None:
            query = cursor.execute(query, values)
        else:
            query = cursor.execute(query)
        result = query.fetchall()
        description: Any = cursor.description
        col_names: list[str] = [col[0] for col in description]
        data: list[dict[str, Any]] = [dict(zip(col_names, row)) for row in result]
        return list(map(lambda r: cls.deserialize(r), data))

    @classmethod
    def all(cls: Type[T], cursor: SupportsCursor) -> list[T]:
        return cls.query_many(cursor, f"select * from {cls.Meta.table_name};")

    @classmethod
    def find(cls: Type[T], cursor: SupportsCursor, id: Any) -> Optional[T]:
        return cls.query(cursor, f"select * from {cls.Meta.table_name} where {cls.Meta.primary_key} = ?;", (id,))

    @classmethod
    def delete(cls: Type[T], cursor: SupportsCursor, id: Any):
        if cls.find(cursor, id) is None:
            raise AttributeError(f"object with primary key \"{id}\" does not exist")
        cursor.execute(f"delete from {cls.Meta.table_name} where {cls.Meta.primary_key} = ?;", (id,))

    def destroy(self: T, cursor: SupportsCursor):
        self.delete(cursor, getattr(self, self.Meta.primary_key))

    def save(self: T, cursor: SupportsCursor):
        data = self.serialize()
        if self.find(cursor, getattr(self, self.Meta.primary_key)) is not None:
            query = [f"update {self.__class__.Meta.table_name} set "]
            for field in fields(self)[1:]:
                query += f"{field.name} = ?, "
            query[:-1] = query[:-1][:-1]
            query.append(f"where {self.Meta.primary_key} = ?;")
            cursor.execute("".join(query), data[1:] + (data[0],))
        else:
            query = [
                f"insert into {self.Meta.table_name} values ",
                "(",
                ", ".join(["?"] * len(fields(self))),
                ");"
            ]
            cursor.execute("".join(query), data)

    def update(self: T, cursor: SupportsCursor, field: str, value: Any):
        if field not in fields(self):
            raise AttributeError(f"\"{field}\" is not a valid field for this model")
        if field == self.Meta.primary_key:
            raise ValueError("cannot change the primary key of an object")
        setattr(self, field, value)
        serialized_value = serialize_value(value)
        if self.find(cursor, self.Meta.primary_key) is not None:
            self.save(cursor)
        else:
            cursor.execute(f"update posts set {field} = ? where {self.Meta.primary_key} = ?;",
                           (serialized_value, getattr(self, self.Meta.primary_key)))
