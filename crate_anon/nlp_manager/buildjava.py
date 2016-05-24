#!/usr/bin/env python
# crate/nlp_manager/buildjava.py

"""
Script to compile Java source for CrateGatePipeline

Author: Rudolf Cardinal
Copyright (C) 2015-2016 Rudolf Cardinal.
License: http://www.apache.org/licenses/LICENSE-2.0
"""

import argparse
import glob
import os
import platform
import shlex
import shutil
import stat
import subprocess

from crate_anon.nlp_manager.constants import GATE_PIPELINE_CLASSNAME


def moveglob(src, dest, allow_nothing=False):
    something = False
    for file in glob.glob(src):
        shutil.move(file, dest)
        something = True
    if something or allow_nothing:
        return
    raise ValueError("No files found matching: {}".format(src))


def rmglob(pattern):
    for f in glob.glob(pattern):
        os.remove(f)

WINDOWS = platform.system == 'Windows'
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BUILD_DIR = os.path.join(THIS_DIR, 'compiled_nlp_classes')
SOURCE_FILE = os.path.join(THIS_DIR, GATE_PIPELINE_CLASSNAME + '.java')
DEFAULT_RUNSCRIPT = os.path.join(
    THIS_DIR, 'runjavademo' + ('.bat' if WINDOWS else '.sh'))
DEFAULT_GATEDIR = os.path.join(os.path.expanduser('~'), 'software',
                               'GATE_Developer_8.0')
DEFAULT_JAVA = 'java'
DEFAULT_JAVAC = 'javac'



def hack_shlex_quote(x):
    # shlex.quote should make something suitable for shell escaping. However,
    # it quotes using ', while Windows needs ".
    #
    # http://stackoverflow.com/questions/4748344/whats-the-reverse-of-shlex-split  # noqa
    # http://bugs.python.org/issue9723
    # https://hg.python.org/cpython/file/83f477471351/Lib/shlex.py#l278
    # https://docs.python.org/3/library/shlex.html#shlex.quote
    # https://github.com/rg3/youtube-dl/issues/5889
    x = shlex.quote(x)
    if WINDOWS:
        x = x.replace("'", '"')
    return x


def main():
    parser = argparse.ArgumentParser(
        description="Compile Java classes for CRATE's interface to GATE")
    parser.add_argument(
        '--builddir', default=DEFAULT_BUILD_DIR,
        help="Output directory for compiled .class files (default: {})".format(
            DEFAULT_BUILD_DIR))
    parser.add_argument(
        '--script', default=DEFAULT_RUNSCRIPT,
        help="Output Bash script for testing (default: {})".format(
            DEFAULT_RUNSCRIPT))
    parser.add_argument(
        '--gatedir', default=DEFAULT_GATEDIR,
        help="Root directory of GATE installation (default: {})".format(
            DEFAULT_GATEDIR))
    parser.add_argument(
        '--java', default=DEFAULT_JAVA,
        help="Java executable (default: {})".format(DEFAULT_JAVA))
    parser.add_argument(
        '--javac', default=DEFAULT_JAVAC,
        help="Java compiler (default: {})".format(DEFAULT_JAVAC))
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help="Be verbose (use twice for extra verbosity)")
    args = parser.parse_args()

    gatejar = os.path.join(args.gatedir, 'bin', 'gate.jar')
    gatelibjars = os.path.join(args.gatedir, 'lib', '*')
    classpath = os.pathsep.join([args.builddir, gatejar, gatelibjars])
    classpath_options = ['-classpath', classpath]
    javac_options = (
        ['-Xlint:unchecked'] +
        (['-verbose'] if args.verbose > 0 else []) +
        classpath_options
    )
    java_options = classpath_options
    appfile = os.path.join(args.gatedir,
                           'plugins', 'ANNIE', 'ANNIE_with_defaults.gapp')
    features = ['-a', 'Person', '-a', 'Location']
    eol_options = ['-it', 'END', '-ot', 'END']
    debug_options_1 = ['-v', '-v']
    debug_options_2 = ['-wg', 'wholexml_', '-wa', 'annotxml_']
    prog_args = ['-g', appfile] + features + eol_options + debug_options_1

    cmdargs = [args.javac] + javac_options + [SOURCE_FILE]
    print("Executing command: {}".format(cmdargs))
    subprocess.check_call(cmdargs)
    os.makedirs(args.builddir, exist_ok=True)
    rmglob(os.path.join(args.builddir, '*.class'))
    moveglob(os.path.join(THIS_DIR, '*.class'), args.builddir)

    # JAR build and run
    # mkdir -p jarbuild

    # cd jarbuild
    # javac $JAVAC_OPTIONS ../CrateGatePipeline.java
    # for JARFILE in $GATEJAR $GATELIBJARS; do
    #     echo "Extracting from JAR: $JARFILE"
    #     jar xvf $JARFILE
    # done
    # mkdir -p META-INF
    # echo "Main-Class: CrateGatePipeline" > META-INF/MANIFEST.MF
    # CLASSES=`find . -name "*.class"`
    # jar cmvf META-INF/MANIFEST.MF ../gatehandler.jar $CLASSES
    # cd ..

    # This does work, but it can't find the gate.plugins.home, etc.,
    # so we gain little.

    # See also: http://one-jar.sourceforge.net/version-0.95/

    # Note that arguments *after* the program name are seen by the program, and
    # arguments before it go to Java. If you specify the classpath (which you
    # need to to find GATE), you must also include the directory of your
    # MyThing.class file.

    democommand_args = (
        [args.java] + java_options + [GATE_PIPELINE_CLASSNAME] + prog_args
    )
    democommand_2_args = democommand_args +  debug_options_2
    democommand = ' '.join(hack_shlex_quote(x) for x in democommand_args)
    democommand_2 = ' '.join(hack_shlex_quote(x) for x in democommand_2_args)
    comment = 'REM ' if WINDOWS else '# '
    with open(args.script, 'w') as outfile:
        if not WINDOWS:
            print('#!/bin/bash', file=outfile)
            print('', file=outfile)
        print(democommand, file=outfile)
        print('', file=outfile)
        print(comment + 'For extra verbosity:', file=outfile)
        print(comment + democommand_2, file=outfile)
    os.chmod(args.script,
             stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
             stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
             stat.S_IROTH | stat.S_IXOTH)
    print("Run {} for a demo.".format(args.script))

    # JAR run:
    # java -jar ./gatehandler.jar $PROG_ARGS


if __name__ == '__main__':
    main()
