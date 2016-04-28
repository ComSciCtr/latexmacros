#!/usr/bin/env python
###############################################################################
# publish.py
#
# A script to take a latex project and produce a version more suitable for
# archaic journals.
#
# Copyright 2016 Ryan G. James.
# This work may be used freely as long as this notice is included.
# The work is provided "as is" without warranty, express or implied.
###############################################################################

import click
import logbook
import pathlib
import regex as re
import sarge
import sys

from itertools import product

re.DEFAULT_VERSION = re.VERSION1

LOG_STREAM = logbook.StreamHandler(sys.stdout)
LOG_STREAM.format_string = "{record.level_name}: {record.message}"
LOG = logbook.Logger('Publisher')

DIRECTORY_NAME = 'publish'

TEMPLATE_FILES = [
    'cmechabbrev.tex',
    'cmvec.sty',
    'dynlearn.sty',
    'idiagrams.tikz',
    'infotheory.tex',
    'vaucanson.tikz',
]

UNWANTED_EXTENSIONS = [
    'aux',
    'bbl',
    'bib',
    'blg',
    'brf',
    'log',
    'lox',
    'out',
    'sed',
    # 'sty',
    'tikz',
    'toc',
]

IMAGE_EXTENSIONS = [
    'pdf',
    'eps',
    'ps',
    'png',
    'jpg',
    'bmp',
]


@click.command()
@click.argument('tex')
@click.option('--inline', default='', help='comma seperated list of macro files to inline')
def publish(tex, inline):
    """
    This command performs several operations:

    - Produce a `publish` directory with tex files copied over

    - Remove comments

    - Factor out tikz code

    - Rename images to figure-n.pdf and place them alongside the tex

    - Factors out cref

    - Produces the .bbl file

    - Ensure status is `final`

    - Remove `fixme` notes

    - Inline the bbl file

    - Remove unneeded files

    """
    if len(tex.split('.')) < 2:
        tex += '.tex'

    LOG.info('Creating publication version of {}'.format(tex))
    pdir = create_and_populate(tex)

    LOG.info('Removing comments')
    remove_comments(tex, pdir)

    LOG.info('Removing TikZ dependency')
    remove_tikz(tex, pdir)

    LOG.info('Copying images')
    copy_and_rename_figures(tex, pdir)

    LOG.info('Removing cref dependency')
    remove_cref(tex, pdir)

    LOG.info('Removing fixmes')
    remove_notes(tex, pdir)

    LOG.info('Making document final')
    make_final(tex, pdir)

    LOG.info('Inlining the bbl file')
    inline_bbl(tex, pdir)

    LOG.info('Compiling document')
    compile_tex(tex, pdir, bibtex=False)

    LOG.info('Cleaning directory')
    clean_directory(pdir)


def create_and_populate(tex):
    """
    """
    cwd = pathlib.Path().cwd()
    pdir = (cwd / DIRECTORY_NAME)

    if pdir.exists():
        LOG.warn('Removing existing {} directory'.format(DIRECTORY_NAME))
        cmd = sarge.shell_format("rm -rf {0}", DIRECTORY_NAME)
        sarge.run(cmd, cwd=str(cwd))

    pdir.mkdir()

    files = TEMPLATE_FILES + find_bib_files(tex) + [tex]
    for filename in files:
        cmd = sarge.shell_format("cp {0} {1}", filename, DIRECTORY_NAME)
        sarge.run(cmd, cwd=str(cwd))

    return str(pdir)


def find_bib_files(tex):
    """
    """
    bib_file_regex = r'\\bibliography{(?P<bib_files>.+)}'

    with open(tex) as source:
        bib_file_matches = re.search(bib_file_regex, source.read())

    bib_files = bib_file_matches.groupdict()['bib_files']
    bib_files = [ fn+'.bib' for fn in bib_files.split(',')]
    return bib_files


def remove_comments(tex, cwd):
    """
    """
    comment_regex = r'%.*'
    with open("{}/{}".format(cwd, tex)) as source:
        source = source.read()

    source = re.sub(comment_regex, '%', source)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)


def remove_tikz(tex, cwd):
    """
    """
    # find tikz cache directory
    sty_file = cwd+'/dynlearn.sty'

    tikz_prefix_regex = r'\\tikzsetexternalprefix\{(?P<tikz>.*)\}'
    with open(sty_file) as dynlearn:
        tikz_dir = re.search(tikz_prefix_regex, dynlearn.read())
    tikz_dir = tikz_dir.groupdict()['tikz']

    # ensure that the externalize directory exists
    tikz_dir_path = pathlib.Path(tikz_dir)
    if not tikz_dir_path.exists():
        tikz_dir_path.mkdir()

    # ensure that externalize is on
    dynlearn_fn = str(pathlib.Path().cwd() / 'dynlearn.sty')

    with open(dynlearn_fn) as dynlearn:
        source = dynlearn.read()

    source = re.sub(r'%\W*\\tikzexternalize', r'\\tikzexternalize', source)

    with open(dynlearn_fn, 'w') as dynlearn:
        dynlearn.write(source)

    # generate images
    compile_tex(tex, str(pathlib.Path().cwd()))

    # replace tikzpictures with includegraphics
    def fig_name_gen():
        incl_gfx = r'\includegraphics{{{{{}{}-figure{{}}}}}}'
        incl_gfx = incl_gfx.format(tikz_dir, tex.split('.')[0])
        i = 0
        while True:
            fn = incl_gfx.format(i)
            i += 1
            yield fn

    with open("{}/{}".format(cwd, tex)) as source:
        source = source.read()

    tikz_regex = r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}'
    repls = fig_name_gen()

    source = re.sub(tikz_regex, lambda mo: next(repls), source, flags=re.MULTILINE|re.DOTALL)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)

    # comment out tikz includes
    tikz_imports = [
        r'\\usepackage\{tikz\}',
        r'\\usetikzlibrary\{.*\}',
        r'\\pgfkeys\{.*\}',
        r'\\tikzexternalize',
        r'\\tikzsetexternalprefix\{.*\}',
        r'\\input\{.*\.tikz\}',
        r'\\usepackage\{pgfplots\}',
        r'\\usepgfplotslibrary\{.*\}',
        r'\\pgfplotsset\{.*\}',
    ]
    comment_lines("{}/{}".format(cwd, 'dynlearn.sty'), tikz_imports)


def copy_and_rename_figures(tex, dest_dir):
    """
    """
    cwd = str(pathlib.Path().cwd())

    def image_renamer():
        fn = "figure_{:02}.{}"
        i = 1
        file_path = yield

        while True:
            options, file_path = file_path.groups()
            file_path = find_img("{}/{}".format(cwd, file_path))

            new_file_name = fn.format(i, file_path.split('.')[-1])

            to_path = "{}/{}".format(dest_dir, new_file_name)

            cmd = sarge.shell_format("cp {0} {1}", file_path, to_path)

            sarge.run(cmd)

            i += 1

            incl_gfx = "\\includegraphics{}{{{}}}"

            file_path = yield incl_gfx.format(options, new_file_name)

    with open("{}/{}".format(dest_dir, tex)) as source:
        source = source.read()

    img_regex = r'\\includegraphics(.*)\{(.*)\}'
    img_repl = image_renamer()
    next(img_repl)

    source = re.sub(img_regex, img_repl.send, source)

    with open("{}/{}".format(dest_dir, tex), 'w') as output:
        output.write(source)


def find_img(path):
    """
    """
    img = pathlib.Path(path)
    if not img.exists(): # path didn't have an extension
        for ext in IMAGE_EXTENSIONS:
            img = pathlib.Path("{}.{}".format(path, ext))
            if img.exists():
                break
        else:
            LOG.warn("Could not find an image matching {}".format(path))
            return None
    return str(img)


def remove_cref(tex, cwd):
    """
    """
    sty_file = cwd+'/dynlearn.sty'

    # add poorman to cleveref import
    cref_regex1 = (r'usepackage\{cleveref\}', r'usepackage[poorman]{cleveref}')
    cref_regex2 = (r'usepackage\[(\w*)\]\{cleveref\}', r'usepackage[\g<1>,poorman]{cleveref}')

    with open(sty_file) as dynlearn:
        source = dynlearn.read()

    for exp, repl in [cref_regex1, cref_regex2]:
        source = re.sub(exp, repl, source)

    with open(sty_file, 'w') as dynlearn:
        dynlearn.write(source)

    # generate and run the sed script
    compile_tex(tex, cwd)

    sed_cmd = sarge.shell_format("sed -f {0}.sed {0}.tex > {0}.tex.temp", tex.split('.')[0])
    sarge.run(sed_cmd, cwd=cwd)
    sarge.run(sarge.shell_format("mv {0}.temp {0}", tex), cwd=cwd)

    # remove the cleveref import
    cref_regex3 = r'\\usepackage\[.*\]\{cleveref\}'
    comment_lines(sty_file, [cref_regex3])


def remove_notes(tex, cwd):
    """
    """
    sty_file = "{}/dynlearn.sty".format(cwd)
    note_types = ['note', 'warning', 'error', 'fatal']
    authors = ['fx'] + find_authors(sty_file)

    with open("{}/{}".format(cwd, tex)) as source:
        source = source.read()

    regexs = [ r'\\{}{}\{{[^{{]*?\}}'.format(a, t) for a, t in product(authors, note_types)]

    for regex in regexs:
        source = re.sub(regex, '', source, re.MULTILINE|re.DOTALL)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)

    comment_lines("{}/{}".format(cwd, tex), [r'\\listoffixmes'])

    fx_regexs = [
        r'\\usepackage.*\{fixme\}',
        r'\\fxsetup\{.*\}',
        r'\\fxsetface\{.*\}',
        r'\\FXRegisterAuthor\{.*\}',
    ]
    comment_lines(sty_file, fx_regexs)


def make_final(tex, cwd):
    """
    """
    regex = r'(\\documentclass\[.*)(draft)(.*)'

    with open("{}/{}".format(cwd, tex)) as source:
        source = source.read()

    source = re.sub(regex, r'\g<1>final\g<3>', source)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)


def inline_bbl(tex, cwd):
    """
    """
    regex = re.compile(r'\\bibliography\{.*?\}')


    with open("{}/{}.bbl".format(cwd, tex.split('.')[0])) as bbl:
        bbl = bbl.readlines()

    with open("{}/{}".format(cwd, tex)) as source:
        source = source.readlines()

    bib = [ i for i, line in enumerate(source) if regex.match(line) ]

    if bib:
        source = source[:bib[0]] + bbl + source[bib[0]+1:]

        with open("{}/{}".format(cwd, tex), 'w') as output:
            output.writelines(source)



def find_authors(sty_file):
    """
    """
    regex = r'\\FXRegisterAuthor\{(.*?)\}\w*'

    with open(sty_file) as source:
        source = source.read()

    authors = re.findall(regex, source)

    return authors


def comment_lines(filename, regexs):
    """
    """
    with open(filename) as source:
        source = source.read()

    for regex in regexs:
        source = re.sub(regex, r'% \g<0>', source)

    with open(filename, 'w') as output:
        output.write(source)


def compile_tex(tex, cwd, bibtex=True):
    """
    """
    pdflatex = "pdflatex --shell-escape {}".format(tex)
    bibtex = "bibtex {}".format(tex.split('.')[0])

    cmds = [pdflatex, pdflatex]
    if bibtex:
        cmds = [pdflatex, bibtex] + cmds

    for cmd in cmds:
        sarge.capture_both(cmd, cwd=cwd)


def clean_directory(cwd):
    """
    """
    p = pathlib.Path(cwd)
    for ext in UNWANTED_EXTENSIONS:
        files = p.glob('*.{}'.format(ext))
        for file in files:
            if file.exists():
                file.unlink()


if __name__ == '__main__':
    with LOG_STREAM.applicationbound():
        publish()
