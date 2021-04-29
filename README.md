# Jamz

Jamz is a small command-line utility for renaming music files based on their tags.

For example, if you ran:

`jamz ~/Music/Nirvana/Nevermind/ '{jamz_padded_tracknumber} - {title}.flac'`

Your Nevermind songs would now be named:

```txt
01 - Smells Like Teen Spirit.flac
02 - In Bloom.flac
03 - Come as You Are.flac
...
12 - Something in the Way / Endless, Nameless.flac
```

## Usage

Jamz takes two positional arguments, the directory to rename files in, and the template with which to rename them.
For the template, Jamz passes all the tags from each file as formatting arguments, so you can use any tag in your template that the filetype supports.
For example, when working with files that use the Vorbis comment format (FLAC, Ogg, etc.), you can use TITLE, ALBUM, DATE, etc. in your template.

`jamz /mymusic/ '{ARTIST} - {TITLE} - {TRACKNUMBER}.ogg'`

(Note: for this format specifically, jamz also supports using the lowercase version of each tag, e.g. "title")

### Special Tags

Jamz also adds a few special tags of its own. Every Jamz custom tag will start with `jamz`.

`jamz_padded_tracknumber`: If jamz is able to find a tracknumber tag, this will be the tracknumber padded to two digits (e.g. `2` -> `02`)

`jamz_original_suffix`: This will be the original suffix of the file. For example, if the file jamz is processing is `song.flac`, this will be `.flac`.

### Flags

```txt
-r, --recursive  Recursively descend the file tree
-d, --dry-run    Print the new names of the files, but don't actually rename them
-v, --verbose    Enable verbose logging
```

## Technical Details

Jamz uses [Mutagen](https://mutagen.readthedocs.io/en/latest/) to read tags.
All non-special tags available for use in templates come from the Mutagen tags object.
Because Mutagen supports multiple tags per key, Jamz assumes the first value is canonical, and passes only that one to the template.
