import yaml
import cattr
import glob
import os
from datetime import datetime
from typing import List, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import models_file
import models_db


# Database


def open_database() -> scoped_session:
    # TODO: Only make this create the whole thing if it needs to
    engine = create_engine("sqlite:///metadata.sqlite")
    db_session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    Base = models_db.Base

    Base.query = db_session.query_property()
    Base.metadata.drop_all(bind=engine)  # TODO: Don't
    Base.metadata.create_all(bind=engine)

    return db_session


def upsert_tag(
    db: scoped_session,
    tag_id: str,
    description: str = None,
    softname: str = None,
    update: bool = False,
) -> models_db.Tag:
    tag_row = models_db.Tag.query.filter_by(tag_id=tag_id).first()
    if tag_row:
        if update:
            tag_row.softname = softname
    else:
        split = tag_id.split("#")
        parent_tag = None
        if len(split) > 1:
            parent_tag = upsert_tag(db, "#".join(split[:-1]))

        tag_row = models_db.Tag(
            tag_id=tag_id,
            tag_name=split[-1:][0],
            description=description,
            softname=softname,
            parent=parent_tag,
        )
        db.add(tag_row)
        db.commit()

    return tag_row


def upsert_species(
    db: scoped_session,
    species_name: str,
    description: str = None,
    softname: str = None,
    update: bool = False,
) -> models_db.Species:
    if species_name.startswith("species#"):
        # Handle tag entry
        species_name = species_name[8:]

    if "#" in species_name:
        raise RuntimeError("Found hash in species name '{}'".format(species_name))

    species_row = models_db.Species.query.filter_by(species_name=species_name).first()
    if species_row:
        if update:
            species_row.description = description
    else:
        species_row = models_db.Species(
            species_name=species_name, description=description, softname=softname
        )
        db.add(species_row)
        db.commit()

    return species_row


def upsert_group(
    db: scoped_session,
    group_name: str,
    description: str = None,
    softname: str = None,
    update: bool = False,
) -> models_db.Group:
    if group_name.startswith("group#"):
        # Handle tag entry
        group_name = group_name[6:]

    if "#" in group_name:
        raise RuntimeError("Found hash in group name '{}'".format(group_name))

    group_row = models_db.Group.query.filter_by(group_name=group_name).first()
    if group_row:
        if update:
            group_row.description = description
    else:
        group_row = models_db.Group(
            group_name=group_name, description=description, softname=softname
        )
        db.add(group_row)
        db.commit()

    return group_row


def get_character_form(char_tag: str) -> models_db.CharacterForm:
    form_row = models_db.CharacterForm.query.filter_by(form_id=char_tag).first()
    if not form_row:
        raise RuntimeError("Undefined character '{}'".format(char_tag))
    return form_row


def insert_species_dict(db: scoped_session, species: Dict[str, str]):
    if species:
        for s, sn in species.items():
            upsert_species(db, s, softname=sn, update=True)

    db.commit()


def insert_characters_dict(
    db: scoped_session, characters: Dict[str, models_file.Character]
):
    for cn, c in characters.items():
        character_row = models_db.Character(
            name=c.name,
            description=c.description,
            owner=c.owner,
            root=c.root,
            links=cattr.unstructure(c.links),
        )
        db.add(character_row)

        for sn, s in c.species.items():
            top_form_id = "{}#{}".format(cn, sn)
            top_form_row = models_db.CharacterForm(
                form_id=top_form_id,
                form_name=sn,
                description=s.description if s else None,
                refsheets=cattr.unstructure(s.refsheet) if s else None,
                character=character_row,
                species_name=sn,
            )
            db.add(top_form_row)

            if s and s.subforms:
                for sfn, sf in s.subforms.items():
                    subform_row = models_db.CharacterForm(
                        form_id="{}#{}#{}".format(cn, sn, sfn),
                        form_name=sfn,
                        description=sf.description if sf else None,
                        is_subform=True,
                        refsheets=cattr.unstructure(sf.refsheet) if sf else None,
                        character=character_row,
                        species_name=sn,
                        parent_id=top_form_id,
                    )
                    db.add(subform_row)

    db.commit()


def insert_tags_dicts(
    db: scoped_session,
    aliases: Dict[str, str],
    descriptions: Dict[str, str],
    softnames: Dict[str, str],
):
    def insert(tag_name, description=None, softname=None):
        # TODO: This is probably not what we want
        # Images need their tags aliased, so this should probably be a spare table read at upsert time?
        # Or just passed through to the upsert function to begin with...
        if aliases and tag_name in aliases:
            tag_name = aliases[tag_name]

        # Handle magic tags
        if tn.startswith("species#"):
            upsert_species(
                db, tag_name, description=description, softname=softname, update=True
            )
        elif tn.startswith("group#"):
            upsert_group(
                db, tag_name, description=description, softname=softname, update=True
            )
        else:
            upsert_tag(
                db, tag_name, description=description, softname=softname, update=True
            )

    if descriptions:
        for tn, desc in descriptions.items():
            insert(tn, description=desc)

    if softnames:
        for tn, sn in softnames.items():
            insert(tn, softname=sn)

    db.commit()


def insert_artist_file(
    db: scoped_session,
    artist_file: models_file.ArtistFile,
    file_path: str,
    aliases: Dict[str, str],
):
    artist = artist_file.artist
    artist_row = models_db.Artist(
        name=artist.name, links=cattr.unstructure(artist.links), path=file_path,
    )
    db.add(artist_row)
    db.commit()

    files = artist_file.files
    for f in files:
        parsedDate = datetime.strptime(str(f.date), "%Y%m%d")
        file_row = models_db.Submission(
            artist=artist_row,
            filename=f.filename,
            title=f.title,
            slug=f.slug,
            date=parsedDate,
            description=f.description,
            visibility=f.visibility,
            lockout=f.lockout,
            sequence=cattr.unstructure(f.sequence),
            my_links=cattr.unstructure(f.my_links),
            artist_links=cattr.unstructure(f.artist_links),
        )

        tags: set[models_db.Tag] = set()
        species: set[models_db.Species] = set()
        groups: set[models_db.Group] = set()

        for tn in f.tags:
            if aliases and tn in aliases:
                tn = aliases[tn]

            if tn.startswith("species#"):
                species.add(tn)
                continue

            if tn.startswith("group#"):
                groups.add(tn)
                continue

            tags.add(tn)

        for c in f.characters:
            form = get_character_form(c)
            file_row.characters.append(form)
            species.add(form.species_name)

        for tn in tags:
            file_row.tags.append(upsert_tag(db, tn))

        for sn in species:
            file_row.species.append(upsert_species(db, sn))

        for gn in groups:
            file_row.groups.append(upsert_group(db, gn))

        db.add(file_row)
        db.commit()


# Metadata files


class ConfigFileError(Exception):
    def __init__(self, filename=None):
        Exception.__init__(self, filename)

    def __suppress_context__(self):
        return False

    @property
    def filename(self) -> str:
        if self.args:
            filename = self.args[0]
            if filename is not None:
                return filename


def load_artist_file(filename: str) -> models_file.ArtistFile:
    """Load an artist file."""
    with open(filename, "r", encoding="utf-8") as f:
        obj = yaml.load(f.read(), Loader=yaml.SafeLoader)
        obj = cattr.structure(obj, models_file.ArtistFile)
        return obj


def get_artist_files(path: str) -> List[str]:
    files = glob.glob(os.path.join(path, "**", ".art*.yaml"), recursive=True)
    if len(files) == 0:
        raise FileNotFoundError("No content files found.")
    return files


def load_metadata_file(filename: str) -> models_file.MetadataFile:
    """Load a metadata file."""
    with open(filename, "r", encoding="utf-8") as f:
        obj = yaml.load(f.read(), Loader=yaml.SafeLoader)
        obj = cattr.structure(obj, models_file.MetadataFile)
        return obj


def process_art_database(art_path: str):
    """Process some art data."""

    # Open the database
    db = open_database()

    # General metadata, start here
    metapath = os.path.join(art_path, ".metadata.yaml")
    if not os.path.exists(metapath):
        raise FileNotFoundError("No metadata file found.")

    try:
        metadata = load_metadata_file(metapath)
    except Exception as e:
        raise ConfigFileError("Error processing file: {}".format(metapath)) from e

    insert_species_dict(db, metadata.species_softname)
    insert_characters_dict(db, metadata.characters)
    insert_tags_dicts(
        db,
        aliases=metadata.tag_aliases,
        descriptions=metadata.tag_descriptions,
        softnames=metadata.tag_softname,
    )

    # Artist directory files
    for artist_file in get_artist_files(art_path):
        try:
            artist_file_path = os.path.dirname(artist_file)
            artist_data = load_artist_file(artist_file)
            insert_artist_file(db, artist_data, artist_file_path, metadata.tag_aliases)
        except Exception as e:
            raise ConfigFileError(
                "Error processing file: {}".format(artist_file)
            ) from e
