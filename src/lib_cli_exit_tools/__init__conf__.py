# CONF

name = 'lib_cli_exit_tools'
title = 'functions to exit an cli application properly'
version = 'v0.0.1'
url = 'https://github.com/bitranox/lib_cli_exit_tools'
author = 'Robert Nowotny'
author_email = 'bitranox@gmail.com'
shell_command = 'lib_cli_exit_tools'


def print_info() -> None:
    print(f"""\

Info for {name}:

    functions to exit an cli application properly

    Version : {version}
    Url     : {url}
    Author  : {author}
    Email   : {author_email}""")
