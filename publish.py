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

try:
    from halo import Halo
    SPIN = True
except:
    SPIN = False
import click
import logbook
from logbook.more import ColorizedStderrHandler
try:
    import pathlib2 as pathlib
except:
    import pathlib
try:
    import regex as re
    re.DEFAULT_VERSION = re.VERSION1
except:
    import re
import sarge
import sys

from itertools import product

LOG_STREAM = ColorizedStderrHandler()
LOG_STREAM.format_string = "\r{record.level_name}: {record.message}"
LOG = logbook.Logger('Publisher')

RUN_CMD = sarge.capture_both

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
@click.option('--inline', is_flag=True, help='inline all tex and sty files')
@click.option('--debug', is_flag=True, help='show debug info')
def publish(tex, inline, debug):
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
    if debug:
        global RUN_CMD
        RUN_CMD = sarge.run


    if len(tex.split('.')) < 2:
        tex += '.tex'

    run_task(task='info', msg='Creating publication version of {}'.format(tex))

    pdir = create_and_populate(tex)

    tasks = [('Removing comments', (remove_comments, [tex, pdir])),
             ('Removing TikZ dependency', (remove_tikz, [tex, pdir])),
             ('Copying images', (copy_and_rename_figures, [tex, pdir])),
             ('Removing cref dependency', (remove_cref, [tex, pdir])),
             ('Removing fixmes', (remove_notes, [tex, pdir])),
             ('Making document final', (make_final, [tex, pdir])),
             ('Inlining the bbl file', (inline_bbl, [tex, pdir])),
             ('Compiling document', (compile_tex, [tex, pdir, False])),
             ('Cleaning directory', (clean_directory, [tex, pdir])),
    ]

    if inline:
        tasks[7:8] = [('Inlining files', (inline_files, [tex, pdir]))]
        global UNWANTED_EXTENSIONS
        UNWANTED_EXTENSIONS += ['sty', 'tex']

    for task, func in tasks:
        run_task(task=func, msg=task)


def run_task(task, msg, style=None):
    """
    """
    if SPIN:
        with Halo(text=msg) as spinner:
            if task == 'info':
                spinner.info()
            elif task == 'warn':
                spinner.warn()
            elif task == 'error':
                spinner.fail()
            else:
                try:
                    task[0](*task[1])
                    spinner.succeed()
                except Exception as e:
                    spinner.fail()
                    raise(e)
    else:
        if task == 'info':
            LOG.info(msg)
        elif task == 'warn':
            LOG.warn(msg)
        elif task == 'error':
            LOG.error(msg)
        else:
            LOG.info(msg)
            try:
                task[0](*task[1])
            except Exception as e:
                raise(e)


def create_and_populate(tex):
    """
    """
    cwd = pathlib.Path().cwd()
    pdir = (cwd / DIRECTORY_NAME)

    if pdir.exists():
        run_task(task='warn', msg='Removing existing {} directory'.format(DIRECTORY_NAME))
        cmd = sarge.shell_format("rm -rf {0}", DIRECTORY_NAME)
        RUN_CMD(cmd, cwd=str(cwd))

    pdir.mkdir()

    files = TEMPLATE_FILES + find_bib_files(tex) + [tex]
    for filename in files:
        if pathlib.Path(filename).exists():
            cmd = sarge.shell_format("cp {0} {1}", filename, DIRECTORY_NAME)
            RUN_CMD(cmd, cwd=str(cwd))

    # inline inputs
    cmd = sarge.shell_format('latexpand --keep-comments {0} -o {1}/{0}', tex, str(pdir))
    RUN_CMD(cmd, cwd=str(cwd))

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
    cmd = sarge.shell_format('latexpand --keep-includes {0} -o {0}_new', tex)
    RUN_CMD(cmd, cwd=cwd)
    cmd = sarge.shell_format('mv {0}_new {0}', tex)
    RUN_CMD(cmd, cwd=cwd)


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
    compile_tex(tex, str(pathlib.Path().cwd()), shell_escape=True)

    # remove stuff
    for _ in range(3): # handle nested tikz images
        remove_tikz_named(tex, cwd, tikz_dir)
        remove_tikz_unnamed(tex, cwd, tikz_dir)

    remove_tikz_imports(tex, cwd)


def remove_tikz_named(tex, cwd, tikz_dir):
    """
    """
    # replace tikzpictures with includegraphics
    def fig_name(mo):
        incl_gfx = r'\includegraphics{{{}{}}}'
        incl_gfx = incl_gfx.format(tikz_dir, mo['filename'])
        return incl_gfx

    with open("{}/{}".format(cwd, tex)) as source:
        source = source.read()

    tikz_regex = r'(?:\\tikzsetnextfilename\{(?P<filename>\w*?)\})(?:(?!tikzpicture).)*?(?:\\begin\{tikzpicture\}(?:(?!tikzpicture).)*?\\end\{tikzpicture\})'

    source = re.sub(tikz_regex, fig_name, source, flags=re.MULTILINE|re.DOTALL)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)


def remove_tikz_unnamed(tex, cwd, tikz_dir):
    """
    """
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

    tikz_regex = r'\\begin\{tikzpicture\}(?:(?!tikzpicture).)*?\\end\{tikzpicture\}'
    repls = fig_name_gen()

    source = re.sub(tikz_regex, lambda mo: next(repls), source, flags=re.MULTILINE|re.DOTALL)

    with open("{}/{}".format(cwd, tex), 'w') as output:
        output.write(source)


def remove_tikz_imports(tex, cwd):
    """
    """
    tikz_imports = [
        r'\\usepackage\{tikz\}',
        r'\\usetikzlibrary\{.*?\}',
        r'\\pgfkeys\{.*?\}',
        r'\\tikzexternalize',
        r'\\tikzsetexternalprefix\{.*?\}',
        r'\\tikzsetnextfilename\{.*?\}',
        r'\\input\{.*?\.tikz\}',
        r'\\usepackage\{pgfplots\}',
        r'\\usepgfplotslibrary\{.*?\}',
        r'\\pgfplotsset\{.*?\}',
        r'\\usepackage\{pgfplotstable\}',
        r'\\usepackage\{tcolorbox\}',
        r'\\tcbuselibrary\{.*?\}',
        r'\\usepackage\{circuitikz\}',
    ]
    comment_lines("{}/{}".format(cwd, 'dynlearn.sty'), tikz_imports)
    comment_lines("{}/{}".format(cwd, tex), tikz_imports)


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
            run_task(task='error', msg="Could not find an image matching {}".format(path))
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

    sed_cmd = sarge.shell_format("sed -f {0}.sed {0}.tex", tex.split('.')[0])
    cleaned = RUN_CMD(sed_cmd, cwd=cwd, stdout=sarge.Capture())

    with (pathlib.Path(cwd) / tex).open('w') as output:
        output.write(cleaned.stdout.text)

    # remove the cleveref import
    cref_regex3s = [r'\\usepackage\[.*\]\{cleveref\}',
                    r'\\crefname',
                   ]
    comment_lines(sty_file, cref_regex3s)


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


    regexs2 = [ r'\\{}{}\{{.*?\}}'.format(a, t) for a, t in product(authors, note_types)]

    for regex in regexs2:
        if re.findall(regex, source, re.MULTILINE|re.DOTALL):
            msg = "Some notes could not be removed due to nested curly braces."
            run_task(task='error', msg=msg)
            raise Exception()

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


def compile_tex(tex, cwd, bibtex=True, shell_escape=False):
    """
    """
    if shell_escape:
        pdflatex = "pdflatex -shell-escape {}".format(tex)
    else:
        pdflatex = "pdflatex {}".format(tex)
    bibtex = "bibtex {}".format(tex.split('.')[0])

    cmds = [pdflatex, pdflatex]
    if bibtex:
        cmds = [pdflatex, bibtex] + cmds

    for cmd in cmds:
        RUN_CMD(cmd, cwd=cwd)


def clean_directory(tex, cwd):
    """
    """
    p = pathlib.Path(cwd)
    for ext in UNWANTED_EXTENSIONS:
        files = p.glob('*.{}'.format(ext))
        for file in files:
            if file.exists() and file.name != tex:
                file.unlink()


def inline_files(tex, cwd):
    """
    """
    cmd = sarge.shell_format('latexpand --expand-usepackage {0} -o {0}_new', tex)
    RUN_CMD(cmd, cwd=cwd)
    cmd = sarge.shell_format('mv {0}_new {0}', tex)
    RUN_CMD(cmd, cwd=cwd)


if __name__ == '__main__':
    with LOG_STREAM.applicationbound():
        publish()
