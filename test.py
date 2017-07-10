import cattr
import yaml
from models import ArtistFile

def load_artist_file(filename):
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, ArtistFile)
        print(obj)


load_artist_file("testdata/Amber-Aria/.art.yaml")
