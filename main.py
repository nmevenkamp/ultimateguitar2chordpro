import os
import re
import sys
import subprocess
import unicodedata
from enum import Enum
from glob import glob
from tqdm import tqdm

import PyPDF2


class OutputMode(Enum):
    PRINT = 0
    CHO = 1
    PDF = 2
    CHO_PDF = 3
    PRINT_RAW = 4
    ALL_PDF = 5
    SONGBOOK = 6


MODE = OutputMode.SONGBOOK
TITLE = "Viertel vor Sieben"
ARTIST = "Reinhard May"
CAPO = None
COLUMNS = 2
TEXTSIZE = 10

INPUT_FILE = "plain_text.txt"
OUTPUT_DIR = "D:\\Dropbox\\ChordPro"
CHORDPRO_EXE = "C:\\Program Files (x86)\\ChordPro.ORG\\ChordPro\\chordpro.exe"
CHORDPRO_CFG = "D:\\Dropbox\\ChordPro\\config.json"


def main():
    if MODE is OutputMode.ALL_PDF:
        save_all_pdf()
        return

    if MODE is OutputMode.SONGBOOK:
        save_songbook()
        return

    if MODE in {OutputMode.PRINT, OutputMode.CHO, OutputMode.CHO_PDF, OutputMode.PRINT_RAW}:
        # add title and subtitle
        res = f"{{title: {ARTIST} - {TITLE}}}\r\n"
        res += f"{{columns: {COLUMNS}}}\r\n"
        if TEXTSIZE is not None:
            res += f"{{textsize: {TEXTSIZE}}}\r\n"
        if CAPO is not None:
            res += f"{{subtitle: Capo: {CAPO}}}\r\n"
        res += "\n"

        # load raw text
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            plain_text = f.readlines()

        cleanup(plain_text)

        if MODE is OutputMode.PRINT_RAW:
            for line in plain_text:
                print(repr(line))
            return

        res += get_cho(plain_text)
    else:
        res = ""

    if MODE is OutputMode.PRINT:
        print(res)
    if MODE in {OutputMode.CHO, OutputMode.CHO_PDF}:
        basename = f"{slugify(ARTIST)}-{slugify(TITLE)}"
        fname_cho = os.path.join(OUTPUT_DIR, 'cho', f"{basename}.cho")

        if os.path.isfile(fname_cho):
            answer = input(f"'{basename}.cho' already exists. Are you sure you want to overwrite it? (yes/no): ")
            if answer not in {"y", "yes"}:
                return

        with open(fname_cho, 'w') as f:
            f.write(res)
            print(f"'{ARTIST} - {TITLE}' CHO saved to '{fname_cho}'")
    if MODE in {OutputMode.PDF, OutputMode.CHO_PDF}:
        if ARTIST is not None and TITLE is not None:
            basename = f"{slugify(ARTIST)}-{slugify(TITLE)}"
            fname_cho = os.path.join(OUTPUT_DIR, 'cho', f"{basename}.cho")
            generate_pdf(fname_cho)
            print(f"'{ARTIST} - {TITLE}' PDF saved to '{(fname_cho.replace('.cho', '.pdf'))}'")
        else:
            fnames_cho = glob(os.path.join(OUTPUT_DIR, 'cho', "*.cho"))
            for fname_cho in tqdm(fnames_cho, desc="generating PDFs", file=sys.stdout):
                generate_pdf(fname_cho)


def generate_pdf(fname_cho):
    fname_pdf = fname_cho.replace("cho", "pdf")
    chordpro_cmd = f"\"{CHORDPRO_EXE}\""
    if CHORDPRO_CFG:
        chordpro_cmd += f" --config=\"{CHORDPRO_CFG}\""
    chordpro_cmd += f" --output=\"{fname_pdf}\" \"{fname_cho}\""
    subprocess.call(chordpro_cmd)


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


def get_chords_positions(chords_str, chords_lib=None):
    if chords_lib is None:
        chords_lib = get_chords_lib()

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

    if chord is not None and len(chords) < len(positions):
        chords.append(chord)

    if len(chords) != len(positions):
        raise ValueError("chords and positions expected to have equal length!")

    chords = [c.replace(",", "") for c in chords]

    return chords, positions


def merge(line, chords_str, chords_lib=None):
    if chords_lib is None:
        chords_lib = get_chords_lib()

    if not chords_str:
        return line
    chords, positions = get_chords_positions(chords_str)

    if not chords:
        return line

    if len(line) - 1 < positions[-1]:
        offset = positions[-1] - len(line) + 1
        line = line.replace("\n", "")
        line += "".join([" "] * offset) + "\n"
    res = ""
    for i, c in enumerate(line):
        if i in positions:
            ii = positions.index(i)
            chord = chords[ii]
            if chord in chords_lib:
                res += f"[{chord}]"
            else:
                res += f"[({chord})]"
        res += c

    return res


def cleanup(plain_text):
    for i in range(len(plain_text)):
        if plain_text[i].lstrip(" ") == "\n":
            plain_text[i] = "\n"

    # remove leading blank lines
    while plain_text[0] == "\n":
        del plain_text[0]

    # remove trailing blank lines
    while plain_text[-1] == "\n":
        del plain_text[-1]

    # remove in-between blanks (if there is just a single one, otherwise reduce to a single one)
    i = 0
    force_delete = False
    chorus = False
    while i < len(plain_text) - 1:
        if plain_text[i][0] == "[":
            force_delete = True

            if plain_text[i] == "[Chorus]\n":
                plain_text[i] = "{start_of_chorus}\n"
                chorus = True
                i += 1
                continue

            del plain_text[i]
            continue

        if plain_text[i] == "\n":
            if force_delete:
                del plain_text[i]
                continue
            if plain_text[i + 1] == "\n":  # the next line is also blank, so we remove this one
                if chorus:
                    plain_text[i] = "{end_of_chorus}\n"
                    plain_text.insert(i + 1, "\n")
                    i += 1
                    chorus = False

                force_delete = True
                i += 1
                continue
            del plain_text[i]
            continue

        force_delete = False
        i += 1

    if chorus:
        plain_text.append("{end_of_chorus}\n")


def is_chords_text_pair(plain_text, i ):
    if i >= len(plain_text) - 1:
        return False

    if not is_chords(plain_text[i]):
        return False

    if is_chords(plain_text[i + 1]):
        return False

    if plain_text[i + 1] == "\n":
        return False

    return True


def get_cho(plain_text):
    res = ""

    # parse lines
    i = 0
    while i < len(plain_text):
        if plain_text[i] == "\n":
            res += "\r\n"
            i += 1
            continue

        if is_chords_text_pair(plain_text, i):
            res += merge(plain_text[i + 1], plain_text[i])
            i += 2
            continue

        if is_chords(plain_text[i]):
            res += merge("", plain_text[i])
            i += 1
            continue

        res += plain_text[i]
        i += 1

        # if plain_text[i] == "\n":
        #     i += 1
        #     res += "\r\n"
        #     continue
        # if plain_text[i] == ";\n":
        #     res += "\n" + merge(plain_text[i + 1], "")
        #     i += 2
        #     continue
        # if plain_text[i][0] == ";":
        #     res += merge("", plain_text[i][1:])
        #     i += 1
        #     continue
        # if plain_text[i][0] == "{":
        #     res += plain_text[i]
        #     i += 1
        #     continue
        # chords_str = plain_text[i]
        # line = plain_text[i + 1]
        # res += merge(line, chords_str)
        # i += 2

    return res


def is_chords(line, chords_lib=None):
    if chords_lib is None:
        chords_lib = get_chords_lib()

    words = line.replace(",", "").split(" ")
    words = [word.rstrip().replace("(", "").replace(")", "") for word in words if word]
    chords = [word for word in words if word in chords_lib]

    return len(chords) / len(words) >= 0.5


def get_chords_lib():
    with open("chords_list.txt", "r") as f:
        lines = f.readlines()

    chords = []
    for line in lines:
        line = line.replace("\t", " ")
        chords_ = line.split(" ")
        for chord in chords_:
            if not chord:
                continue

            chords.append(chord.replace('\n', ''))

    return chords


def save_all_pdf():
    fnames_cho = glob(os.path.join(OUTPUT_DIR, 'cho', "*.cho"))

    for fname_cho in tqdm(
        iterable=fnames_cho,
        desc="generating PDFs",
        file=sys.stdout,
    ):
        generate_pdf(fname_cho)


def save_songbook():
    writer = PyPDF2.PdfWriter()

    pdf_paths = glob(os.path.join(OUTPUT_DIR, 'pdf', "*.pdf"))

    page = 0

    for pdf_path in pdf_paths:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            if page % 2 == 1 and len(reader.pages) > 1:
                writer.add_blank_page()
                page += 1

            writer.append_pages_from_reader(reader)
            page += len(reader.pages)

    with open(os.path.join(OUTPUT_DIR, 'songbook.pdf'), 'wb') as f:
        writer.write(f)


if __name__ == "__main__":
    main()
