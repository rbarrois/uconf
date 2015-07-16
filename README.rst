UConf
=======


UConf is a small tool aiming to provide simple handling of configuration files for an heterogeneous
computer set.

Its key concepts are:

- Abstract host-specific config to common features (server, relay, ...)
- Host-specific configuration may range from a single-line change to a whole file rewrite
- Configuration files are modified in place, not in the source - versionned - repository.


In other words, it provides the following features:

- Map each host to a set of categories (e.g laptop, server, dev, remote, ...)
- For each category (or combination thereof), list the files to install and their destinations
- For each file, conditionnally include some parts depending on the active categories


Usage
-----

Configuration
"""""""""""""

First, create the folder structure:

.. code-block:: shell

    $ cd ~/conf
    $ mkdir .uconf
    $ touch .uconf/config

Then, set a few settings:

.. code-block:: ini

    # .uconf/config

    [core]
    # Install files to my home folder
    target = ~/

    [categories]
    # The host names "myhostname" belongs to the 'shell' and 'x11' categories
    myhostname: shell x11

    [files]
    # Hosts in the 'shell' category should install
    # the 'shell/gitconfig' and 'ssh/config' files
    shell: shell/gitconfig ssh/config

    # Hosts in the 'shell' but not the 'work' category should install
    # our authorized_keys
    shell && !work: ssh/authorized_keys

    [actions]
    # Files located in ~/conf/ssh are parsed and written to ~/.ssh/
    ssh/* = parse destdir=".ssh/"

    # shell/gitconfig goes to ~/.gitconfig
    shell/gitconfig = parse destdir="~/.gitconfig"


Files
"""""

The heart of ``uconf`` is its file processing engine.

On the surface, it is a simple preprocessor that will parse files
based on the categories defined in the ``.uconf/config`` file.

In other words, if the file ``shell/gitconfig`` contains:

.. code-block:: ini

    [user]
    #@if work
      name = Raphaël Barrois
      email = raphael.barrois@example.org
    #@else
      name = Xelnor
      email = raphael.barrois@polytechnique.org
    #@endif

And is build on the ``myhostname`` from the above example, the output will be:

.. code-block:: ini

    # ~/.gitconfig
    [user]
      name = Xelnor
      email = raphael.barrois@polytechnique.org


Commands
""""""""

Once your configuration folder is set up, basic commands will be:

.. code-block:: sh

    $ cd ~/conf
    $ uconf make
    Building file shell/gitconfig (FileProcessingAction)
    Building file ssh/config (FileProcessingAction)
    Building file ssh/authorized_keys (FileProcessingAction)

If you have modified a file, just backport its changes:

.. code-block:: sh

    $ cd ~/conf
    $ uconf back shell/gitconfig
    Backporting file shell/gitconfig (FileProcessingAction)

This will update the source file (``~/conf/shell/gitconfig`` in this example)
to incorporate the changes from the destination file (here, ``~/.gitconfig``).

This works even if the file contained branches, i.e if the source file was:

.. code-block:: ini

    [user]
    #@if work
      name = Raphaël Barrois
      email = raphael.barrois@example.org
    #@else
      name = Xelnor
      email = raphael.barrois@polytechnique.org
    #@endif

And the destination (on a non-work machine) was modified to read:

.. code-block:: ini

    [user]
      name = Raphaël "Xelnor" Barrois
      email = raphael.barrois@polytechnique.org

Then the result of running ``uconf back shell/gitconfig`` will be:

.. code-block:: ini

    [user]
    #@if work
      name = Raphaël Barrois
      email = raphael.barrois@example.org
    #@else
      name = Raphaël "Xelnor" Barrois
      email = raphael.barrois@polytechnique.org
    #@endif
