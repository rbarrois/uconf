UConf
=======


UConf is a small tool aiming to provide simple handling of configuration files for an heterogeneous
computer set.

Its key concepts are:

- Abstract host-specific config to common features (server, relay, ...)
- Host-specific configuration may range from a single-line change to a whole file rewrite
- Configuration files are modified in place, not in the source - versionned - repository.


Usage
-----


Once your configuration folder is set up, basic commands will be:

.. code-block:: sh

    $ cd ~/conf
    $ uconf make
    Building file shell/screenrc (FileProcessingAction)
    Building file shell/gitconfig (FileProcessingAction)
    Building file ssh/config (FileProcessingAction)
    Building file ssh/authorized_keys (FileProcessingAction)
    Building file x11/xinitrc (FileProcessingAction)

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


Configuring
-----------

You can get started with ``uconf init <source_dir> <target_dir>``.
This will generate the following layout::

    ./<source_dir>
        config
        src/

The ``config`` file is UConf's main entry point. Its content should look like::

    [global]
    ; Install files into the <target_dir> folder.
    target: <target_dir>

    ; Default to parsing the files.
    default-action: parse

    [categories]
    ; Put your category definitions here
    ; Example:
    ; myserv: server
    ; server and slave: not master

    [files]
    ; Add category-file rules
    ; server: ssh/sshd_config
    ; laptop: X11/xorg.conf

    [rules]
    ; Override file rules here
    ; boot/splash_screen: copy
