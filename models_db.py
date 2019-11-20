from utils import LimitFilter, build_filename, clean_string
from typing import List, Optional, Iterable
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean, Date, desc
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator
import json
import os

Base = declarative_base()


# Type decorators


class JSONB(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value else None

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value) if value else None
        except json.JSONDecodeError:
            return None


# Many-to-many association tables

submission_tag_association_table = Table(
    "submission_tags",
    Base.metadata,
    Column(
        "submission_id",
        Integer,
        ForeignKey("submissions.submission_id"),
        primary_key=True,
    ),
    Column("tag_id", String, ForeignKey("tags.tag_id"), primary_key=True),
)

submission_group_association_table = Table(
    "submission_groups",
    Base.metadata,
    Column(
        "submission_id",
        Integer,
        ForeignKey("submissions.submission_id"),
        primary_key=True,
    ),
    Column("group_name", String, ForeignKey("groups.group_name"), primary_key=True),
)

submission_species_association_table = Table(
    "submission_species",
    Base.metadata,
    Column(
        "submission_id",
        Integer,
        ForeignKey("submissions.submission_id"),
        primary_key=True,
    ),
    Column(
        "species_name", String, ForeignKey("species.species_name"), primary_key=True
    ),
)

submission_form_association_table = Table(
    "submission_forms",
    Base.metadata,
    Column(
        "submission_id",
        Integer,
        ForeignKey("submissions.submission_id"),
        primary_key=True,
    ),
    Column("form_id", Integer, ForeignKey("characterforms.form_id"), primary_key=True),
)


# Mixins


class SubmissionFilterMixin(object):
    def submissions_filtered(
        self, filter: Optional[LimitFilter] = None
    ) -> Iterable["__class__"]:
        if not filter:
            return self.submissions

        return filter.filter(self.submissions)


# Tables


class Artist(Base, SubmissionFilterMixin):
    __tablename__ = "artists"

    name = Column(String, primary_key=True)
    links = Column(JSONB, nullable=True)
    path = Column(String)

    # Relationships
    submissions = relationship("Submission", back_populates="artist")

    # Local methods
    def slug(self) -> str:
        return clean_string(self.name).lower()

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        return "{}/{}".format(self.slug(), build_filename("index", limit=limit))

    def __repr__(self):
        return u"Artist(name={0})".format(self.name)

    # Static methods
    @staticmethod
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        artist_results = Artist.query.order_by(Artist.name).all()
        if len(artist_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for artist in artist_results:
            if any(map(lambda m: m.is_visible(limit), artist.submissions)):
                yield artist

    @staticmethod
    def get_path_all(limit: Optional[LimitFilter] = None) -> str:
        return build_filename("all_artists", limit=limit)


class Submission(Base):
    __tablename__ = "submissions"

    submission_id = Column(Integer, primary_key=True)

    submission_type = Column(String, default="image")
    filename = Column(String)
    title = Column(String)
    slug = Column(String)
    date = Column(Date)
    description = Column(String, nullable=True)
    visibility = Column(String, nullable=True)
    lockout = Column(String, nullable=True)
    sequence = Column(JSONB, nullable=True)
    my_links = Column(JSONB, nullable=True)
    artist_links = Column(JSONB, nullable=True)

    # Relationships
    artist_id = Column(Integer, ForeignKey(Artist.name))
    artist = relationship("Artist", back_populates="submissions")

    characters = relationship(
        "CharacterForm", secondary=submission_form_association_table
    )
    tags = relationship("Tag", secondary=submission_tag_association_table)
    species = relationship("Species", secondary=submission_species_association_table)
    groups = relationship("Group", secondary=submission_group_association_table)

    # Local methods
    def get_date_str(self) -> str:
        return "{d:%B} {d.day}, {d.year}".format(d=self.date)

    def get_file_ext(self) -> str:
        img_fn, img_ext = os.path.splitext(self.filename)
        return img_ext[1:]

    def get_thumbnail_name(self, size: int) -> str:
        return "{slug}_{size}.{ext}".format(
            size=size, slug=self.slug, ext=self.get_file_ext()
        )

    def is_visible(self, limit: Optional[LimitFilter] = None) -> bool:
        return limit.is_visible(self) if limit else True

    def get_path(
        self, in_artist_dir: bool = False, limit: Optional[LimitFilter] = None
    ) -> str:
        path = build_filename(self.slug, limit=limit)

        if not in_artist_dir:
            path = "{}/{}".format(self.artist.slug(), path)

        return path

    def __repr__(self):
        return u"Submission(filename={0}, artist={1})".format(
            self.filename, self.artist
        )

    # Static methods
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        submission_results = Submission.query.order_by(desc(Submission.date)).all()
        if len(submission_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for sub in submission_results:
            if sub.is_visible(limit):
                yield sub


class Species(Base, SubmissionFilterMixin):
    __tablename__ = "species"

    species_name = Column(String, primary_key=True)
    description = Column(String, nullable=True)
    softname = Column(String, nullable=True)

    # Relationships
    forms = relationship("CharacterForm", back_populates="species")
    submissions = relationship(
        "Submission", secondary=submission_species_association_table
    )

    # Local methods
    def slug(self) -> str:
        return self.species_name.lower()

    def get_friendly_name(self, lower: bool = False) -> str:
        output = self.softname if self.softname else self.species_name
        if lower:
            output = output.lower()
        return output

    def get_detail(self, as_none=False) -> str:
        if self.description:
            return self.description
        elif as_none:
            return None
        else:
            return self.species_name

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        return "_species/{}".format(build_filename(self.slug(), limit=limit))

    def __repr__(self):
        return u"Species(species_name={0})".format(self.species_name)

    # Static methods
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        species_results = Species.query.order_by(Species.species_name).all()
        if len(species_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for spec in species_results:
            if any(map(lambda m: m.is_visible(limit), spec.submissions)):
                yield spec

    @staticmethod
    def get_path_all(limit: Optional[LimitFilter] = None) -> str:
        return build_filename("all_species", limit=limit)


class Tag(Base, SubmissionFilterMixin):
    __tablename__ = "tags"

    tag_id = Column(String, primary_key=True)
    tag_name = Column(String)
    description = Column(String, nullable=True)
    softname = Column(String, nullable=True)

    # Relationships
    parent_id = Column(Integer, ForeignKey(tag_id), nullable=True)
    children = relationship("Tag", backref=backref("parent", remote_side=[tag_id]))

    submissions = relationship("Submission", secondary=submission_tag_association_table)

    # Local methods
    def slug(self) -> str:
        return self.tag_id.lower().replace("#", "_")

    def get_friendly_name(self, lower: bool = False) -> str:
        output = self.softname if self.softname else self.tag_id
        if lower:
            output = output.lower()
        return output

    def get_detail(self, as_none=False) -> str:
        if self.description:
            return self.description
        elif as_none:
            return None
        else:
            return self.friendly_name()

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        return "_tags/{}".format(build_filename(self.slug(), limit=limit))

    def __repr__(self):
        return u"Tag(tag_id={0})".format(self.tag_id)

    # Static methods
    def get_all(
        limit: Optional[LimitFilter] = None, ignore: Optional[List[str]] = None
    ) -> Iterable["__class__"]:
        query = Tag.query.order_by(Tag.tag_id)
        if ignore:
            query = query.filter(Tag.tag_name not in ignore)

        tag_results = query.all()
        if len(tag_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for tag in tag_results:
            if any(map(lambda m: m.is_visible(limit), tag.submissions)):
                yield tag

    @staticmethod
    def get_path_all(limit: Optional[LimitFilter] = None) -> str:
        return build_filename("all_tags", limit=limit)


class Group(Base, SubmissionFilterMixin):
    __tablename__ = "groups"

    group_name = Column(String, primary_key=True)
    description = Column(String, nullable=True)
    softname = Column(String, nullable=True)

    # Relationships
    submissions = relationship(
        "Submission", secondary=submission_group_association_table
    )

    # Local methods
    def slug(self) -> str:
        return self.group_name.lower()

    def get_friendly_name(self, lower: bool = False) -> str:
        output = self.softname if self.softname else self.group_name
        if lower:
            output = output.lower()
        return output

    def get_detail(self, as_none=False) -> str:
        if self.description:
            return self.description
        elif as_none:
            return None
        else:
            return self.friendly_name()

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        return "_groups/{}".format(build_filename(self.slug(), limit=limit))

    def __repr__(self):
        return u"Group(group_name={0})".format(self.group_name)

    # Static methods
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        group_results = Group.query.order_by(Group.group_name).all()
        if len(group_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for group in group_results:
            if any(map(lambda m: m.is_visible(limit), group.submissions)):
                yield group

    @staticmethod
    def get_path_all(limit: Optional[LimitFilter] = None) -> str:
        return build_filename("all_groups", limit=limit)


class Character(Base):
    __tablename__ = "characters"

    name: str = Column(String, primary_key=True)
    description: str = Column(String, nullable=True)
    owner: str = Column(String, nullable=True)
    root: bool = Column(Boolean, default=False)
    links = Column(JSONB, nullable=True)

    # Relationships
    forms = relationship("CharacterForm", back_populates="character")

    # Local methods
    def slug(self) -> str:
        return self.name.lower()

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        return "_characters/{}".format(build_filename(self.slug(), limit=limit))

    def __repr__(self):
        return u"Character(name={0})".format(self.name)

    def get_root_forms(
        self, limit: Optional[LimitFilter] = None
    ) -> Iterable["CharacterForm"]:
        for form in self.forms:
            if not form.is_subform:
                yield form

    def submissions_filtered(
        self, limit: Optional[LimitFilter] = None
    ) -> Iterable[Submission]:
        for form in self.forms:
            yield from form.submissions_filtered(limit)

    # Static methods
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        character_results: List[Character] = Character.query.order_by(
            Character.name
        ).all()
        if len(character_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for char in character_results:
            if any(char.submissions_filtered(limit)):
                yield char

    @staticmethod
    def get_path_all(limit: Optional[LimitFilter] = None) -> str:
        return build_filename("all_characters", limit=limit)


class CharacterForm(Base, SubmissionFilterMixin):
    __tablename__ = "characterforms"

    form_id = Column(String, primary_key=True)
    form_name = Column(String)
    description = Column(String, nullable=True)
    is_subform = Column(Boolean, default=False)
    refsheets = Column(JSONB, nullable=True)

    # Relationships
    parent_id = Column(Integer, ForeignKey(form_id), nullable=True)
    children = relationship(
        "CharacterForm", backref=backref("parent", remote_side=[form_id])
    )

    character_name = Column(Integer, ForeignKey(Character.name))
    character = relationship("Character", back_populates="forms")

    species_name = Column(String, ForeignKey(Species.species_name))
    species = relationship("Species", back_populates="forms")

    submissions = relationship(
        "Submission", secondary=submission_form_association_table
    )

    # Local methods
    def slug(self) -> str:
        return self.form_name.lower()

    def get_friendly_name(self, lower: bool = False) -> str:
        output = self.form_name
        if self.is_subform:
            output += " " + self.parent.species.get_friendly_name()
        output = output.lower()
        if not lower:
            output = output.lower().capitalize()
        return output

    def get_path(self, limit: Optional[LimitFilter] = None) -> str:
        char_path = self.character.get_path(limit)
        if self.is_subform:
            return "{}#{}_{}".format(char_path, self.parent.slug(), self.slug())
        else:
            return "{}#{}".format(char_path, self.slug())

    def __repr__(self):
        return u"CharacterForm(id={0})".format(self.form_id)

    # Static methods
    def get_all(limit: Optional[LimitFilter] = None) -> Iterable["__class__"]:
        character_results = CharacterForm.query.order_by(CharacterForm.form_id).all()
        if len(character_results) < 1:
            return []

        # TODO: Figure out how to turn limits into query filters
        for char in character_results:
            if any(map(lambda m: m.is_visible(limit), char.submissions)):
                yield char
