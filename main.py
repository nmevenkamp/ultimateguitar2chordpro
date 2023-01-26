import os
import re
import unicodedata


INPUT_FILE = "plain_text.txt"
OUTPUT_DIR = "D:\\Dropbox\\ChordPro"
TITLE = "The Call and the Answer"
ARTIST = "De Dannan"
CAPO = 3


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '_', value).strip('-_')


def get_chords_positions(chords_str):
    chords, positions = [], []
    chord = None
    for i, c in enumerate(chords_str):
        if chords_str[i] in {" ", "\n"}:
            if chord is not None:
                chords.append(chord)
                chord = None
        else:
            if chord is None:
                chord = c
                positions.append(i)
            else:
                chord += c

    return chords, positions


def merge(line, chords_str):
    chords, positions = get_chords_positions(chords_str)
    res = ""
    for i, c in enumerate(line):
        if i in positions:
            ii = positions.index(i)
            chord = chords[ii]
            res += f"[{chord}]"
        res += c

    return res


def main():
    with open(INPUT_FILE, 'r') as f:
        plain_text = f.readlines()

    res = f"{{title: {ARTIST} - {TITLE}}}\r\n"
    if CAPO is not None:
        res += f"{{subtitle: Capo: {CAPO}}}\r\n"
    res += "\n"
    i = 0
    while i < len(plain_text) - 1:
        if plain_text[i] == "\n":
            i += 1
            res += "\r\n"
            continue
        chords_str = plain_text[i]
        line = plain_text[i+1]
        res += merge(line, chords_str)
        i += 2

    basename = f"{slugify(ARTIST)}-{slugify(TITLE)}"
    fname = os.path.join(OUTPUT_DIR, f"{basename}.cho")
    with open(fname, 'w') as f:
        f.write(res)


if __name__ == "__main__":
    main()
