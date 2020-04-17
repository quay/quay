import hashlib

from sqlalchemy import (
    Table,
    MetaData,
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    Date,
    BigInteger,
    Index,
    text,
)
from peewee import (
    PrimaryKeyField,
    CharField,
    BooleanField,
    DateTimeField,
    TextField,
    ForeignKeyField,
    BigIntegerField,
    IntegerField,
    DateField,
)


OPTIONS_TO_COPY = [
    "null",
    "default",
    "primary_key",
]


OPTION_TRANSLATIONS = {
    "null": "nullable",
}


MAXIMUM_INDEX_NAME_LENGTH = 64
MAXIMUM_INDEX_NAME_ALLOWANCE = 54


def normalize_index_name(index_name, legacy_index_map):
    if len(index_name) <= MAXIMUM_INDEX_NAME_LENGTH:
        return index_name

    # If a legacy name was defined, use it instead.
    if index_name in legacy_index_map:
        return legacy_index_map[index_name]

    # Otherwise, hash the index name and use a short SHA + the allowance
    # to generate a unique, stable name.
    hashed = hashlib.sha256(index_name).hexdigest()
    updated = "%s_%s" % (index_name[0:MAXIMUM_INDEX_NAME_ALLOWANCE], hashed[0:8])
    assert len(updated) <= MAXIMUM_INDEX_NAME_LENGTH
    return updated


def gen_sqlalchemy_metadata(peewee_model_list, legacy_index_map=None):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    for model in peewee_model_list:
        meta = model._meta

        all_indexes = set(meta.indexes)
        fulltext_indexes = []

        columns = []
        for field in meta.sorted_fields:
            alchemy_type = None
            col_args = []
            col_kwargs = {}
            if isinstance(field, PrimaryKeyField):
                alchemy_type = Integer
            elif isinstance(field, CharField):
                alchemy_type = String(field.max_length)
            elif isinstance(field, BooleanField):
                alchemy_type = Boolean
            elif isinstance(field, DateTimeField):
                alchemy_type = DateTime
            elif isinstance(field, DateField):
                alchemy_type = Date
            elif isinstance(field, TextField):
                alchemy_type = Text
            elif isinstance(field, ForeignKeyField):
                alchemy_type = Integer
                all_indexes.add(((field.name,), field.unique))
                if not field.deferred:
                    target_name = "%s.%s" % (
                        field.rel_model._meta.table_name,
                        field.rel_field.column_name,
                    )
                    col_args.append(ForeignKey(target_name))
            elif isinstance(field, BigIntegerField):
                alchemy_type = BigInteger
            elif isinstance(field, IntegerField):
                alchemy_type = Integer
            else:
                raise RuntimeError("Unknown column type: %s" % field)

            if hasattr(field, "__fulltext__"):
                # Add the fulltext index for the field, based on whether we are under MySQL or Postgres.
                fulltext_indexes.append(field.name)

            for option_name in OPTIONS_TO_COPY:
                alchemy_option_name = (
                    OPTION_TRANSLATIONS[option_name]
                    if option_name in OPTION_TRANSLATIONS
                    else option_name
                )
                if alchemy_option_name not in col_kwargs:
                    option_val = getattr(field, option_name)
                    col_kwargs[alchemy_option_name] = option_val

            if field.unique or field.index:
                all_indexes.add(((field.name,), field.unique))

            new_col = Column(field.column_name, alchemy_type, *col_args, **col_kwargs)
            columns.append(new_col)

        new_table = Table(meta.table_name, metadata, *columns)

        for col_prop_names, unique in all_indexes:
            col_names = [meta.fields[prop_name].column_name for prop_name in col_prop_names]
            index_name = "%s_%s" % (meta.table_name, "_".join(col_names))
            col_refs = [getattr(new_table.c, col_name) for col_name in col_names]
            Index(normalize_index_name(index_name, legacy_index_map), *col_refs, unique=unique)

        for col_field_name in fulltext_indexes:
            index_name = "%s_%s__fulltext" % (meta.table_name, col_field_name)
            col_ref = getattr(new_table.c, col_field_name)
            Index(
                normalize_index_name(index_name, legacy_index_map),
                col_ref,
                postgresql_ops={col_field_name: "gin_trgm_ops"},
                postgresql_using="gin",
                mysql_prefix="FULLTEXT",
            )

    return metadata
